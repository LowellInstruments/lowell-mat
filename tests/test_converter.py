from unittest import TestCase
from numpy import array
from mat.converter import Converter
from mat.cubic_accelerometer import CubicAccelerometer
from mat.cubic_magnetometer import CubicMagnetometer
from mat.light import DEFAULT_PDA
from mat.linear_accelerometer import LinearAccelerometer
from mat.pressure import DEFAULT_PRA
from mat.temp_compensated_magnetometer import TempCompensatedMagnetometer
from mat.v3_calibration import V3Calibration
from utils import (
    calibration_from_file,
)


ZERO_ARRAY = array([0])
TEMP_ARRAY = array([1])
CUBIC_IDENTITY = array([[1, 2, 3],
                        [5, 6, 7],
                        [9, 10, 11]])
EXAMPLE_RAW_DATA = array([[1, 2, 3, 4],
                          [5, 6, 7, 8],
                          [9, 10, 11, 12]])
EXAMPLE_TEMP_ARRAY = array([1, 1, 1, 1])


class TestConverter(TestCase):
    def test_empty_calibration(self):
        with self.assertRaises(KeyError):
            Converter(V3Calibration({}))

    def test_calibrated_temperature(self):
        assert Converter(
            calibration_from_file("v3_calibration.txt")).temperature(
                TEMP_ARRAY).shape == (1, )

    def test_calibrated_pressure(self):
        assert Converter(
            calibration_from_file("v3_calibration.txt")).pressure(
            ZERO_ARRAY) == array([DEFAULT_PRA])

    def test_calibrated_light(self):
        assert Converter(
            calibration_from_file("v3_calibration.txt")).light(
            ZERO_ARRAY) == array([DEFAULT_PDA])

    def test_missing_accelerometer(self):
        assert Converter(
            calibration_from_file("v3_missing_tags.txt")).accelerometer(
                EXAMPLE_RAW_DATA) is None

    def test_calibrated_linear_accelerometer(self):
        converter = Converter(calibration_from_file("v2_linear_acc.txt"))
        assert isinstance(converter.accelerometer_converter,
                          LinearAccelerometer)
        assert converter.accelerometer(EXAMPLE_RAW_DATA).shape == (3, 4)

    def test_calibrated_cubic_accelerometer(self):
        converter = Converter(calibration_from_file("v3_calibration.txt"))
        assert isinstance(converter.accelerometer_converter,
                          CubicAccelerometer)
        assert converter.accelerometer(EXAMPLE_RAW_DATA).shape == (3, 4)

    def test_missing_magnetometer(self):
        assert Converter(
            calibration_from_file("v3_missing_tags.txt")).magnetometer(
            EXAMPLE_RAW_DATA) is None

    def test_calibrated_cubic_magnetometer(self):
        converter = Converter(calibration_from_file("v3_calibration.txt"))
        assert isinstance(converter.magnetometer_converter,
                          CubicMagnetometer)
        assert converter.magnetometer(EXAMPLE_RAW_DATA).shape == (3, 4)

    def test_calibrated_temp_comp_magnetometer_with_no_temp(self):
        converter = Converter(calibration_from_file("v3_temp_comp.txt"))
        assert isinstance(converter.magnetometer_converter,
                          TempCompensatedMagnetometer)
        assert converter.magnetometer(EXAMPLE_RAW_DATA).shape == (3, 4)

    def test_calibrated_temp_comp_magnetometer(self):
        converter = Converter(calibration_from_file("v3_temp_comp.txt"))
        assert isinstance(converter.magnetometer_converter,
                          TempCompensatedMagnetometer)
        assert converter.magnetometer(EXAMPLE_RAW_DATA,
                                      EXAMPLE_TEMP_ARRAY).shape == (3, 4)
