import bluepy.btle as btle
import time
import re
import xmodem
from mat.logger_controller import LoggerController

#TODO: consider putting time.sleep() in necessary commands

class Delegate(btle.DefaultDelegate):
    def __init__(self):
        btle.DefaultDelegate.__init__(self)
        self.buffer = ''
        self.read_buffer = []
        self.xmodem_buffer = bytes()
        self.xmodem_mode = False
        self.rx_observers = []
        self.sentC = False

    def handleNotification(self, cHandle, data):
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
            # print("-> NOTIF {}, len {}, type {}".
            # format(data, len(data), type(data)))
            if not self.sentC:
                # answer to GET command
                temp = data.decode("utf-8")
                #print("-> NOTI pre_sentC -> {} type {} len {}".
                # format(temp, type(temp), len(temp)))
                self.buffer += temp
            else:
                temp = data
                # print("-> NOTI pos_sentC -> {} type {} len {}".
                # format(temp, type(temp), len(temp)))
                self.xmodem_buffer += temp

    @property
    def in_waiting(self):
        return True if self.read_buffer else False

    def read_line(self):
        if not self.read_buffer:
            raise IndexError('Read buffer is empty')
        return self.read_buffer.pop(0)

    def read_chars(self, num_chars):
        if num_chars > len(self.buffer):
            raise RuntimeError('Insufficient characters in buffer')
        self.buffer = self.buffer[num_chars:]
        return_string = self.buffer[:num_chars]
        # print("-> SELF.BUFFER  {}, len {}, type {}".
        #       format(self.buffer, len(self.buffer), type (self.buffer)))
        # print("-> RETURNSTRING {}, len {}, type {}".
        #       format(return_string, len(return_string), type(return_string)))
        return return_string


class LoggerControllerBLE(LoggerController):
    def __init__(self, mac):
        self.peripheral = btle.Peripheral(mac)
        # add a short delay for unknown, but required reason at RN4020
        time.sleep(1)
        self.delegate = Delegate()
        self.peripheral.setDelegate(self.delegate)
        self.mldp_service = self.peripheral.getServiceByUUID('00035b03-58e6-07dd-021a-08123a000300')
        self.mldp_data = self.mldp_service.getCharacteristics('00035b03-58e6-07dd-021a-08123a000301')[0]
        cccd = self.mldp_data.valHandle + 1
        self.peripheral.writeCharacteristic(cccd, b'\x01\x00')
        self.modem = xmodem.XMODEM(self.getc, self.putc)

    def open(self):
        pass

    def command(self, tag, data=None):
        # build and send the command
        return_val = None
        data = '' if data is None else data
        length = '%02x' % len(data)
        if tag == 'sleep' or tag == 'RFN':
            out_str = tag
        else:
            out_str = tag + ' ' + length + data
        self.write(out_str + chr(13))

        # expect answer? RST, BSL and sleep don't return tags
        if tag == 'RST' or tag == 'sleep' or tag == 'BSL':
            tag_waiting = ''
        else:
            tag_waiting = tag

        while tag_waiting:
            if not self.peripheral.waitForNotifications(5):
                raise OdlwException('Logger timeout while waiting for: ' + tag_waiting)

            if self.delegate.in_waiting:
                inline = self.delegate.read_line()
                if inline.startswith(tag_waiting):
                    tag_waiting = ''
                    return_val = inline
                elif inline.startswith('ERR'):
                    raise OdlwException('MAT-1W returned ERR')
                elif inline.startswith('INV'):
                    raise OdlwException('MAT-1W reported invalid command')

        return return_val

    def control_command(self, data):
        # send commands to RN4020
        out_str = 'BTC 00' + data + chr(13)
        self.write(out_str)
        last_rx = time.time()
        return_val = ''
        while time.time() - last_rx < 2:
            if self.peripheral.waitForNotifications(0.5):
                last_rx = time.time()
            if self.delegate.in_waiting:
                inline = self.delegate.read_line()
                return_val += inline
        # time for MLDP clear string
        time.sleep(2)
        return return_val

    # write in BLE characteristic
    def write(self, data, response=False):
        for c in data:
            self.mldp_data.write(c.encode("utf-8"), withResponse=response)

    def list_files(self):
        # this 'DIR' command does not answer as the others (call commmand())
        files = []
        self.delegate.buffer = ''
        self.delegate.read_buffer = []

        self.write('DIR 00' + chr(13))

        last_rx = time.time()
        while True:
            self.peripheral.waitForNotifications(0.01)
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
                    raise OdlwException('DIR returned an invalid filename.')

                files.append((file_name, file_size))
            # There was a timeout. Don't return anything
            if time.time() - last_rx > 2:
                raise OdlwException('Timeout while getting file list.')

        return files

    def getc(self, size, timeout=5):
        last_rx = time.time()
        while time.time() - last_rx < timeout:
            if self.peripheral.waitForNotifications(0.005):
                last_rx = time.time()
            if len(self.delegate.xmodem_buffer) >= size:
                in_char = self.delegate.xmodem_buffer[:size]
                self.delegate.xmodem_buffer = self.delegate.xmodem_buffer[size:]
                # in_char is a <bytes> here
                temp = in_char
                # print("-> GETC temp {}, type {} len {}".
                # format(temp, type(temp), len(temp)))
                print(".", end="", flush=True)
                return temp
        # timeout
        print("-> *4*")
        return None

    def xmodem_write(self, data, response=False):
        for c in data:
            # print("-> WRITE c {}, type {}".format(c, type(c)))
            if not self.delegate.sentC:
                self.mldp_data.write(chr(67).encode("utf-8"), withResponse=response)
                self.delegate.sentC = True
            else:
                self.mldp_data.write(chr(c).encode("utf-8"), withResponse=response)

    def putc(self, data, timeout=0):
        start_time = time.time()
        while time.time() - start_time < 0.1:
            self.peripheral.waitForNotifications(0.005)
        # print("<- PUTC {}".format(data))
        self.xmodem_write(data)

    def get_file(self, filename, size, outstream):
        length = '%02x' % len(filename)
        out_str = 'GET ' + length + filename + chr(13)
        self.write(out_str)

        # the first 10 bytes are the answer to GET
        self.delegate.xmodem_mode = True
        last_rx = time.time()
        while time.time() - last_rx < 0.5:
            self.peripheral.waitForNotifications(0.005)

        # start receiving the binary file
        self.delegate.xmodem_buffer = bytes()
        self.delegate.sentC = False
        self.modem.recv(outstream)

        # get file size, truncate if necessary
        outstream.seek(0, 2)
        if outstream.tell() < size:
            raise XModemException('File too small, may be incomplete.')
        outstream.truncate(size)

        # clean up
        self.delegate.buffer = ''
        self.delegate.xmodem_mode = False
        print('Logger: {}, size {} Bytes downloaded ok'.format(filename, size))
        return True

    def disconnect(self):
        self.peripheral.disconnect()
        time.sleep(2)
        return "ok"

    def close(self):
        self.disconnect()


class OdlwException(Exception):
    pass


class XModemException(Exception):
    pass
