# GPLv3 License
# Copyright (c) 2018 Lowell Instruments, LLC, some rights reserved

from mat.logger_controller import (
    LoggerController,
    DELAY_COMMANDS)
import os
import re
import time
from serial import (
    Serial,
    SerialException,
)
from serial.tools.list_ports import grep
from mat.logger_cmd import LoggerCmd


TIMEOUT = 5
PORT_PATTERNS = {
    'posix': r'(ttyACM0)',
    'nt': r'^COM(\d+)',
}


def find_port():
    try:
        field = list(grep('2047:08[AEae]+'))[0][0]
    except (TypeError, IndexError):
        raise RuntimeError("Unable to find port")
    pattern = PORT_PATTERNS.get(os.name)
    if not pattern:
        raise RuntimeError("Unsupported operating system: " + os.name)
    return re.search(pattern, field).group(1)


class LoggerControllerUSB(LoggerController):
    def __init__(self, address=None):
        super().__init__(address)
        self.is_connected = False
        self.__port = None

    def open(self):
        try:
            self.address = self.address or find_port()
            if self.address:
                self._open_port()
        except (SerialException, RuntimeError):
            self.close()
        return self.is_connected

    def _open_port(self):
        if isinstance(self.__port, Serial):
            self.__port.close()
        if os.name == 'posix':
            self.__port = Serial('/dev/' + self.address)
        else:
            self.__port = Serial('COM' + str(self.address))
        self.__port.timeout = TIMEOUT
        self.is_connected = True

    def command(self, *args):
        if not self.is_connected:
            return None
        try:
            return self.receive_response(self.send_command(args))
        except SerialException:
            self.close()
            self.is_connected = False
            return None

    def receive_response(self, expected_tag):
        if not expected_tag:
            return
        while True:
            cmd = LoggerCmd(self.__port)
            if cmd.tag == expected_tag or cmd.tag in ['ERR', 'INV']:
                self.callback('rx', cmd.cmd_str())
                return cmd.result()

    def send_command(self, args):
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
        if tag in DELAY_COMMANDS:
            time.sleep(2)
        return tag

    def close(self):
        if self.__port:
            self.__port.close()
        self.is_connected = False
