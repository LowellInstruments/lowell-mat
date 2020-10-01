# GPLv3 License
# Copyright (c) 2018 Lowell Instruments, LLC, some rights reserved

from mat.header import Header
from mat.calibration_factories import calibration_from_string
from abc import ABC, abstractmethod


FULL_HEADER_LENGTH = 1000


class SensorDataFile(ABC):
    def __init__(self, file_path, calibration=None):
        self._file_path = file_path
        self._file = None
        self._header = None
        self.header_error = None
        self._calibration = calibration
        self._page_times = None
        self._cached_page = None
        self._cached_page_n = None
        self._file_size = None
        self._mini_header_length = None
        self._samples_per_page = None
        self._n_pages = None
        self._n_pages = self.n_pages()
        if self.data_bytes() == 0:
            raise NoDataError('There is no data in the file')

    @property
    @abstractmethod
    def data_start(self):
        pass  # pragma: no cover

    @abstractmethod
    def _load_page(self, i):
        pass  # pragma: no cover

    @abstractmethod
    def mini_header_length(self):
        pass  # pragma: no cover

    @abstractmethod
    def n_pages(self):
        pass  # pragma: no cover

    @abstractmethod
    def page_times(self):
        pass  # pragma: no cover

    def page(self, i):
        if self._cached_page_n == i:
            return self._cached_page
        self._cached_page_n = i
        self._cached_page = self._load_page(i)
        return self._cached_page

    def header(self):
        if self._header:
            return self._header
        self._header = Header(self._read_full_header())
        self._header.parse_header()
        return self._header

    def calibration(self):
        if self._calibration:
            return self._calibration
        full_header = self._read_full_header()
        self._calibration = calibration_from_string(full_header)
        return self._calibration

    def seconds_per_page(self):
        if self.n_pages() > 1:
            return self.page_times()[1] - self.page_times()[0]
        else:
            return None

    def file(self):
        if self._file is None:
            self._file = open(self._file_path, 'rb')
        return self._file

    def file_size(self):
        if self._file_size:
            return self._file_size
        file_pos = self.file().tell()
        self.file().seek(0, 2)
        self._file_size = self.file().tell()
        self.file().seek(file_pos)
        return self._file_size

    def data_bytes(self):
        return self.file_size() - self.data_start - self.mini_header_length()

    def _read_full_header(self):
        file_position = self.file().tell()
        self.file().seek(0)
        full_header = self.file().read(FULL_HEADER_LENGTH).decode('IBM437')
        self.file().seek(file_position)
        return full_header

    def close(self):
        if self._file:
            self._file.close()
        self._file = None

    def __del__(self):
        if self._file:
            self.close()


class NoDataError(Exception):
    pass
