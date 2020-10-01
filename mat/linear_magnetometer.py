from mat.meter import Meter
from mat.utils import array_from_tags


SLOPE_KEYS = ['MXS', 'MYS', 'MZS']
OFFSET_KEYS = ['MXA', 'MYA', 'MZA']


class LinearMagnetometer(Meter):
    REQUIRED_KEYS = set(SLOPE_KEYS).union(OFFSET_KEYS)

    def __init__(self, hs):
        self.slope = array_from_tags(hs, SLOPE_KEYS).transpose()
        self.offset = array_from_tags(hs, OFFSET_KEYS).transpose()

    def convert(self, raw_magnetometer, temperature=None):
        return (raw_magnetometer + self.offset) * self.slope
