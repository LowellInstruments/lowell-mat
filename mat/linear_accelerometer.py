from mat.meter import Meter
from mat.utils import array_from_tags


OFFSET_KEYS = ['AXA', 'AYA', 'AZA']
SLOPE_KEYS = ['AXB', 'AYB', 'AZB']


class LinearAccelerometer(Meter):

    REQUIRED_KEYS = set(OFFSET_KEYS).union(SLOPE_KEYS)

    def __init__(self, hs):
        self.slope = 1 / array_from_tags(hs, SLOPE_KEYS).transpose()
        self.offset = array_from_tags(hs, OFFSET_KEYS).transpose()

    def convert(self, raw_meter, temperature=None):
        return -raw_meter * self.slope - self.offset
