import os
from mat.calibration_factories import make_from_calibration_file
from math import isclose


def reference_file(file_name):
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "files",
        file_name)


def calibration_from_file(file_name):
    file = reference_file(file_name)
    return make_from_calibration_file(file)


def assert_compare_expected_file(file_name, expected_name=None):
    new_path = reference_file(file_name)
    expected_path = reference_file(expected_name or (file_name + ".expect"))
    with open(new_path) as new_file, open(expected_path) as expected_file:
        new_lines = [line.strip() for line in new_file.readlines()]
        expected_lines = [line.strip() for line in expected_file.readlines()]
    os.remove(new_path)
    assert new_lines == expected_lines


def compare_files(path1, path2):
    with open(path1, 'r') as fid1, open(path2, 'r') as fid2:
        assert _n_lines(fid1) == _n_lines(fid2)
        assert _n_columns(fid1) == _n_columns(fid2)
        _values_are_close(zip(fid1, fid2))
    os.remove(path1)


def _n_lines(fid):
    count = sum([1 for line in fid])
    fid.seek(0)
    return count


def _n_columns(fid):
    line = fid.readline()
    return len(line.split(','))


def _values_are_close(zip_obj):
    row_count = 0
    for rows in zip_obj:
        file1 = rows[0].strip().split(',')
        file2 = rows[1].strip().split(',')
        for i in range(1, len(file1)):
            assert isclose(float(file1[i]), float(file2[i]), abs_tol=0.01)
        row_count += 1
