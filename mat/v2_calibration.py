from mat.calibration import Calibration
from mat.utils import trim_start


class V2Calibration(Calibration):
    def __init__(self, coefficients):
        self.coefficients = {}
        for tag in coefficients:
            self.coefficients[tag] = float(coefficients[tag])

    @staticmethod
    def _parse_tag_value_pairs(calibration_string):
        """
        calibration_string has the following repeating format:
        3 character tag, 1 character length, n, in hex,
        n characters as a plain text float
        eg: The AXX, AXY and AXZ tags: AXX6-0.243AXY6-0.006AXZ6-0.002
        """
        yield 'RVN', '2'
        while True:
            tag = calibration_string[:3]
            if tag == 'HSE':
                break
            length = int(calibration_string[3], 16)
            value = calibration_string[4:4 + length]
            calibration_string = trim_start(calibration_string, 3+1+length)
            yield tag, value

    def make_serial_string(self):
        yield 'RVN12'
        for key in self.coefficients:
            if key == 'RVN':
                continue
            value = str(self.coefficients[key])
            length_hex = '%x' % len(value)
            yield key + length_hex + value

    def write_to_file(self, path):
        raise NotImplementedError('Feature not implemented for V2Calibration')
