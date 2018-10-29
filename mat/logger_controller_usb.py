from mat.logger_controller import LoggerController
import os
import re
from serial import (
    Serial,
    SerialException,
)
from serial.tools.list_ports import grep
from mat.logger_cmd_usb import LoggerCmdUsb


PORT_PATTERNS = {
    'posix': r'(ttyACM0)',
    'nt': r'^COM(\d+)',
}

TIMEOUT = 5


class LoggerControllerUSB(LoggerController):
    def __init__(self):
        LoggerController.__init__(self)
        self.__callback = {}
        self.is_connected = False
        self.__port = None
        self.com_port = None

    def open(self):
        self.open_port()

    def open_port(self, com_port=None):
        try:
            com_port = com_port or find_port()
            if com_port:
                self._open_port(com_port)
        except SerialException:
            self.close()
        return self.is_connected

    def _open_port(self, com_port):
        if isinstance(self.__port, Serial):
            self.__port.close()
        if os.name == 'posix':
            self.__port = Serial('/dev/' + com_port)
        else:
            self.__port = Serial('COM' + str(com_port))
        self.__port.timeout = TIMEOUT
        self.is_connected = True
        self.com_port = com_port

    def close(self):
        self.close_port()

    def close_port(self):
        if self.__port:
            self.__port.close()
        self.is_connected = False
        self.com_port = 0

    def command(self, *args):
        if not self.is_connected:
            return None
        try:
            return self.find_tag(self.target_tag(args))
        except SerialException:
            self.close_port()
            return None

    def find_tag(self, target):
        if not target:
            return
        while True:
            cmd = LoggerCmdUsb(self.__port)
            if cmd.tag == target or cmd.tag == 'ERR':
                self.callback('rx', cmd.cmd_str())
                return cmd.result()

    def callback(self, key, cmd_str):
        if key in self.__callback:
            self.__callback[key](cmd_str)

    def target_tag(self, args):
        tag = args[0]
        data = ''
        if len(args) == 2:
            data = str(args[1])
        length = '%02x' % len(data)
        if tag == 'sleep' or tag == 'RFN':
            out_str = tag + chr(13)
        else:
            out_str = tag + ' ' + length + data + chr(13)
        self.__port.reset_input_buffer()
        self.__port.write(out_str.encode('IBM437'))
        self.callback('tx', out_str[:-1])
        if tag == 'RST' or tag == 'sleep' or tag == 'BSL':
            return ''
        return tag

    def set_callback(self, event, callback):
        self.__callback[event] = callback


def find_port():
    try:
        field = list(grep('2047:08[AEae]+'))[0][0]
    except (TypeError, IndexError):
        raise RuntimeError("Unable to find port")
    pattern = PORT_PATTERNS.get(os.name)
    if not pattern:
        raise RuntimeError("Unsupported operating system: " + os.name)
    return re.search(pattern, field).group(1)

