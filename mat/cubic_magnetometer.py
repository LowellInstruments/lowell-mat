from numpy import dot
from mat.meter import Meter
from mat.utils import array_from_tags


X_KEYS = ['MXX', 'MXY', 'MXZ']
Y_KEYS = ['MYX', 'MYY', 'MYZ']
Z_KEYS = ['MZX', 'MZY', 'MZZ']
OFFSET_KEYS = ['MXV', 'MYV', 'MZV']


class CubicMagnetometer(Meter):
    REQUIRED_KEYS = set(OFFSET_KEYS).union(X_KEYS,
                                           Y_KEYS,
                                           Z_KEYS,
                                           OFFSET_KEYS)

    def __init__(self, hs):
        self.hard_iron = array_from_tags(hs, OFFSET_KEYS).transpose()
        self.soft_iron = array_from_tags(hs,
                                         X_KEYS,
                                         Y_KEYS,
                                         Z_KEYS).transpose()

    def convert(self, raw_magnetometer, temperature=None):
        return dot(self.soft_iron, raw_magnetometer + self.hard_iron)
