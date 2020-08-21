from numpy import array


DEFAULT_PRA = 3
DEFAULT_PRB = 0.0016


class Pressure:
    def __init__(self, calibration):
        coefficients = calibration.coefficients
        pra = coefficients.get('PRA', DEFAULT_PRA)
        prb = coefficients.get('PRB', DEFAULT_PRB)
        self.pressure_slope = array([prb], dtype='float')
        self.pressure_offset = array([pra], dtype='float')

    def convert(self, raw_pressure):
        return ((self.pressure_slope * raw_pressure + self.pressure_offset)
                * 0.689475728)
