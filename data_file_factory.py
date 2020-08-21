from mat.lid_data_file import LidDataFile


DATA_FILE_TYPES = {'.lid': LidDataFile}


def load_data_file(file_path, calibration=None):
    extension = file_path[-4:]
    try:
        klass = DATA_FILE_TYPES.get(extension)
        return klass(file_path, calibration)
    except TypeError:
        raise WrongFileTypeError('Invalid Filename or extension')


class WrongFileTypeError(Exception):
    pass
