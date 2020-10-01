from unittest import TestCase
from numpy import array
from numpy.testing import assert_array_almost_equal
from mat.converter import Converter
from mat.cubic_accelerometer import CubicAccelerometer
from mat.cubic_magnetometer import CubicMagnetometer
from mat.light import DEFAULT_PDA
from mat.linear_accelerometer import LinearAccelerometer
from mat.temp_compensated_magnetometer import TempCompensatedMagnetometer
from mat.binary_coded_decimal import BinaryCodedDecimal
from mat.v3_calibration import V3Calibration
from tests.utils import calibration_from_file
from mat.temperature import ZERO_KELVIN


EXAMPLE_RAW_DATA = array([[1, 2, 3, 4],
                          [5, 6, 7, 8],
                          [9, 10, 11, 12]])
EXAMPLE_TEMP_ARRAY = array([1, 1, 1, 1])
CUBIC_ACCELEROMETER_EXPECTATION = array(
    [[-0.052881, -0.053123, -0.053364, -0.053605],
     [-0.023976, -0.024236, -0.024496, -0.024755],
     [-0.044227, -0.044491, -0.044755, -0.045019]])
CUBIC_MAGNETOMETER_EXPECTATION = array(
    [[-667.08790764,  -665.97841294,  -664.86891823,  -663.75942353],
     [-1930.41903643, -1929.34010623, -1928.26117604, -1927.18224584],
     [-2298.89591205, -2297.79603673, -2296.69616142, -2295.59628611]])
LINEAR_ACCELEROMETER_EXPECTATION = array(
    [[-0.000977, -0.001953, -0.00293, -0.003906],
     [-0.004883, -0.005859, -0.006836, -0.007812],
     [-0.008789, -0.009766, -0.010742, -0.011719]])
TCM_EXPECTATION = array(
    [[-448.188964,  -446.993222,  -445.79748,  -444.601739],
     [-5258.577008, -5257.446861, -5256.316713, -5255.186566],
     [-4588.130654, -4586.98616, -4585.841665, -4584.697171]])
TCM_NO_TEMP_EXPECTATION = array(
    [[-382.623668,  -381.427926,  -380.232185,  -379.036443],
     [-5052.676622, -5051.546475, -5050.416327, -5049.28618],
     [-4424.023578, -4422.879083, -4421.734589, -4420.590094]])
TEMP_ARRAY = array([1])
TEMPERATURE_EXPECTATION = array([1194.08902837])
ZERO_ARRAY = array([0])


class TestConverter(TestCase):
    def test_empty_calibration(self):
        with self.assertRaises(KeyError):
            Converter(V3Calibration({}))

    def test_calibrated_temperature(self):
        assert_array_almost_equal(Converter(
            calibration_from_file("v3_calibration.txt")).temperature(
                TEMP_ARRAY), TEMPERATURE_EXPECTATION)

    def test_65535_temperature(self):
        assert_array_almost_equal(Converter(
            calibration_from_file("v3_calibration.txt")).temperature(
            65535), ZERO_KELVIN)

    def test_calibrated_pressure(self):
        assert Converter(
            calibration_from_file("v3_calibration.txt")).pressure(
                ZERO_ARRAY) == array([2.068427184])

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
        assert_array_almost_equal(converter.accelerometer(EXAMPLE_RAW_DATA),
                                  LINEAR_ACCELEROMETER_EXPECTATION)

    def test_calibrated_cubic_accelerometer(self):
        converter = Converter(calibration_from_file("v3_calibration.txt"))
        assert isinstance(converter.accelerometer_converter,
                          CubicAccelerometer)
        assert_array_almost_equal(converter.accelerometer(EXAMPLE_RAW_DATA),
                                  CUBIC_ACCELEROMETER_EXPECTATION)

    def test_missing_magnetometer(self):
        assert Converter(
            calibration_from_file("v3_missing_tags.txt")).magnetometer(
            EXAMPLE_RAW_DATA) is None

    def test_calibrated_cubic_magnetometer(self):
        converter = Converter(calibration_from_file("v3_calibration.txt"))
        assert isinstance(converter.magnetometer_converter,
                          CubicMagnetometer)
        assert_array_almost_equal(converter.magnetometer(EXAMPLE_RAW_DATA),
                                  CUBIC_MAGNETOMETER_EXPECTATION)

    def test_calibrated_temp_comp_magnetometer_with_no_temp(self):
        converter = Converter(calibration_from_file("v3_temp_comp.txt"))
        assert isinstance(converter.magnetometer_converter,
                          TempCompensatedMagnetometer)
        assert_array_almost_equal(converter.magnetometer(EXAMPLE_RAW_DATA),
                                  TCM_NO_TEMP_EXPECTATION)

    def test_calibrated_temp_comp_magnetometer(self):
        converter = Converter(calibration_from_file("v3_temp_comp.txt"))
        assert isinstance(converter.magnetometer_converter,
                          TempCompensatedMagnetometer)
        assert_array_almost_equal(converter.magnetometer(EXAMPLE_RAW_DATA,
                                                         EXAMPLE_TEMP_ARRAY),
                                  TCM_EXPECTATION)

    def test_dissolved_oxygen(self):
        data = array([6400, 9847, 39321])
        expected = array([19.00, 26.77, 99.99])
        converter = BinaryCodedDecimal()
        assert_array_almost_equal(converter.convert(data), expected)
