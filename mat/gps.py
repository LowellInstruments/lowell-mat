import serial
import datetime
import time
from collections import namedtuple


def parse_int(x):
    return int(x) if x else None


def parse_float(x):
    return float(x) if x else None


class GPS:

    BAUD_RATE_BU_353_S4 = 4800
    RMC_Frame = namedtuple('RMC_Frame',
                           'valid timestamp latitude longitude knots course')
    TIMEOUT_PORT_READS = 3

    def __init__(self, port, baud_rate=BAUD_RATE_BU_353_S4):
        self.port = serial.Serial(port, baud_rate, timeout=1)
        self.handlers = {
            '$GPRMC': self._on_rmc,
        }
        self.last_rmc = None

    def get_gps_info(self, timeout=TIMEOUT_PORT_READS):
        if self._wait_for_frame_type('$GPRMC', timeout):
            # decide fields needed to consider RMC frame as valid
            if self.last_rmc and self.last_rmc.timestamp:
                return self.last_rmc
        return None

    # waits for frame_type + checksum OK -> populates self.last_*
    def _wait_for_frame_type(self, frame_type, timeout=TIMEOUT_PORT_READS):
        end_time = time.time() + timeout
        while time.time() < end_time:
            line_bytes = self.port.readline().strip()
            frame_type_received = self._parse_line(line_bytes, frame_type)
            if frame_type_received:
                return frame_type_received
            else:
                time.sleep(0.1)
        return None

    def _parse_line(self, line_bytes, frame_type):
        if line_bytes.startswith('$'.encode('ASCII')):
            line = line_bytes.decode('ASCII')
            data, checksum = line.split('*')
            tokens = data.split(',')
            gps_sentence, args = tokens[0], tokens[1:]
            handler = self.handlers.get(gps_sentence)
            if GPS._verify_string(data, checksum) is False \
                    or gps_sentence != frame_type \
                    or handler is None:
                return None
            handler(args)
            return line
        else:
            return None

    @staticmethod
    def _verify_string(data, checksum):
        # lose '$' character at the beginning of gps sentence
        data = data[1:]
        checksum_in_decimal = int(checksum, 16)
        int_values = [ord(x) for x in data]
        calculated = 0
        for x in int_values:
            calculated = calculated ^ x
        return True if calculated == checksum_in_decimal else False

    def _on_rmc(self, args):
        # print(args)
        if args[1] != 'A':
            return
        timestamp = datetime.datetime.strptime(args[8] + args[0],
                                               '%d%m%y%H%M%S.%f')
        latitude = GPS._to_decimal_degrees(args[2], args[3])
        longitude = GPS._to_decimal_degrees(args[4], args[5])
        knots = parse_float(args[6])
        course = parse_float(args[7])
        self.last_rmc = GPS.RMC_Frame(
            args[1], timestamp, latitude, longitude, knots, course)

    @staticmethod
    def _to_decimal_degrees(value, nsew):
        # BU-353-S4 lat, lon fields are DDMM.mmmm, may be empty if no coverage
        if not value:
            return None
        a, b = value.split('.')
        if len(a) < 4:
            raise ValueError
        degrees = int(a) // 100
        minutes = int(a) % 100
        minutes += float(int(b) / 10 ** len(b))
        result = degrees + minutes / 60.0
        if nsew in 'SW':
            result = -result
        return result
