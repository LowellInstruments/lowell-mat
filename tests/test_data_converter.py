# GPLv3 License
# Copyright (c) 2018 Lowell Instruments, LLC, some rights reserved


from unittest import TestCase
from mat.data_converter import DataConverter, default_parameters
from mat.data_file_factory import load_data_file, WrongFileTypeError
from tests.utils import reference_file, compare_files
from tests.utils import assert_compare_expected_file
from mat.tiltcurve import TiltCurve
from mat.calibration_factories import make_from_calibration_file


class TestDataConverter(TestCase):
    def test_creation(self):
        assert DataConverter('no file', default_parameters())

    def test_factory_no_filename(self):
        with self.assertRaises(WrongFileTypeError):
            load_data_file('')

    def test_conversion(self):
        full_file_path = reference_file('test.lid')
        parameters = default_parameters()
        parameters['average'] = False
        converter = DataConverter(full_file_path, parameters)
        converter.convert()
        assert_compare_expected_file('test_AccelMag.csv')
        assert_compare_expected_file('test_Temperature.csv')

    def test_data_converter_creation(self):
        full_file_path = reference_file("test.lid")
        parameters = default_parameters()
        parameters['output_format'] = 'csv'
        DataConverter(full_file_path, parameters)

    def test_observer(self):
        full_file_path = reference_file('test.lid')
        parameters = default_parameters()
        parameters['average'] = False
        dc = DataConverter(full_file_path, parameters)
        dc.register_observer(lambda percent_done: None)
        dc.convert()
        assert_compare_expected_file('test_AccelMag.csv')
        assert_compare_expected_file('test_Temperature.csv')

    def test_convert_legacy(self):
        full_file_path = reference_file('test.lid')
        parameters = default_parameters()
        parameters['time_format'] = 'legacy'
        dc = DataConverter(full_file_path, parameters)
        dc.convert()
        assert_compare_expected_file('test_AccelMag.csv',
                                     'test_AccelMag-legacy.csv.expect')
        assert_compare_expected_file('test_Temperature.csv',
                                     'test_Temperature-legacy.csv.expect')

    def test_current(self):
        full_file_path = reference_file('test.lid')
        tilt_file_path = reference_file('tiltcurve/TCM-1, 1BalSalt.cal')
        tilt_curve = TiltCurve(tilt_file_path)
        parameters = default_parameters()
        parameters['output_type'] = 'current'
        parameters['tilt_curve'] = tilt_curve
        dc = DataConverter(full_file_path, parameters)
        dc.convert()
        assert_compare_expected_file('test_Current.csv')
        assert_compare_expected_file('test_Temperature.csv')

    def test_compass(self):
        full_file_path = reference_file('test.lid')
        parameters = default_parameters()
        parameters['output_type'] = 'compass'
        dc = DataConverter(full_file_path, parameters)
        dc.convert()
        compare_files(reference_file('test_Heading.csv'),
                      reference_file('test_Heading_GS.txt'))

    def test_unsupported_format(self):
        full_file_path = reference_file('test.lid')
        parameters = default_parameters()
        parameters['output_format'] = 'unsupported'
        with self.assertRaises(ValueError):
            DataConverter(full_file_path, parameters).convert()

    def test_temp_comp_magnetometer(self):
        full_file_path = reference_file('TCM1_Calibrate_(0).lid')
        dc = DataConverter(full_file_path, default_parameters())
        dc.convert()
        assert_compare_expected_file('TCM1_Calibrate_(0)_AccelMag.csv')
        assert_compare_expected_file('TCM1_Calibrate_(0)_Temperature.csv')

    def test_convert_w_posix_time(self):
        full_file_path = reference_file('test.lid')
        parameters = default_parameters()
        parameters['time_format'] = 'posix'
        dc = DataConverter(full_file_path, parameters)
        dc.convert()
        assert_compare_expected_file('test_AccelMag.csv',
                                     'test_AccelMag-posix.csv.expect')
        assert_compare_expected_file('test_Temperature.csv',
                                     'test_Temperature-posix.csv.expect')

    def test_convert_w_elapsed_time(self):
        full_file_path = reference_file('test.lid')
        parameters = default_parameters()
        parameters['time_format'] = 'elapsed'
        dc = DataConverter(full_file_path, parameters)
        dc.convert()
        assert_compare_expected_file('test_AccelMag.csv',
                                     'test_AccelMag-elapsed.csv.expect')
        assert_compare_expected_file('test_Temperature.csv',
                                     'test_Temperature-elapsed.csv.expect')

    def test_current_no_accel(self):
        full_file_path = reference_file('temp_mag_no_accel.lid')
        parameters = default_parameters()
        parameters['output_type'] = 'current'
        dc = DataConverter(full_file_path, parameters)
        with self.assertRaises(ValueError):
            dc.convert()

    def test_accel_mag_no_temp(self):
        full_file_path = reference_file('accel_mag_no_temp.lid')
        dc = DataConverter(full_file_path, default_parameters())
        dc.convert()
        assert_compare_expected_file('accel_mag_no_temp_AccelMag.csv')

    def test_custom_calibration(self):
        full_file_path = reference_file('custom_cal/test.lid')
        cal_path = reference_file('custom_cal/hoststorage_default.txt')
        calibration = make_from_calibration_file(cal_path)
        parameters = default_parameters()
        parameters['calibration'] = calibration
        parameters['average'] = False
        dc = DataConverter(full_file_path, parameters)
        dc.convert()
        compare_files(reference_file('custom_cal/test_AccelMag.csv'),
                      reference_file('custom_cal/test_default_hs_MA.txt'))

    def test_yaw_pitch_roll(self):
        full_file_path = reference_file('test.lid')
        parameters = default_parameters()
        parameters['output_type'] = 'ypr'
        dc = DataConverter(full_file_path, parameters)
        dc.convert()
        compare_files(reference_file('test_YawPitchRoll.csv'),
                      reference_file('test_ypr_GS.txt'))

    def test_specify_file_name(self):
        full_file_path = reference_file('test.lid')
        parameters = default_parameters()
        parameters['file_name'] = 'calley'
        dc = DataConverter(full_file_path, parameters)
        dc.convert()
        compare_files(reference_file('calley_AccelMag.csv'),
                      reference_file('test_AccelMag-posix.csv.expect'))
        compare_files(reference_file('calley_Temperature.csv'),
                      reference_file('test_Temperature-posix.csv.expect'))
