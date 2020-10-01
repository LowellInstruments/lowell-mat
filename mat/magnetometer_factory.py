from mat.cubic_magnetometer import CubicMagnetometer
from mat.temp_compensated_magnetometer import TempCompensatedMagnetometer
from mat.linear_magnetometer import LinearMagnetometer
from mat.utils import obj_from_coefficients


def magnetometer_factory(calibration):
    return obj_from_coefficients(calibration.coefficients,
                                 [TempCompensatedMagnetometer,
                                  CubicMagnetometer,
                                  LinearMagnetometer])
