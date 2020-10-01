from mat.ascii85 import ascii85_to_num, num_to_ascii85
from mat.calibration import Calibration
from mat.utils import trim_start


class V3Calibration(Calibration):
    def __init__(self, coefficients):
        self.coefficients = {}
        for tag in coefficients:
            if tag == 'RVN':
                # RVN isn't encoded in ascii85 for backward compatibility
                self.coefficients['RVN'] = 3
                continue
            self.coefficients[tag] = ascii85_to_num(coefficients[tag])

    @staticmethod
    def _parse_tag_value_pairs(calibration_string):
        """
        calibration_string has the following repeating format:
        3 character tag, 5 character value encoded as ascii85
        eg: The AXX, AXY and AXZ tags: AXX^3r#pAXY3o"WbAXZ]$(%<
        """

        # Manually remove RVN13 from start of calibration_string because it
        # follows a different format for backward compatibility
        calibration_string = trim_start(calibration_string, 5)
        yield 'RVN', 3
        while True:
            tag = calibration_string[:3]
            if tag == 'HSE':
                break
            value = calibration_string[3:8]
            calibration_string = trim_start(calibration_string, 8)
            yield tag, value

    def make_serial_string(self):
        yield 'RVN13'
        for key, value in self._key_value():
            yield key + value

    def write_to_file(self, path):
        with open(path, 'w') as f:
            f.write('RVN 3\n')
            for key, value in self._key_value():
                value_str = ascii85_to_num(value)
                f.write('{} {}  // {}\n'.format(key, value, value_str))

    def _key_value(self):
        for key in self.coefficients:
            if key == 'RVN':
                continue
            value = num_to_ascii85(self.coefficients[key])
            yield key, value
