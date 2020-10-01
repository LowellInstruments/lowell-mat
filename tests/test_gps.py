import serial

from mat.gps import (
    parse_int,
    parse_float,
    GPS
)
from contextlib import contextmanager
from unittest.mock import patch
from unittest import TestCase


class FakeSerial:
    def __init__(self, fakeport, fakebaudrate, timeout=1):
        pass

    def readline(self):
        return b'$GPRMC,210239.000,A,4134.2946,N,\
        07038.2859,W,0.00,196.76,041218,,,A*77'


class FakeSerialNoAnswer(FakeSerial):
    def readline(self):
        return b''


class FakeSerialWrongChecksum(FakeSerial):
    def readline(self):
        return b'$GPRMC,210239.000,A,4134.2946,N,\
        07038.2859,W,0.00,196.76,041218,,,A*11'


class FakeSerialReadlineNotStartsWithDollar(FakeSerial):
    def readline(self):
        return b'GPRMC,210239.000,A,4134.2946,N,\
        07038.2859,W,0.00,196.76,041218,,,A*11'


@contextmanager
def _patch_serial(fake_serial_class):
    with patch('serial.Serial', fake_serial_class):
        yield


class TestGPS(TestCase):
    # link: https://www.directionsmag.com/site/latlong-converter/
    def test_convert_lat_n_to_decimal_degrees(self):
        lat_str = '3015.4550'
        assert GPS._to_deg(lat_str, 'N') == 30.257583333333333

    def test_convert_lat_s_to_decimal_degrees(self):
        lat_str = '3015.4550'
        assert GPS._to_deg(lat_str, 'S') == -30.257583333333333

    def test_convert_lon_e_to_decimal_degrees(self):
        lon_str = '07301.3281'
        assert GPS._to_deg(lon_str, 'E') == 73.022135

    def test_convert_lon_w_to_decimal_degrees(self):
        lon_str = '07301.3281'
        assert GPS._to_deg(lon_str, 'W') == -73.022135

    def test_convert_lon_too_short_to_decimal_degrees(self):
        lon_str = '807.2500'
        with self.assertRaises(ValueError):
            GPS._to_deg(lon_str, 'W')

    def test_convert_none_to_decimal_degrees(self):
        assert GPS._to_deg('', 'SW') is None

    def test_bad_on_rmc(self):
        with _patch_serial(FakeSerial):
            assert GPS('any', 57600)._on_rmc([None, 'V']) is None

    def test_parse_int(self):
        assert parse_int('3') == 3

    def test_parse_float(self):
        assert parse_float('3.5') == 3.5

    def test_gps_wait_for_rmc_frame_type(self):
        with _patch_serial(FakeSerial):
            assert GPS('any', 57600)._wait_frame('$GPRMC', 3) is not None

    def test_gps_wait_for_not_rmc_frame_type(self):
        with _patch_serial(FakeSerial):
            assert GPS('any', 57600)._wait_frame('$GPXXX', 0) is None

    def test_gps_wait_for_rmc_frame_type_no_handler(self):
        with _patch_serial(FakeSerial):
            o = GPS('any', 57600)
            o.handlers = {}
            assert o._wait_frame('$GPRMC', timeout=0.2) is None

    def test_gps_wait_for_rmc_frame_type_checksum_bad_and_timeouts(self):
        with _patch_serial(FakeSerialWrongChecksum):
            assert GPS('any', 57600)._wait_frame('$GPRMC',
                                                 timeout=0.2) is None

    def test_gps_wait_for_rmc_frame_type_but_not_starts_with_dollar(self):
        with _patch_serial(FakeSerialReadlineNotStartsWithDollar):
            assert GPS('any', 57600)._wait_frame('$GPRMC',
                                                 timeout=0.2) is None

    def test_get_last_rmc_frame_not_empty(self):
        with _patch_serial(FakeSerial):
            o = GPS('any', 57600)
            assert type(o.get_gps_info()) is GPS.RMC_Frame

    def test_get_last_rmc_frame_empty(self):
        with _patch_serial(FakeSerialNoAnswer):
            o = GPS('any', 57600)
            assert o.get_gps_info(timeout=0.2) is None

    def test_error_on_parse_line(self):
        with _patch_serial(FakeSerial):
            o = GPS('any', 57600)
            assert o._parse_line(None, '$GPRMC') is None

    def test_error_constructor(self):
        assert GPS('badport', 57600).port is None

    def test_error_on_gps_get_info(self):
        with _patch_serial(FakeSerial):
            o = GPS('any', 57600)
            o.port = None
            assert o.get_gps_info() is None
