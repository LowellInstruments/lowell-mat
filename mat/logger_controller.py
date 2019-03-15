# GPLv3 License
# Copyright (c) 2018 Lowell Instruments, LLC, some rights reserved

from abc import ABC, abstractmethod
from datetime import datetime
import re
from mat.calibration_factories import calibration_from_string
from mat.converter import Converter
from mat.logger_info_parser import LoggerInfoParser
from mat.sensor_parser import SensorParser
from mat.utils import four_byte_int


FIRMWARE_VERSION_CMD = 'GFV'
CALIBRATION_CMD = 'RHS'
INTERVAL_TIME_CMD = 'GIT'
LOGGER_INFO_CMD = 'RLI'
LOGGER_SETTINGS_CMD = 'GLS'
PAGE_COUNT_CMD = 'GPC'
RESET_CMD = 'RST'
RUN_CMD = 'RUN'
SD_CAPACITY_CMD = 'CTS'
SD_FILE_SIZE_CMD = 'FSZ'
SD_FREE_SPACE_CMD = 'CFS'
SENSOR_READINGS_CMD = 'GSR'
SERIAL_NUMBER_CMD = 'GSN'
START_TIME_CMD = 'GST'
STATUS_CMD = 'STS'
STOP_CMD = 'STP'
STOP_WITH_STRING_CMD = 'SWS'
SET_TIME_CMD = 'STM'
TIME_CMD = 'GTM'
DEL_FILE_CMD = 'DEL'

SIMPLE_CMDS = [
    FIRMWARE_VERSION_CMD,
    INTERVAL_TIME_CMD,
    PAGE_COUNT_CMD,
    RUN_CMD,
    SERIAL_NUMBER_CMD,
    START_TIME_CMD,
    STATUS_CMD,
    STOP_CMD,
    TIME_CMD,
]

DELAY_COMMANDS = [
    RUN_CMD,
    STOP_CMD
]


class LoggerController(ABC):
    def __init__(self, address):
        self.address = address
        self.__callback = {}
        self.calibration = None
        self.converter = None

    @abstractmethod
    def open(self):
        pass  # pragma: no cover

    @abstractmethod
    def close(self):
        pass  # pragma: no cover

    @abstractmethod
    def command(self, *args):
        pass  # pragma: no cover

    def __enter__(self):
        if self.open():
            return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def callback(self, key, cmd_str):
        if key in self.__callback:
            self.__callback[key](cmd_str)

    def load_calibration(self):
        cal_string = self._multi_read(CALIBRATION_CMD, 10, 38)
        self.calibration = calibration_from_string(cal_string)
        self.converter = Converter(self.calibration)

    def logger_info(self):
        li_string = self._multi_read(LOGGER_INFO_CMD, 3, 42)
        if li_string and not all([c == 255 for c in
                                  bytes(li_string, encoding='IBM437')]):
            return LoggerInfoParser(li_string).info()

    def _multi_read(self, read_command, n_reads, read_size):
        in_str = ''
        for i in range(n_reads):
            read_address = i * read_size
            read_address = '%04X' % read_address
            read_address = read_address[2:4] + read_address[0:2]
            read_length = '%02X' % read_size
            command_str = read_address + read_length
            this_read = self.command(read_command, command_str)
            if this_read:
                in_str += this_read
            else:
                break
        return in_str

    def get_logger_settings(self):
        gls_string = self.command(LOGGER_SETTINGS_CMD)
        if not gls_string:
            return {}
        logger_settings = {
            'TMP': gls_string[0:2] == '01',
            'ACL': gls_string[2:4] == '01',
            'MGN': gls_string[4:6] == '01',
            'TRI': four_byte_int(gls_string[6:10]),
            'ORI': four_byte_int(gls_string[10:14]),
            'BMR': int(gls_string[14:16], 16),
            'BMN': four_byte_int(gls_string[16:20]),
        }

        if len(gls_string) == 30:
            logger_settings.update({
                'PRS': gls_string[20:22] == '01',
                'PHD': gls_string[22:24] == '01',
                'PRR': int(gls_string[24:26], 16),
                'PRN': four_byte_int(gls_string[26:30]),
            })

        return logger_settings

    def stop_with_string(self, data):
        return self.command(STOP_WITH_STRING_CMD, data)

    def get_sensor_readings(self):
        sensor_string = self.command(SENSOR_READINGS_CMD)
        if not self.converter:
            self.load_calibration()
        return SensorParser(sensor_string, self.converter).sensors()

    def get_sd_capacity(self):
        return _extract_sd_kb(self.command(SD_CAPACITY_CMD))

    def get_sd_free_space(self):
        return _extract_sd_kb(self.command(SD_FREE_SPACE_CMD))

    def get_sd_file_size(self):
        fsz = self.command(SD_FILE_SIZE_CMD)
        return int(fsz) if fsz else None

    def sync_time(self):
        formatted_now = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        return self.command(SET_TIME_CMD, formatted_now)

    def set_callback(self, event, callback):
        self.__callback[event] = callback

    def __del__(self):
        self.close()

    def check_time(self):
        logger_time = self.command(TIME_CMD)
        logger_time = logger_time[6:]
        logger_time = datetime.strptime(logger_time, '%Y/%m/%d %H:%M:%S')
        local_time = datetime.now()
        return (local_time - logger_time).total_seconds()


def _extract_sd_kb(data):
    if not data:
        return None
    regexp = re.search('([0-9]+)KB', data)
    if regexp:
        return int(regexp.group(1))
    else:
        return None


class CommunicationError(Exception):
    pass
