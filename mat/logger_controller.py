# GPLv3 License
# Copyright (c) 2018 Lowell Instruments, LLC, some rights reserved

import datetime
import re
from mat.calibration_factories import calibration_from_string
from mat.converter import Converter
from mat.logger_info_parser import LoggerInfoParser
from mat.sensor_parser import SensorParser
from mat.utils import four_byte_int
from abc import ABC, abstractmethod


# TODO: the "command" method is in DIRE shape! Please, please fix it!
# TODO: currently the logger class is blocking. Needs to be rewritten
# TODO: if calibration isn't loaded, gsr crashes.
# TODO: A default value needs to be loaded.


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
SYNC_TIME_CMD = 'STM'
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


class LoggerController(ABC):
    def __init__(self):
        self.logger_info = {}
        self.calibration = None
        self.converter = None

    @abstractmethod
    def open(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def command(self, *args):
        pass

    def load_calibration(self):
        read_size = 38
        cal_string = ''

        # Load the entire HS from the logger
        for i in range(10):
            read_address = i * read_size
            read_address = '%04X' % read_address
            read_address = read_address[2:4] + read_address[0:2]
            read_length = '%02X' % read_size
            command_str = read_address + read_length
            in_str = self.command(CALIBRATION_CMD, command_str)
            if in_str:
                cal_string += in_str
            else:
                break

        self.calibration = calibration_from_string(cal_string)
        self.converter = Converter(self.calibration)

    def load_logger_info(self):
        read_size = 42
        li_string = ''
        for i in range(3):
            read_address = i*read_size
            read_address = '%04x' % read_address
            read_address = read_address[2:4] + read_address[0:2]
            read_length = '%02x' % read_size
            command_str = read_address + read_length
            li_string += self.command(LOGGER_INFO_CMD, command_str)
        if li_string and not all([c == 255 for c in
                                  bytes(li_string, encoding='IBM437')]):
            self.logger_info = LoggerInfoParser(li_string).info()

    def get_timestamp(self):
        """ Return posix timestamp """
        date_string = self.command(TIME_CMD)
        epoch = datetime.datetime(1970, 1, 1)  # naive datetime format
        logger_time = datetime.datetime.strptime(date_string,
                                                 '%Y/%m/%d %H:%M:%S')
        return (logger_time-epoch).total_seconds()

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
        date_time_obj = datetime.datetime.now()
        formatted_string = date_time_obj.strftime('%Y/%m/%d %H:%M:%S')
        return self.command(SYNC_TIME_CMD, formatted_string)

    def delete_file(self, name):
        self.command(DEL_FILE_CMD, name)

    def start_deployment(self):
        return self.command(RUN_CMD)

    def stop_deployment(self):
        return self.command(STOP_CMD)

    def get_status(self):
        return self.command(STATUS_CMD)

    def get_time(self):
        return datetime.datetime.strptime(
            self.command(TIME_CMD)[6:], '%Y/%m/%d %H:%M:%S')

    def get_serial_number(self):
        return self.command(SERIAL_NUMBER_CMD)

    def get_firmware_version(self):
        return self.command(FIRMWARE_VERSION_CMD)

    def check_time(self):
        pre_time = self.get_time()
        synced = False
        if abs(datetime.datetime.now() - pre_time).total_seconds() > 60:
            synced = True
            self.sync_time()
            post_time = self.get_time()
        if synced:
            rv = "\n\tTime synced from {} to {}".format(pre_time, post_time)
        else:
            rv = "\n\tLogger Time is {}".format(pre_time)
        return rv



def _extract_sd_kb(data):
    if not data:
        return None
    regexp = re.search('([0-9]+)KB', data)
    if regexp:
        return int(regexp.group(1))
    else:
        return None
