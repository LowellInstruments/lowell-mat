from unittest import TestCase
from mat.data_file_factory import create_data_file
from mat.lid_data_file import LidDataFile
from mat.lis_data_file import LisDataFile
from tests.utils import reference_file
from mat.v3_calibration import V3Calibration
from mat.header import Header


class TestSensorDataFile(TestCase):
    def test_create_lid(self):
        data_file = create_data_file(reference_file('test.lid'))
        assert isinstance(data_file, LidDataFile)

    def test_create_lis(self):
        data_file = create_data_file(reference_file('test.lis'))
        assert isinstance(data_file, LisDataFile)

    def test_create_bad_file(self):
        with self.assertRaises(ValueError):
            create_data_file(reference_file('test.xyz'))

    def test_n_pages_lid(self):
        data_file = create_data_file(reference_file('test.lid'))
        assert data_file.n_pages() == 1

    def test_n_pages_lis(self):
        data_file = create_data_file(reference_file('test.lis'))
        assert data_file.n_pages() == 1

    def test_sensors(self):
        data_file = create_data_file(reference_file('test.lid'))
        data_file.sensors()

    def test_load_page(self):
        data_file = create_data_file(reference_file('test.lid'))
        data_file.page(0)
        pass

    def test_load_calibration(self):
        data_file = create_data_file(reference_file('test.lid'))
        cal = data_file.calibration()
        cal = data_file.calibration()
        assert type(cal) == V3Calibration

    def test_load_header(self):
        data_file = create_data_file(reference_file('test.lid'))
        header = data_file.header()
        header = data_file.header()
        header.parse_header()
        assert type(header) == Header

    def test_seconds_per_page_partial_page(self):
        data_file = create_data_file(reference_file('test.lid'))
        data_file.seconds_per_page()
        pass
