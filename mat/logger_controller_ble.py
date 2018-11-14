import bluepy.btle as btle
import time
import re
import xmodem
from mat.logger_controller import LoggerController


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
        # bytes as ascii for command() answers
        if not self.xmodem_mode:
            self.buffer += data.decode("utf-8")
            # Get rid of LFs and initial CRs
            self.buffer = self.buffer.replace(chr(10), '')
            while chr(13) in self.buffer:
                if self.buffer.startswith(chr(13)):
                    self.buffer = self.buffer[1:]
                    continue

                # if there is a complete string, add it for 'in_waiting()'
                pos = self.buffer.find(chr(13))
                in_str = self.buffer[:pos]
                self.buffer = self.buffer[pos+1:]
                if in_str:
                    self.read_buffer.append(in_str)

        else:
            if not self.sentC:
                # answer to GET command, byte as ascii after self.write('GET')
                temp = data.decode("utf-8")
                self.buffer += temp
            else:
                # bytes as bytes, for get_file() fxn
                temp = data
                self.xmodem_buffer += temp

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
        LoggerController.__init__(self)
        # after ble_connect, 1s delay required at RN4020
        self.peripheral = btle.Peripheral(mac)
        time.sleep(1)
        self.delegate = Delegate()
        self.peripheral.setDelegate(self.delegate)
        self.mldp_service = self.peripheral.getServiceByUUID('00035b03-58e6-07dd-021a-08123a000300')
        self.mldp_data = self.mldp_service.getCharacteristics('00035b03-58e6-07dd-021a-08123a000301')[0]
        cccd = self.mldp_data.valHandle + 1
        self.peripheral.writeCharacteristic(cccd, b'\x01\x00')
        self.modem = xmodem.XMODEM(self.getc, self.putc)
        self.modem.log.disabled = True
        self.get_dots = 0

    def open(self):
        pass

    def command(self, tag, data=None):
        # build and send the command
        self.delegate.buffer = ''
        self.delegate.read_buffer = []
        data = '' if data is None else data
        length = '%02x' % len(data)
        if tag == 'sleep' or tag == 'RFN':
            self.write(tag + chr(13))
        else:
            self.write(tag + ' ' + length + data + chr(13))

        # expect answer? RST, BSL and sleep commands don't return any
        tag_waiting = tag
        if tag == 'RST' or tag == 'sleep' or tag == 'BSL':
            tag_waiting = ''

        # collect line generated by handleNotification(), if any
        while tag_waiting:
            if not self.peripheral.waitForNotifications(5):
                raise LCBLEException('\tAnswer timeout at ' + tag_waiting)

            if self.delegate.in_waiting:
                inline = self.delegate.read_line()
                if inline.startswith(tag_waiting):
                    # return all the answer (ex: STS 0201)
                    return inline
                elif inline.startswith('ERR'):
                    raise LCBLEException('MAT-1W returned ERR')
                elif inline.startswith('INV'):
                    print(inline)
                    raise LCBLEException('MAT-1W reported invalid command')

    # send commands to RN4020
    def control_command(self, data):
        self.delegate.buffer = ''
        self.delegate.read_buffer = []
        self.write('BTC 00' + data + chr(13))

        # collect answer in 'return_val' until timeout
        last_rx = time.time()
        return_val = ''
        while time.time() - last_rx < 2:
            if self.peripheral.waitForNotifications(0.5):
                last_rx = time.time()
            if self.delegate.in_waiting:
                inline = self.delegate.read_line()
                return_val += inline

        # time for RN4020 to clear string, it went well
        if return_val != "CMDAOKMLDP":
            raise LCBLEException('RN4020 could not speed up, restarting.')
        else:
            time.sleep(2)
        return return_val

    # write in BLE characteristic, used in command() ang list_/get_files()
    def write(self, data, response=False):
        for c in data:
            self.mldp_data.write(c.encode("utf-8"), withResponse=response)

    def list_files(self):
        # 'DIR' command does not return "answer_tag" like command() does
        files = []
        self.delegate.buffer = ''
        self.delegate.read_buffer = []
        self.write('DIR 00' + chr(13))

        last_rx = time.time()
        while True:
            self.peripheral.waitForNotifications(0.005)
            if self.delegate.in_waiting:
                last_rx = time.time()
                file_str = self.delegate.read_line()
                if file_str == chr(4):
                    break
                # Find all printable characters
                re_obj = re.search('([\x20-\x7E]+)\t+(\d*)', file_str)
                try:
                    file_name = re_obj.group(1)
                    file_size = int(re_obj.group(2))
                except (AttributeError, IndexError):
                    raise LCBLEException("'DIR' got invalid filename.")

                files.append((file_name, file_size))
            # timeout while 'DIR', do not return anything
            if time.time() - last_rx > 2:
                raise LCBLEException("'DIR' got timeout while listing.")

        return files

    # getc() used by xmodem module
    def getc(self, size, timeout=5):
        last_rx = time.time()
        while time.time() - last_rx < timeout:
            if self.peripheral.waitForNotifications(0.005):
                last_rx = time.time()
            if len(self.delegate.xmodem_buffer) >= size:
                in_char = self.delegate.xmodem_buffer[:size]
                self.delegate.xmodem_buffer = self.delegate.xmodem_buffer[size:]
                # in_char is a <bytes> here
                return in_char

        # some xmodem interaction can timeout (first one always)
        return None

    def putc(self, data):
        # give time to receive last getc()
        start_time = time.time()
        while time.time() - start_time < 0.1:
            self.peripheral.waitForNotifications(0.005)

        # send 'C', ACK, NACKs... here
        if not self.delegate.sentC:
            self.mldp_data.write(chr(67).encode("utf-8"), withResponse=False)
            self.delegate.sentC = True
        else:
            self.mldp_data.write(data, withResponse=False)
            # aesthetics, just to know ongoing download
            self.get_dots = (self.get_dots + 1) % 50
            print("") if self.get_dots == 0 else print(".", end="", flush=True)

    def get_file(self, filename, size, out_stream):
        # stage 1 of get_file() command: ascii 'GET' file name
        self.delegate.buffer = ''
        self.delegate.read_buffer = []
        length = '%02x' % len(filename)
        out_str = 'GET ' + length + filename + chr(13)
        self.write(out_str)

        # GET answer = 10 bytes, slow to come, just filter them by now
        last_rx = time.time()
        while time.time() - last_rx < 0.3:
            if self.peripheral.waitForNotifications(0.005):
                last_rx = time.time()

        # stage 2 of get_file() command: binary recv() a file
        self.delegate.xmodem_mode = True
        self.delegate.xmodem_buffer = bytes()
        self.delegate.sentC = False
        self.modem.recv(out_stream)
        self.delegate.xmodem_mode = False

        # local filesystem stuff
        out_stream.seek(0, 2)
        if out_stream.tell() < size:
            raise XModemException("Xmodem, error: page < 1024 may be small.")
        out_stream.truncate(size)

    def disconnect(self):
        self.peripheral.disconnect()

    def close(self):
        self.disconnect()
        time.sleep(1)
        return "ok"


class LCBLEException(Exception):
    pass


class XModemException(Exception):
    pass
