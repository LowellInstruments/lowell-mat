import numpy as np
from mat.meter import Meter


class BinaryCodedDecimal(Meter):
    """
    Convert a two byte BCD of format xx.xx
    The integer is the first byte, the decimal is the second byte
    e.g. 0x2677 converts to 26.77
    """
    def __init__(self, hs=None):
        self._convert_fcn = np.vectorize(self._dec_to_bcd)

    def convert(self, raw_meter, temperature=None):
        return self._convert_fcn(raw_meter)

    def _dec_to_bcd(self, value):
        output = 0
        for i in range(4):
            shift = 12 - 4*i
            multiplier = 10 / (10**i)
            output += (value >> shift & 15) * multiplier
        return output
