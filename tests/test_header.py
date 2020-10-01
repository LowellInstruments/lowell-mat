from unittest import TestCase
from mat import header
from tests.utils import reference_file


class TestHeader(TestCase):
    def test_header(self):
        expected_dict = {
            'ACL': True,
            'BAT': '0e5e',
            'BMN': 8,
            'BMR': 8,
            'CLK': '2018-05-25 08:27:07',
            'DFS': 32768,
            'DPL': 2,
            'ETM': '4096-01-01 00:00:00',
            'FWV': '1.8.32.5',
            'LED': True,
            'MGN': True,
            'ORI': 10,
            'PHD': False,
            'PRN': 4,
            'PRR': 4,
            'PRS': False,
            'PWC': '0001',
            'SER': '1805225',
            'STM': '1970-01-01 00:00:00',
            'STS': 1,
            'TMP': True,
            'TRI': 10,
        }
        h = header.header_factory(reference_file('test.lid'))
        h.parse_header()
        assert h._header == expected_dict

    def test_bad_header(self):
        with self.assertRaises(ValueError):
            h = header.header_factory(reference_file('bad_header.lid'))
            h.parse_header()

    def test_missing_hds(self):
        with self.assertRaises(ValueError):
            h = header.header_factory(reference_file('missing_hds_header.lid'))
            h.parse_header()

    def test_missing_hde(self):
        with self.assertRaises(ValueError):
            h = header.header_factory(reference_file('missing_hde.lid'))
            h.parse_header()
