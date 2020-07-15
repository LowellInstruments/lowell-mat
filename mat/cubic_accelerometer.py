from numpy import dot
from mat.meter import Meter
from mat.utils import array_from_tags


X_KEYS = ['AXX', 'AXY', 'AXZ']
Y_KEYS = ['AYX', 'AYY', 'AYZ']
Z_KEYS = ['AZX', 'AZY', 'AZZ']
OFFSET_KEYS = ['AXV', 'AYV', 'AZV']
CUBIC_KEYS = ['AXC', 'AYC', 'AZC']


class CubicAccelerometer(Meter):
    REQUIRED_KEYS = set(CUBIC_KEYS).union(X_KEYS,
                                          Y_KEYS,
                                          Z_KEYS,
                                          OFFSET_KEYS)

    def __init__(self, hs):
        self.gain = array_from_tags(hs, X_KEYS, Y_KEYS, Z_KEYS)
        self.offset = array_from_tags(hs, OFFSET_KEYS).transpose()
        self.cubic = array_from_tags(hs, CUBIC_KEYS).transpose()

    def convert(self, raw_meter, temperature=None):
        raw_accelerometer = raw_meter / 1024.
        return (dot(self.gain, raw_accelerometer) +
                self.offset +
                self.cubic * raw_accelerometer ** 3)
