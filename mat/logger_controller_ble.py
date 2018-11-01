from mat.logger_controller import LoggerController
import bluepy.btle as btle
import re
import sys
import time
import xmodem


class LoggerControllerBLE(LoggerController):
    # peripheral is an open BLE Peripheral object
    # 'service' is Microchip MLDP, 'data_characteristic' (dc) is for data
    # 'handler' writes characteristic description to enable 'dc' notification
    # 'observer_*' list contain delegate class callbacks, notify goes to rx
    def __init__(self, mac):
        try:
            self.peripheral = btle.Peripheral(mac)
            print('BLE Logger Connected: {}'.format(mac))
        except btle.BTLEException:
            print('Failed to connect to {}'.format(mac))
        else:
            self.is_connected = True
            self.delegate = Delegate()
            self.delegate.rx_observers.append(self.rx_notify)
            self.peripheral.setDelegate(self.delegate)
            self.service = self.peripheral.getServiceByUUID('00035b03-58e6-07dd-021a-08123a000300')
            self.data_characteristic = self.service.getCharacteristics('00035b03-58e6-07dd-021a-08123a000301')[0]
            self.peripheral.writeCharacteristic(self.data_characteristic.valHandle + 1, b'\x01\x00')
            self.modem = xmodem.XMODEM(self.getc_xmodem, self.putc_xmodem)

    def open(self, mac):
        if self.is_connected:
            return True
        return self.__init__(self.peripheral.addr)

    def close(self):
        self.peripheral.disconnect()
        self.is_connected = False

    def rx_notify(self, data):
        for observer in self.rx_observers:
            observer(data)  # since the

    def command(self, *args):
        if not self.is_connected:
            return None

        # tag indicates which command are we sending via BLE
        tag = args[0]
        data = str(args[1]) if len(args) == 2 else ""
        length = '%02x' % len(data)
        if tag == 'sleep' or tag == 'RFN':
            out_str = tag
        else:
            out_str = tag + ' ' + length + data

        # 'write_BLE()', actually send, the BLE command
        return_val = None
        self.write_BLE(out_str + chr(13))

        # RST, BSL and sleep don't return tags
        tag_waiting = tag
        if tag == 'RST' or tag == 'sleep' or tag == 'BSL':
            tag_waiting = ''

        # wait for a BLE answer
        while tag_waiting:
            # we did not receive it in time
            if not self.peripheral.waitForNotifications(5):
                raise LogCtrlBLEException('BLE Logger timeout while waiting for: ' + tag_waiting)
            # we receive BLE answer in time
            if self.delegate.in_waiting:
                inline = self.delegate.read_line()
                # we leave this loop
                if inline.startswith(tag_waiting):
                    tag_waiting = ''
                    return_val = inline
                elif inline.startswith('ERR'):
                    raise LogCtrlBLEException('MAT-1W returned ERR')
                elif inline.startswith('INV'):
                    raise LogCtrlBLEException('MAT-1W reported invalid command')
        # analyze the answer outside
        return return_val

    def control_command(self, data):
        # commands not for logger but for RN4020 module itself
        out_str = 'BTC 00' + data + chr(13)
        self.write_BLE(out_str)

        last_rx = time.time()
        return_val = ''
        while time.time() - last_rx < 2:
            if self.peripheral.waitForNotifications(0.5):
                last_rx = time.time()
            if self.delegate.in_waiting:
                inline = self.delegate.read_line()
                return_val += inline
        return return_val

    def write_BLE(self, data, response=False):
        # write byte-to-byte to BLE characteristic, update tx_observers w/ data sent
        # from official website: data is 'str' in python2, 'bytes' in python3
        for c in data:
            c_in_bytes = c.encode("utf-8")
            self.data_characteristic.write(c_in_bytes, withResponse=response)

    def getc_xmodem(self, size, timeout=2):
        # try to receive 'size' characters from xmodem module
        start_time = time.time()
        while True:
            self.peripheral.waitForNotifications(0.005)
            in_char = self.delegate.read_chars(size) if len(self.delegate.buffer) >= size else None
            if in_char:
                # 'in_char' is a string, .encode it for bytes
                sys.stdout.write('.')
                return in_char.encode("utf-8")
            else:
                print("NONE CHAR")
            if time.time() - start_time > timeout:
                print("--> GETC timeout?")
                return None

    def putc_xmodem(self, data):
        # transmit data via xmodem
        print("--> PUTC data {}, type {}, ord {}".format(data, type(data), ord(data)))
        self.data_characteristic.write(data.encode("utf-8"), withResponse=False)

    def list_files(self):
        # get [list] of (name, size) tuples of the files in the logger
        files = []
        self.delegate.buffer = ''
        self.delegate.read_buffer = []

        # 'DIR' command does not generate a timeout...
        self.write_BLE('DIR 00' + chr(13))

        # ... so we create our own timeout scheme
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
                    raise LogCtrlBLEException('DIR returned an invalid filename.')
                else:
                    files.append((file_name, file_size))
            # timeout while retrieving files, do not return anything
            if time.time() - last_rx > 2:
                raise LogCtrlBLEException('Timeout while getting file list.')

        # return file list
        return files

    def get_file(self, filename, size, outstream):
        # get 'filename' and writes all its 'size' bytes to outstream ~ fseek
        self.command('GET', filename)
        self.delegate.buffer = ''
        self.delegate.read_buffer = []
        self.delegate.xmodem_mode = True

        # use xmodem to get the file
        try:
            self.modem.recv(outstream)
        except:
            raise XModemException('there was a File transfer error')

        # offset within the file
        outstream.seek(0, 2)
        if outstream.tell() < size:
            raise XModemException('File too small. Transmission was incomplete.')

        # cut file to size (remove trailing padding 0x1A)
        outstream.truncate(size)
        self.delegate.buffer = ''
        self.delegate.xmodem_mode = False
        return True

    def disconnect(self):
        self.peripheral.disconnect()


