from mat.data_file_factory import load_data_file
from mat.data_product import data_product_factory
from mat.sensor import create_sensors, major_interval_info
from math import floor


def default_parameters():
    """
    If this were a stand alone dictionary, and not in a function, the user
    would need to remember to copy the dictionary each time as it is mutable
    """
    return {'output_directory': None,
            'file_name': None,
            'output_type': 'discrete',
            'output_format': 'csv',
            'average': True,
            'time_format': 'iso8601',
            'tilt_curve': None,
            'declination': 0,
            'split': None,
            'calibration': None,
            'overwrite': True}


class DataConverter:
    def __init__(self, path, parameters):
        self.path = path
        self.parameters = parameters
        self.source_file = None
        self.observers = []
        self._is_running = None

    def _load_source_file(self):
        if not self.source_file:
            self.source_file = load_data_file(self.path,
                                              self.parameters['calibration'])
        return self.source_file

    def cancel_conversion(self):
        self._is_running = False  # pragma: no cover

    def convert(self):
        self._is_running = True
        self._load_source_file()
        outputs = data_product_factory(self.path,
                                       self._build_sensors(),
                                       self.parameters)

        page_times = self.source_file.page_times()
        for i in range(self.source_file.n_pages()):
            if not self._is_running:
                break  # pragma: no cover
            page = self.source_file.page(i)
            self._write_to_outputs(outputs, page, page_times[i])
            percent = (i + 1) / self.source_file.n_pages() * 100
            self._update_observers(percent)

    def _build_sensors(self):
        header = self.source_file.header()
        seconds = self.source_file.seconds_per_page()
        # if there is only one data page, seconds has to be calculated
        if not seconds:
            major_interval, bytes = major_interval_info(header)
            seconds = floor((self.source_file.PAGE_SIZE
                             - self.source_file.mini_header_length())
                            / bytes) * major_interval
        return create_sensors(header,
                              self.source_file.calibration(),
                              seconds)

    def _write_to_outputs(self, outputs, page, page_time):
        for this_output in outputs:
            this_output.process_page(page, page_time)

    def _update_observers(self, percent):
        for observer in self.observers:
            observer(percent_done=percent)

    def register_observer(self, observer):
        self.observers.append(observer)

    def close_source(self):
        if self.source_file:
            self.source_file.close()

    def __del__(self):
        self.close_source()
