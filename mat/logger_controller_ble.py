import bluepy.btle as btle
import time
import re
import xmodem
from mat.logger_controller import LoggerController
from mat.logger_controller import DELAY_COMMANDS


class Delegate(btle.DefaultDelegate):
    def __init__(self):
        btle.DefaultDelegate.__init__(self)
        self.buffer = ''
        self.read_buffer = []
        self.xmodem_buffer = bytes()
        self.xmodem_mode = False
        self.rx_observers = []
        self.sentC = False

    def handleNotification(self, handler, data):
        # notification arrives while in ascii mode
        if not self.xmodem_mode:
            self.buffer += data.decode('utf-8')
            self.buffer = self.buffer.replace(chr(10), '')
            self._notifications_ascii_mode_to_buffers()
        # notification arrives while in xmodem mode
        else:
            if not self.sentC:
                # this receives tag_answer to 'GET' command
                self.buffer += data.decode('utf-8')
            else:
                self.xmodem_buffer += data

    def _notifications_ascii_mode_to_buffers(self):
        while chr(13) in self.buffer:
            # removes all leading '\r' characters
            if self.buffer.startswith(chr(13)):
                self.buffer = self.buffer[1:]
                continue

            # if a complete string was received, add it to read_buffer
            pos = self.buffer.find(chr(13))
            in_str = self.buffer[:pos]
            self.buffer = self.buffer[pos + 1:]
            if in_str:
                self.read_buffer.append(in_str)

    @property
    def in_waiting(self):
        return True if self.read_buffer else False

    def read_line(self):
        # handleNotifications() does read_buffer.append(), pop() is here
        if not self.read_buffer:
            raise IndexError('Read buffer is empty')
        return self.read_buffer.pop(0)


