# GPLv3 License
# Copyright (c) 2018 Lowell Instruments, LLC, some rights reserved

from mat.utils import cut_out, parse_tags


DATA_FILE_START = 'DFS'
DEPLOYMENT_NUMBER = 'DPL'
IS_ACCELEROMETER = 'ACL'
IS_LED = 'LED'
IS_MAGNETOMETER = 'MGN'
IS_PHOTO_DIODE = 'PHD'
IS_PRESSURE = 'PRS'
IS_TEMPERATURE = 'TMP'
ORIENTATION_BURST_COUNT = 'BMN'
ORIENTATION_BURST_RATE = 'BMR'
ORIENTATION_INTERVAL = 'ORI'
PRESSURE_BURST_COUNT = 'PRN'
PRESSURE_BURST_RATE = 'PRR'
START_TIME = 'CLK'
STATUS = 'STS'
TEMPERATURE_INTERVAL = 'TRI'
HEADER_START_TAG = 'HDS\r\n'
HEADER_END_TAG = 'HDE\r\n'

TYPE_INT = [
    DEPLOYMENT_NUMBER,
    ORIENTATION_BURST_COUNT,
    ORIENTATION_BURST_RATE,
    ORIENTATION_INTERVAL,
    PRESSURE_BURST_COUNT,
    PRESSURE_BURST_RATE,
    STATUS,
    TEMPERATURE_INTERVAL
    ]

TYPE_BOOL = [
    IS_ACCELEROMETER,
    IS_LED,
    IS_MAGNETOMETER,
    IS_PHOTO_DIODE,
    IS_PRESSURE,
    IS_TEMPERATURE,
]

TYPE_HEX = [DATA_FILE_START]

CONVERSION_FUNC = [
    (TYPE_INT, lambda x: int(x)),
    (TYPE_BOOL, lambda x: x == '1'),
    (TYPE_HEX, lambda x: int(x, 16))
]


def header_factory(file_path):
    with open(file_path, 'rb') as fid:
        header_string = fid.read(500).decode('IBM437')
    return Header(header_string)


class Header:
    def __init__(self, header_string):
        self.header_string = header_string
        self._header = {}

    def tag(self, tag):
        return self._header.get(tag)

    def parse_header(self):
        header_string = self._crop_header_block(self.header_string)
        self._validate_header_block(header_string)
        header_string = self._remove_logger_info(header_string)
        header_string = self._remove_header_tags(header_string)
        header_dict = parse_tags(header_string)
        self._header = self._convert_to_type(header_dict)

    def _crop_header_block(self, header_block):
        start_index = header_block.find(HEADER_START_TAG)
        end_index = header_block.find(HEADER_END_TAG)
        if start_index == -1 or end_index == -1:
            raise ValueError('Header tags missing')
        return header_block[start_index:end_index+len(HEADER_END_TAG)]

    def _remove_logger_info(self, header_string):
        lis = header_string.find('LIS')
        lie = header_string.find('LIE')
        if lis > -1 and lie > -1:
            return cut_out(header_string, lis, lie+5)
        else:
            return header_string

    def _remove_header_tags(self, header_string):
        for tag_to_remove in ['HDS', 'HDE', 'MHS', 'MHE']:
            index = header_string.find(tag_to_remove)
            header_string = cut_out(header_string, index, index+5)
        return header_string

    def _validate_header_block(self, header_string):
        mandatory_tags = ['MHS', 'MHE']
        for tag in mandatory_tags:
            if tag not in header_string:
                raise ValueError(tag + ' tag missing in header')

    def _convert_to_type(self, dictionary):
        for tag, value in dictionary.items():
            converted_value = self._convert_value(tag, value)
            if converted_value is not None:
                dictionary[tag] = converted_value
        return dictionary

    def _convert_value(self, tag, value):
        for type_list, conversion_func in CONVERSION_FUNC:
            if tag in type_list:
                return conversion_func(value)

    def major_interval(self):
        orientation_interval = self.tag(ORIENTATION_INTERVAL) or 0
        temperature_interval = self.tag(TEMPERATURE_INTERVAL) or 0
        return max(orientation_interval, temperature_interval)
