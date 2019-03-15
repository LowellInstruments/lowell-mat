import bluepy.btle as btle
import time
import re
from mat.xmodem_ble import xmodem_get_file
from mat.logger_controller import LoggerController
from mat.logger_controller import DELAY_COMMANDS


class Delegate(btle.DefaultDelegate):
    def __init__(self):
        btle.DefaultDelegate.__init__(self)
        self.buffer = bytes()
        self.read_buffer = []
        self.xmodem_mode = False
        self.x_buffer = bytes()

    # receive data from BLE logger, discern ascii or xmodem mode
    def handleNotification(self, handler, data):
        if not self.xmodem_mode:
            self._handle_notifications_ascii_mode(data)
        else:
            self.x_buffer += data

    # receive data from BLE logger, ascii mode
    def _handle_notifications_ascii_mode(self, data):
        # required, some times changes its type
        if self.buffer == '':
            self.buffer = bytes()
        self.buffer += data
        self.buffer = self.buffer.replace(b'\n', b'')
        self._handle_notifications_ascii_mode_extract_buffer()

    # extract data from ascii buffer, put it in queue
    def _handle_notifications_ascii_mode_extract_buffer(self):
        while b'\r' in self.buffer:
            # make sure ascii received doesn't start with CR
            if self.buffer.startswith(b'\r'):
                self.buffer = self.buffer[1:]
                continue
            pos = self.buffer.find(b'\r')
            in_str = self.buffer[:pos]
            self.buffer = self.buffer[pos + 1:]
            if in_str:
                # if complete string received, add to read_buffer
                self.read_buffer.append(in_str)

    @property
    def in_waiting(self):
        return True if self.xmodem_mode or self.read_buffer else False

    # obtain single line from ascii queue, complements append() above
    def read_line(self):
        if not self.read_buffer:
            raise IndexError('Read buffer is empty')
        return self.read_buffer.pop(0)


class LoggerControllerBLE(LoggerController):
    def __init__(self, mac):
        super(LoggerController, self).__init__()
        self.peripheral_mac = mac
        self.peripheral = None
        self.delegate = None
        self.mldp_service = None
        self.mldp_data = None

    # called by __enter__ from class LoggerController
    def open(self):
        try:
            self.peripheral = btle.Peripheral()
            self.peripheral.connect(self.peripheral_mac)
            # one second required by RN4020
            time.sleep(1)
            self.delegate = Delegate()
            self.peripheral.setDelegate(self.delegate)
            UUID_SERV = '00035b03-58e6-07dd-021a-08123a000300'
            UUID_CHAR = '00035b03-58e6-07dd-021a-08123a000301'
            self.mldp_service = self.peripheral.getServiceByUUID(UUID_SERV)
            self.mldp_data = self.mldp_service.getCharacteristics(UUID_CHAR)[0]
            CCCD = self.mldp_data.valHandle + 1
            self.peripheral.writeCharacteristic(CCCD, b'\x01\x00')
            return True
        except AttributeError:
            return False

    # called by __exit__ & __del__ (overriden here) in class LoggerController
    def close(self):
        try:
            self.peripheral.disconnect()
            time.sleep(1)
            return True
        except AttributeError:
            return False

    # build and send command, same interface as other logger_controller_*
    def command(self, *args):
        tag = args[0]
        data = str(args[1]) if len(args) == 2 else ''
        length = '{:02x}'.format(len(data))
        if tag == 'sleep' or tag == 'RFN':
            out_str = tag
        else:
            out_str = tag + ' ' + length + data
        self.write((out_str + chr(13)).encode())

        # answer: RST, BSL and sleep don't return any
        if tag in ['RST', 'sleep', 'BSL']:
            return None

        # answer: commands that do
        return self._command_result(tag).decode()

    # see command result
    def _command_result(self, tag):
        while True:
            if not self.peripheral.waitForNotifications(3):
                raise LCBLEException('Logger timeout waiting: ' + tag)
            if self.delegate.in_waiting:
                return self._command_parse_back(tag)

    # parse command result
    def _command_parse_back(self, tag):
        result = self.delegate.read_line()
        if result.startswith(tag.encode()):
            if tag in DELAY_COMMANDS:
                time.sleep(2)
            return result
        if result.startswith(b'ERR'):
            raise LCBLEException('MAT-1W returned ERR')
        if result.startswith(b'INV'):
            raise LCBLEException('MAT-1W reported invalid command')

    # build and send control_command destined to RN4020 not MSP430
    def control_command(self, data):
        # build and send control command
        self.delegate.buffer = ''
        self.delegate.read_buffer = []
        out_str = ('BTC 00' + data + chr(13)).encode()
        self.write(out_str)
        return self._control_command_result()

    # see control command result
    def _control_command_result(self):
        last_rx = time.time()
        result = ''
        while not result.endswith('MLDP') and time.time() < last_rx + 3:
            result, last_rx = self._control_command_parse_back(result, last_rx)
        return result

    # parse control command result
    def _control_command_parse_back(self, result, last_rx):
        if self.peripheral.waitForNotifications(0.05):
            last_rx = time.time()
        if self.delegate.in_waiting:
            result += self.delegate.read_line().decode()
        return result, last_rx

    # write to logger BLE serial port characteristic
    def write(self, data, response=False):
        data2 = [data[i:i + 1] for i in range(len(data))]
        for c in data2:
            self.mldp_data.write(c, withResponse=response)

    # know which files are in remote logger
    def dir_command(self):
        self.delegate.buffer = ''
        self.delegate.read_buffer = []
        self.write(('DIR 00' + chr(13)).encode())
        return self._dir_command_result()

    # grab dir_command() answer
    def _dir_command_result(self):
        files = []
        answer_bytes = bytes()
        last_rx = time.time()
        while answer_bytes != b'\x04':
            # receive via BLE the file list, parse line by line
            self.peripheral.waitForNotifications(0.01)
            if self.delegate.in_waiting:
                last_rx = time.time()
                answer_bytes = self._dir_command_parse_back(files)
            if time.time() - last_rx > 3:
                raise LCBLEException('Timeout while getting file list.')
        return files

    # parse each row containing file + size
    def _dir_command_parse_back(self, files):
        answer_bytes = self.delegate.read_line()
        try:
            file_str = answer_bytes.decode()
            re_obj = re.search(r'([\x20-\x7E]+)\t+(\d*)', file_str)
            file_name = re_obj.group(1)
            file_size = int(re_obj.group(2))
            files.append((file_name, file_size))
        except (AttributeError, IndexError):
            # do not allow a bad pair to mess everything
            pass
        finally:
            return answer_bytes

    # obtain a file from the logger via BLE using xmodem
    def get_file(self, filename, dfolder):  # pragma: no cover
        self.delegate.buffer = ''
        self.delegate.x_buffer = bytes()
        self.command('GET', filename)
        self.delegate.xmodem_mode = True

        # try to receive binary file using xmodem
        result, bytes_received = xmodem_get_file(self)
        self.delegate.xmodem_mode = False
        if result:
            full_file_path = dfolder + '/' + filename
            with open(full_file_path, 'wb') as f:
                f.write(bytes_received)
            return True
        return False

    # prevent garbage collector closing logger_controller_ble
    def __del__(self):
        pass


class LCBLEException(Exception):
    pass
