from unittest import TestCase
from mat import tiltcurve
from tests.utils import reference_file


class TestHeader(TestCase):
    def test_load_tiltcurve(self):
        file = 'tiltcurve/TCM-1, No Ballast Washer, Salt Water.cal'
        curve = tiltcurve.TiltCurve(reference_file(file))
        curve.parse()
        assert curve.ballast == 0
        assert curve.salinity == 'Salt'
        assert curve.model == 'TCM-1'
        assert curve.speed_from_tilt(0) == 0
        assert curve.speed_from_tilt(90) == 120

    def test_missing_space(self):
        with self.assertRaises(ValueError):
            file = 'tiltcurve/missing_space.cal'
            curve = tiltcurve.TiltCurve(reference_file(file))
            curve.parse()

    def test_extra_line(self):
        with self.assertRaises(ValueError):
            file = 'tiltcurve/extra_line.cal'
            curve = tiltcurve.TiltCurve(reference_file(file))
            curve.parse()

    def test_header_out_of_order(self):
        with self.assertRaises(ValueError):
            file = 'tiltcurve/out_of_order.cal'
            curve = tiltcurve.TiltCurve(reference_file(file))
            curve.parse()