class LoggerControllerBLE(LoggerController):
    def __init__(self, mac):
        super(LoggerController, self).__init__()
        # after ble_connect, 1 second delay required at RN4020
        self.peripheral = btle.Peripheral(mac)
        time.sleep(1)
        self.delegate = Delegate()
        self.peripheral.setDelegate(self.delegate)
        uuid_serv = '00035b03-58e6-07dd-021a-08123a000300'
        uuid_char = '00035b03-58e6-07dd-021a-08123a000301'
        self.mldp_service = self.peripheral.getServiceByUUID(uuid_serv)
        self.mldp_data = self.mldp_service.getCharacteristics(uuid_char)[0]
        cccd = self.mldp_data.valHandle + 1
        self.peripheral.writeCharacteristic(cccd, b'\x01\x00')
        self.modem = xmodem.XMODEM(self.getc, self.putc)
        # feel free to change logging level, default is 30
        self.modem.log.setLevel(50)
        self.modem.log.disabled = True
        self.fw_version = ''

    def open(self):
        pass

    def command(self, tag, data=None):
        rv_tag_waiting = self._command_build(tag, data)
        if rv_tag_waiting == '':
            return None
        return self._command_answer(tag, rv_tag_waiting)

    def _command_build(self, tag, data):
        # build and send the command
        self.delegate.buffer = ''
        self.delegate.read_buffer = []
        data = '' if data is None else data
        length = '%02x' % len(data)
        if tag == 'sleep' or tag == 'RFN':
            self.write(tag + chr(13))
        else:
            self.write(tag + ' ' + length + data + chr(13))

        # expect answer? not for RST, BSL and sleep commands
        tag_waiting = tag
        if tag == 'RST' or tag == 'sleep' or tag == 'BSL':
            tag_waiting = ''
        return tag_waiting

    def _command_answer(self, tag, tag_waiting):
        # analyze line collected by handleNotification(), if any
        while True:
            # one notification w/ 1 byte makes waitForNotifications() continue
            if not self.peripheral.waitForNotifications(5):
                raise LCBLEException('\tAnswer timeout at ' + tag_waiting)
            if self.delegate.in_waiting:
                return self._command_answer_analyze(tag, tag_waiting)

    def _command_answer_analyze(self, tag, tag_waiting):
        inline = self.delegate.read_line()
        if inline.startswith(tag_waiting):
            # return command answer, wait previously if needed
            if tag in DELAY_COMMANDS:
                time.sleep(2)
            return inline
        elif inline.startswith('ERR'):
            raise LCBLEException('MAT-1W returned ERR')
        elif inline.startswith('INV'):
            raise LCBLEException('MAT-1W reported invalid command')

    # send commands directly to RN4020 BLE module
    def control_command(self, data):
        self.delegate.buffer = ''
        self.delegate.read_buffer = []
        self.write('BTC 00' + data + chr(13))

        # check fw_version to control different behaviors
        if self.fw_version == '':
            raise LCBLEException('Need fw_version() prior control_command().')

        return self._control_command_answer()

    def _control_command_answer(self):
        return_val = self._control_command_analyze()

        # time for RN4020 to clear string, it went ok
        if return_val:
            time.sleep(2)
            return 'CMDAOKMLDP'

        # order is important: old firmwares will reach this point
        if self.fw_version < '1.7.28':
            return 'assume_CMDAOKMLDP'
        # check if a new-enough logger could not speed up
        if self.fw_version >= '1.7.28' and return_val != 'CMDAOKMLDP':
            raise LCBLEException('RN4020 did not speed up, restarting...')

    def _control_command_analyze(self):
        # last_rx = time.time()
        # answer = ''
        # while time.time() - last_rx < 3:
        #     self.peripheral.waitForNotifications(0.05)
        #     if self.delegate.in_waiting:
        #         inline = self.delegate.read_line()
        #         answer += inline
        #         if answer == 'CMDAOKMLDP':
        #             return True
        last_rx = time.time()
        answer = ''
        while time.time() - last_rx < 3:
            self.peripheral.waitForNotifications(0.05)
            if self.delegate.in_waiting:
                inline = self.delegate.read_line()
                answer += inline
            if answer == 'CMDAOKMLDP':
                return True

    # write in BLE characteristic, used in command() and list/get_files()
    def write(self, data, response=False):
        for c in data:
            self.mldp_data.write(c.encode('utf-8'), withResponse=response)

    def list_files(self):
        # 'DIR' command does not 'answer_tag'
        self.delegate.buffer = ''
        self.delegate.read_buffer = []
        self.write('DIR 00' + chr(13))

        files_back = []
        time_limit = time.time() + 5
        while time.time() < time_limit:
            self.peripheral.waitForNotifications(0.05)
            end = False
            if self.delegate.in_waiting:
                end = self._collect_dir_files_or_end(files_back)
            if end:
                return files_back

        # timeout while 'DIR', return nothing
        raise LCBLEException('\'DIR\' got timeout while listing.')

    def _collect_dir_files_or_end(self, files):
        file_str = self.delegate.read_line()
        # detect end of listing
        if file_str == chr(4):
            return True
        file_name, file_size = self._extract_file_name_n_size(file_str)
        files.append((file_name, file_size))
        return file_str == chr(4)

    def _extract_file_name_n_size(self, file_str):
        # Find all printable characters
        re_obj = re.search('([\x20-\x7E]+)\t+(\d*)', file_str)
        try:
            file_name = re_obj.group(1)
            file_size = int(re_obj.group(2))
            return file_name, file_size
        except (AttributeError, IndexError):
            raise LCBLEException('\'DIR\' got invalid filename.')

    # getc() used by xmodem module
    def getc(self, size, timeout=2):
        time_limit = time.time() + timeout
        while time.time() < time_limit:
            self.peripheral.waitForNotifications(0.05)
            if len(self.delegate.xmodem_buffer) >= size:
                data = self.delegate.xmodem_buffer[:size]
                self.delegate.xmodem_buffer = self.delegate.xmodem_buffer[size:]
                return data
        if len(self.delegate.xmodem_buffer):
            # getc() timed out, but still some data in buffer < size
            data = self.delegate.xmodem_buffer
            self.delegate.xmodem_buffer = bytes()
            return data
        else:
            # getc() timed out with nothing left in buffer
            return None

    def putc(self, data, timeout=2):
        time_limit = time.time() + timeout
        while time.time() < time_limit:
            try:
                self._putc_C_or_data(data)
            except LCBLEException:
                time.sleep(0.1)
            else:
                return len(data)
        return 0

    def _putc_C_or_data(self, data):
        # sending the triggering 'C' character for xmodem protocol
        if not self.delegate.sentC:
            self.mldp_data.write(chr(67).encode('utf-8'), withResponse=True)
            self.delegate.sentC = True
        # sending normal binary data
        else:
            self.mldp_data.write(data, withResponse=True)

    def get_file(self, filename, size, out_stream):
        self._get_file_ascii_phase(filename)
        self._get_file_xmodem_phase(size, out_stream)

    def _get_file_ascii_phase(self, filename):
        # phase 1 of get_file() command: ascii 'GET' file name
        self.delegate.buffer = ''
        self.delegate.read_buffer = []
        length = '%02x' % len(filename)
        out_str = 'GET ' + length + filename + chr(13)
        self.write(out_str)

        # GET answer 'GET 00', comes bit late! we do as in command()
        last_rx = time.time()
        while time.time() - last_rx < 2:
            self.peripheral.waitForNotifications(0.05)
            if self.delegate.in_waiting\
                    and self.delegate.read_line() == 'GET 00':
                return True
        raise LCBLEException('\'GET\' got timeout while answering.')

    def _get_file_xmodem_phase(self, size, out_stream):
        # phase 2 of get_file() command: binary recv() a file
        self.delegate.xmodem_mode = True
        self.delegate.xmodem_buffer = bytes()
        self.delegate.sentC = False
        # quiet=1 avoids displaying 'error: expected SOH; got b'%'' messages
        self.modem.recv(out_stream, quiet=1)
        self.delegate.xmodem_mode = False

        # local filesystem stuff, check if valid size
        out_stream.seek(0, 2)
        if out_stream.tell() < size:
            raise XModemException('Xmodem, error: page < 1024 may be small.')
        out_stream.truncate(size)

    def close(self):
        try:
            self.peripheral.disconnect()
            time.sleep(1)
            return True
        except AttributeError:
            return False


class LCBLEException(Exception):
    pass


class XModemException(Exception):
    pass
