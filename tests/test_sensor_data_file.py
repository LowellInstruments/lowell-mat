from unittest import TestCase
from mat.data_file_factory import load_data_file, WrongFileTypeError
from mat.lid_data_file import LidDataFile
from tests.utils import reference_file
from mat.v3_calibration import V3Calibration
from mat.header import Header
from mat.sensor_data_file import NoDataError


class TestSensorDataFile(TestCase):
    def test_create_lid(self):
        data_file = load_data_file(reference_file('test.lid'))
        assert isinstance(data_file, LidDataFile)

    def test_create_bad_file(self):
        with self.assertRaises(WrongFileTypeError):
            load_data_file(reference_file('test.xyz'))

    def test_n_pages_lid(self):
        data_file = load_data_file(reference_file('test.lid'))
        assert data_file.n_pages() == 1

    def test_load_page_twice(self):
        data_file = load_data_file(reference_file('test.lid'))
        data_file.page(0)
        data_file.page(0)

    def test_load_calibration_twice(self):
        data_file = load_data_file(reference_file('test.lid'))
        cal = data_file.calibration()
        cal = data_file.calibration()
        assert type(cal) == V3Calibration

    def test_load_header(self):
        data_file = load_data_file(reference_file('test.lid'))
        header = data_file.header()
        header = data_file.header()
        header.parse_header()
        assert type(header) == Header

    def test_seconds_per_page_partial_page(self):
        data_file = load_data_file(reference_file('test.lid'))
        data_file.seconds_per_page()

    def test_read_nonexistent_page(self):
        data_file = load_data_file(reference_file('test.lid'))
        with self.assertRaises(ValueError):
            data_file.page(3)

    def test_mhs_wrong_place(self):
        with self.assertRaises(ValueError):
            load_data_file(reference_file('mhs_wrong_place.lid'))

    def test_no_data_in_lid_file(self):
        with self.assertRaises(NoDataError):
            load_data_file(reference_file('No_Channels_Enabled.lid'))
