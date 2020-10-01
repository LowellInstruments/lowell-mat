from unittest import TestCase
from mat.calibration_factories import (
    make_from_calibration_file,
)
from mat.v3_calibration import V3Calibration
from mat.data_file_factory import load_data_file
from tests.utils import (
    calibration_from_file,
    reference_file,
)
from math import isclose


class TestHeader(TestCase):
    def test_load_v2_calibration(self):
        expected_dict = {'RVN': 2.,
                         'TMO': 0.,
                         'TMR': 10000.,
                         'TMA': 0.00112381007,
                         'TMB': 0.00023494571,
                         'TMC': 0.00000008484,
                         'AXX': -0.243,
                         'AXY': -0.006,
                         'AXZ': -0.002,
                         'AXV': -0.077,
                         'AXC': 0.000,
                         'AYX': 0.004,
                         'AYY': -0.258,
                         'AYZ': -0.000,
                         'AYV': 0.014,
                         'AYC': -0.000,
                         'AZX': 0.000,
                         'AZY': -0.000,
                         'AZZ': -0.264,
                         'AZV': -0.007,
                         'AZC': -0.000,
                         'MXX': 0.166,
                         'MXY': 0.005,
                         'MXZ': -0.001,
                         'MXV': 3439.7,
                         'MYX': -0.004,
                         'MYY': 0.164,
                         'MYZ': -0.008,
                         'MYV': 974.9,
                         'MZX': 0.001,
                         'MZY': -0.011,
                         'MZZ': 0.155,
                         'MZV': -287.3}
        cal = calibration_from_file("v2_calibration.txt")
        cal_is_close(cal.coefficients, expected_dict)

    def test_load_v3_calibration(self):
        expected_dict = {'RVN': 3.,
                         'TMO': 0.,
                         'TMR': 10000.,
                         'TMA': 0.0011238100354,
                         'TMB': 0.0002349457073,
                         'TMC': 0.0000000848361,
                         'AXX': -0.247291,
                         'AXY': 0.001682,
                         'AXZ': -0.001556,
                         'AXV': -0.052634,
                         'AXC': 0.000100,
                         'AYX': 0.001510,
                         'AYY': -0.265206,
                         'AYZ': -0.002301,
                         'AYV': -0.022662,
                         'AYC': -0.000011,
                         'AZX': 0.001809,
                         'AZY': 0.002049,
                         'AZZ': -0.274052,
                         'AZV': -0.041830,
                         'AZC': 0.000007,
                         'MXX': 1.126303,
                         'MXY': 0.005581,
                         'MXZ': -0.022390,
                         'MXV': -625.806650,
                         'MYX': -0.008780,
                         'MYY': 1.097295,
                         'MYZ': -0.009585,
                         'MYV': -1787.425019,
                         'MZX': -0.008803,
                         'MZY': 0.007365,
                         'MZZ': 1.101313,
                         'MZV': -2089.487206,
                         'MRF': 24.961058}
        cal = calibration_from_file("v3_calibration.txt")
        cal_is_close(cal.coefficients, expected_dict)

    def test_load_v3_from_data_file(self):
        load_data_file(reference_file('test.lid'))

    def test_load_v2_from_data_file(self):
        load_data_file(reference_file('v2_datafile.lid'))

    def test_empty_calibration(self):
        load_data_file(reference_file('empty_calibration.lid'))

    def test_make_v2_serial_string(self):
        expected_str = 'RVN12TMO30.0TMR710000.0TMAd0.00112381007' \
                       'TMBd0.00023494571TMC98.484e-08AXX6-0.243' \
                       'AXY6-0.006AXZ6-0.002AXV6-0.077AXC30.0AYX50.004' \
                       'AYY6-0.258AYZ4-0.0AYV50.014AYC4-0.0AZX30.0AZY4-0.0' \
                       'AZZ6-0.264AZV6-0.007AZC4-0.0MXX50.166MXY50.005' \
                       'MXZ6-0.001MXV63439.7MYX6-0.004MYY50.164MYZ6-0.008' \
                       'MYV5974.9MZX50.001MZY6-0.011MZZ50.155MZV6-287.3'
        file = reference_file('v2_calibration.txt')
        cal = make_from_calibration_file(file)
        serial_str = ''.join(cal.make_serial_string())
        assert serial_str == expected_str

    def test_make_v3_serial_string(self):
        expected_str = 'RVN13TMO!!!!!TMR7N=YnTMA3g37`TMB3HeWDTMC1U\\q^' \
                       'AXX^3r#pAXY3o"WbAXZ]$(%<AXV]iUNrAXC371Q,AYX3lUq+' \
                       'AYY^5\'fKAYZ],&@5AYV]XanMAYC[l%)^AZX3pdq^AZY3sJ+' \
                       'AAZZ^5PmKAZV]dm-)AZC2WI`EMXX5EIA\'MXY41=3(MXZ]XM[/' \
                       'MXV`#NikMYX]FW\\@MYY5E\'\\6MYZ]H%>OMYV`8>F#' \
                       'MZX]F[-YMZY47Q=5MZZ5E,?gMZV`<)CMMRF6-$2o'

        file = reference_file('v3_calibration.txt')
        cal = make_from_calibration_file(file)
        serial_str = ''.join(cal.make_serial_string())
        assert serial_str == expected_str

    def test_missing_hse(self):
        with self.assertRaises(ValueError):
            sdf = load_data_file(reference_file('missing_hse.lid'))
            sdf.calibration()

    def test_calibration_missing_value(self):
        with self.assertRaises(ValueError):
            file = reference_file('v3_calibration_missing_value.txt')
            make_from_calibration_file(file)

    def test_empty_cal_string(self):
        with self.assertRaises(ValueError):
            V3Calibration.load_from_string('')

    def test_bad_cal_string(self):
        with self.assertRaises(ValueError):
            V3Calibration.load_from_string('Bad Calibration String')

    def test_missing_hss_from_calibration(self):
        """
        HSE is present, but HSS is missing
        """
        with self.assertRaises(ValueError):
            data_file = load_data_file(reference_file('missing_hss.lid'))
            data_file.calibration()


def cal_is_close(dict1, dict2):
    # Compare two dicts containing floating point numbers
    assert set(dict1.keys()) == set(dict2.keys())
    for key in dict1.keys():
        assert isclose(dict1[key], dict2[key], abs_tol=0.001)
