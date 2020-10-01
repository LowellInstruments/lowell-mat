# GPLv3 License
# Copyright (c) 2018 Lowell Instruments, LLC, some rights reserved

"""
Read/write calibration data from a logger or file

Calibration data is found in .lid and .lis files immediately proceeding
the header. The calibration data is found within the HSS and HSE tags. Each
calibration value is on a separate line.

There have been three different versions of calibration coefficients since
the introduction of the MAT logger. This module is responsible for managing
how the various versions are read and written.

V1 Calibration isn't found "in the wild" so it will be ignored

V2 Calibration is stored in the data file in the following way:
3 letter tag, 1 hex number for length, ascii numeric value
eg. AXX61.1201 -- AXX is the tag, 6 is the data length, 1.1201 is the value

V3 Calibration is stored in the data file in the following way:
3 letter tag, 5 byte ascii-85 encoded single precision float
eg. AXX^3r#p -- AXX is the tag, and "^3r#p" is -0.247291 encoded in ascii85
"""

from abc import ABC, abstractmethod
from mat.utils import trim_start


class Calibration(ABC):
    @abstractmethod
    def __init__(self, coefficients):
        """
        coefficients is a dictionary passed to the subclasses with tags as keys
        and values as strings. The subclasses must convert the string values
        to numeric values.
        The V2 __init__ needs to convert plain text ascii to float
        The V3 __init__ needs to convert five ascii85 characters to float
        """
        pass  # pragma: no cover

    @classmethod
    def load_from_string(cls, calibration_string):
        cls._validate_string(calibration_string)
        # Trim HSS (3 characters) from start of calibration string
        calibration_string = trim_start(calibration_string, 3)
        coefficients = {}
        for tag, value in cls._parse_tag_value_pairs(calibration_string):
            coefficients[tag] = value
        return cls(coefficients)

    @staticmethod
    @abstractmethod
    def _parse_tag_value_pairs(calibration_string):
        pass  # pragma: no cover

    @abstractmethod
    def make_serial_string(self):
        """
        This generator function formats the host storage dict for writing
        to the logger.
        """
        pass  # pragma: no cover

    @staticmethod
    def _validate_string(calibration_string):
        if not calibration_string:
            raise ValueError('Calibration string is empty')
        if calibration_string.find('HSE') == -1:
            raise ValueError('Host storage string must contain HSE tag')

    @abstractmethod
    def write_to_file(self, path):
        pass  # pragma: no cover
