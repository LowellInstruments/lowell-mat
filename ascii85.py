# GPLv3 License
# Copyright (c) 2018 Lowell Instruments, LLC, some rights reserved

import numpy as np
from math import floor


def num_to_ascii85(in_num):
    n = np.array(in_num, dtype='<f4')
    n.dtype = '<u4'
    chars = []
    for i in range(4, -1, -1):
        chars.append(floor((n / 85 ** i) + 33))
        n = n % 85 ** i
    return ''.join([chr(c) for c in chars])


def ascii85_to_num(in_str):
    assert len(in_str) == 5, 'in_str must be exactly five characters.'
    num = np.array([0], dtype='<u4')
    chars = [c for c in in_str]
    for i, c in enumerate(chars):
        num = num + (ord(c) - 33) * 85 ** (4-i)
    num.dtype = '<f4'
    return num.item()
