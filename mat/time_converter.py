from abc import ABC, abstractmethod
import numpy as np


EPOCH = np.datetime64('1970-01-01T00:00:00.000')


def create_time_converter(time_format):
    time_converters = {'iso8601': Iso8601,
                       'legacy': Legacy,
                       'posix': Posix,
                       'elapsed': Elapsed}
    return time_converters.get(time_format)()


class TimeConverter(ABC):
    @abstractmethod
    def header_str(self):
        pass  # pragma: no cover

    @abstractmethod
    def convert(self, time):
        pass


class Iso8601(TimeConverter):
    def header_str(self):
        return 'ISO 8601 Time'

    def convert(self, time):
        time_objects = EPOCH + (time * 1000).astype('timedelta64[ms]')
        time_strings = np.datetime_as_string(time_objects)
        return time_strings


class Legacy(Iso8601):
    def header_str(self):
        return 'Date,Time'

    def convert(self, time):
        time_strings = super().convert(time)
        # replace the "T" with a ","
        time_strings[..., None].view('U1')[..., 10] = ','
        return time_strings


class Posix(TimeConverter):
    def header_str(self):
        return 'POSIX Time'

    def convert(self, time):
        return ['{:0.3f}'.format(x) for x in time]


class Elapsed(TimeConverter):
    def __init__(self):
        self.start_time = None

    def header_str(self):
        return 'Elapsed Seconds'

    def convert(self, time):
        if self.start_time is None:
            self.start_time = time[0]
        return ['{:0.3f}'.format(x-self.start_time) for x in time]
