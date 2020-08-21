from numpy import array, mod
from datetime import datetime
import numpy as np


def obj_from_coefficients(coefficients, classes):
    coefficient_set = set(coefficients)
    for klass in classes:
        keys = klass.REQUIRED_KEYS
        if keys <= coefficient_set:
            return klass(coefficients)
    return None


def trim_start(string, n_chars_to_trim):
    return string[n_chars_to_trim:]


def array_from_tags(data, *key_lists):
    return array([[data[key] for key in key_list]
                  for key_list in key_lists])


def cut_out(string, start_cut, end_cut):
    return string[:start_cut] + string[end_cut:]


def epoch(time):
    return (time - datetime(1970, 1, 1)).total_seconds()


def epoch_from_timestamp(date_string):
    """ Return posix timestamp """
    epoch_time = datetime(1970, 1, 1)
    date_time = datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
    return (date_time - epoch_time).total_seconds()


def parse_tags(string):
    """
    Break a string of tag/value pairs separated by \r\n into a dictionary
    with tags as keys
    eg
    parse_tags('ABC 123\r\nDEF 456\r\n')
    would return
    {'ABC': '123', 'DEF': '456'}
    """
    lines = string.split('\r\n')[:-1]
    dictionary = {}
    for tag_and_value in lines:
        tag, value = tag_and_value.strip().split(' ', 1)
        dictionary[tag] = value
    return dictionary


def four_byte_int(bytes, signed=False):
    try:
        if len(bytes) != 4:
            return 0
        result = int(bytes[2:4] + bytes[0:2], 16)
        if signed and result > 32768:
            return result - 65536
        return result
    except ValueError:
        raise RuntimeError("Unable to extract integer from %s" % bytes)


def roll_pitch_yaw(accel, mag):
    """
    Convert accel and mag components into yaw/pitch/roll. Output is in radians
    """
    roll = np.arctan2(accel[1], accel[2])
    pitch = np.arctan2(-accel[0],
                       accel[1] * np.sin(roll) + accel[2] * np.cos(roll))
    by = mag[2] * np.sin(roll) - mag[1] * np.cos(roll)
    bx = (mag[0] * np.cos(pitch) + mag[1] * np.sin(pitch) * np.sin(roll)
          + mag[2] * np.sin(pitch) * np.cos(roll))
    yaw = np.arctan2(by, bx)
    return roll, pitch, yaw


def apply_declination(heading, declination):
    return mod(heading + 180 + declination, 360) - 180
