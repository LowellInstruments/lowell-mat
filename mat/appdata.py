# GPLv3 License
# Copyright (c) 2018 Lowell Instruments, LLC, some rights reserved

import os
import pickle
from distutils.version import LooseVersion


NT_SUBDIR = 'Lowell Instruments\\'
POSIX_SUBDIR = '.Lowell'


def get_userdata(filename):
    path = userdata_path(filename)
    if os.path.isfile(path):
        with open(path, 'rb') as h:
            return pickle.load(h)
    else:
        return {}


def set_userdata(filename, field, data):
    path = userdata_path()
    if not os.path.exists(path):
        os.makedirs(path)
    userdata = get_userdata(filename)
    userdata[field] = data

    with open(os.path.join(path, filename), 'wb') as h:
        pickle.dump(userdata, h)


def delete_if_version_not_equal(filename, version):
    """
    Looks in appdata for a version field. If it is less than version, or
    if it doesn't exist, delete the appdata file
    """
    userdata = get_userdata(filename)
    userdata_version = userdata['version'] if 'version' in userdata else '0'
    if LooseVersion(userdata_version) != LooseVersion(version):
        if os.path.exists(userdata_path(filename)):
            os.remove(userdata_path(filename))


def userdata_path(filename=""):
    if os.name == 'nt':
        appdata_path = os.getenv('APPDATA')
        subdir = NT_SUBDIR
    elif os.name == 'posix':
        appdata_path = os.getenv('HOME')
        subdir = POSIX_SUBDIR
    else:
        raise SystemError('Unknown system type')
    return os.path.join(appdata_path, subdir, filename)