class Delegate(btle.DefaultDelegate):
    # handleNotificationMethod() here is called when a notification is received
    # this class also contains a read buffer which assembles up to receiving the CR character
    # the different MLDP data packets
    def __init__(self):
        btle.DefaultDelegate.__init__(self)
        self.buffer = ''
        self.read_buffer = []
        self.xmodem_mode = False
        self.rx_observers = []

    def handleNotification(self, handle, data):
        # in python2, a str arrives here, in python3, bytes arrive here
        # 'data' example v3: b'\n\rSTS 0201\r\n', decode() gives us string

        if not self.xmodem_mode:
            # obtain string and remove LFs
            data = data.decode('utf-8')
            self.buffer += data
            self.buffer = self.buffer.replace(chr(10), '')
            while chr(13) in self.buffer:
                # remove initial CRs, if any
                if self.buffer.startswith(chr(13)):
                    self.buffer = self.buffer[1:]
                    continue

                # if a complete string was received, add it to read_buffer
                pos = self.buffer.find(chr(13))
                in_str = self.buffer[:pos]
                self.buffer = self.buffer[pos + 1:]
                if in_str:
                    self.read_buffer.append(in_str)
        else:
            # this goes to xmodem_getc()
            pass

    @property
    def in_waiting(self):
        # returns True if read_buffer contains something, or if xmodem mode is active
        return True if self.xmodem_mode or self.read_buffer else False

    def read_line(self):
        # returns a line, if any, from FIFO read buffer
        if not self.read_buffer:
            raise IndexError('Read buffer is empty')
        return self.read_buffer.pop(0)

    def read_chars(self, num_chars):
        # returns up to 'num_chars' from buffer, if not enough, exception is raised
        if num_chars > len(self.buffer):
            raise RuntimeError('Insufficient characters in buffer')
        self.buffer, return_string = self.buffer[num_chars:], self.buffer[:num_chars]
        return return_string


class Retries(Exception):
    pass


class LogCtrlBLEException(Exception):
    pass


class XModemException(Exception):
    pass