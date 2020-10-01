# GPLv3 License
# Copyright (c) 2018 Lowell Instruments, LLC, some rights reserved

"""
A tilt curve is a carefully calibrated lookup table that associates
the angle of tilt with the speed of passing water.

To load a tilt curve, instantiate the TitlCurve class with the path to
the tilt curve file. Call the parse() method to parse the file.

To convert tilt angle to speed, call speed_from_tilt() with the tilt angle
(in degrees) from vertical.
"""

import numpy as np
from pathlib import Path


class TiltCurve:
    def __init__(self, path):
        self.path = Path(path)
        self.table = None
        self._deployment_configuration = {}
        self.parse()

    @property
    def ballast(self):
        return int(self._deployment_configuration['BAL'])

    @property
    def model(self):
        return self._deployment_configuration['MOD']

    @property
    def salinity(self):
        return self._deployment_configuration['SAL']

    def parse(self):
        with self.path.open('r') as fid:
            fid = self._skip_comments(fid)
            self._parse_deployment_config(fid)
            self._parse_tilt_table(fid)

    def _skip_comments(self, fid):
        while True:
            file_pos = fid.tell()
            line = fid.readline()
            if not line.startswith('//'):
                fid.seek(file_pos)
                return fid

    def _parse_deployment_config(self, fid):
        for expected_tag in ['MOD', 'BAL', 'SAL']:
            line = fid.readline().strip()
            tag, value = self._split_tag_value(line)
            if tag != expected_tag:
                raise ValueError(tag + ' tag not found in expected location')
            self._deployment_configuration[tag] = value

    def _parse_tilt_table(self, fid):
        if not fid.readline().startswith('CAL'):
            raise ValueError('CAL tag missing from start of data')
        self.table = np.loadtxt(fid, delimiter=',')

    def _split_tag_value(self, line):
        tag_value = line.split(' ')
        if len(tag_value) != 2:
            raise ValueError('Structure error in host storage file.')
        return tag_value[0], tag_value[1]

    def speed_from_tilt(self, tilt):
        return np.interp(tilt, self.table[:, 0], self.table[:, 1])

    def _model_ballast(self):
        return self.model, self.ballast

    def __lt__(self, other):
        return self._model_ballast() < other._model_ballast()

    def __gt__(self, other):
        return self._model_ballast() > other._model_ballast()

    def __eq__(self, other):
        return self._model_ballast() == other._model_ballast()
