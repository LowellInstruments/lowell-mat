from numpy import (
    array,
    tile,
)
from mat.cubic_magnetometer import CubicMagnetometer


TEMPERATURE_KEYS = ['TMX', 'TMY', 'TMZ', 'MRF']


class TempCompensatedMagnetometer(CubicMagnetometer):
    REQUIRED_KEYS = CubicMagnetometer.REQUIRED_KEYS.union(TEMPERATURE_KEYS)

    def __init__(self, hs):
        super().__init__(hs)
        self.temperature_slope = array([[hs['TMX'],
                                         hs['TMY'],
                                         hs['TMZ']]]).T
        self.temp_reference = array([hs['MRF']])

    def convert(self, raw_magnetometer, temperature=None):
        """
        NOTE: temperature must be a numpy array, even if it is a single value
        """
        magnetometer = super().convert(raw_magnetometer)
        if temperature is None:
            return magnetometer
        temp_range = [-20, 50]
        temperature[temperature < temp_range[0]] = temp_range[0]
        temperature[temperature > temp_range[1]] = temp_range[1]
        assert temperature.shape == (raw_magnetometer.shape[1],)
        temperature_delta = tile(temperature, (3, 1)) - self.temp_reference
        magnetometer = (magnetometer +
                        temperature_delta * self.temperature_slope)
        return magnetometer
