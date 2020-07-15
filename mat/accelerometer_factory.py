from mat.cubic_accelerometer import CubicAccelerometer
from mat.linear_accelerometer import LinearAccelerometer
from mat.utils import obj_from_coefficients


def accelerometer_factory(calibration):
    return obj_from_coefficients(calibration.coefficients,
                                 [CubicAccelerometer, LinearAccelerometer])
