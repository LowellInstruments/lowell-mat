from unittest import TestCase
from tests.utils import reference_file
from math import isclose


def compare_files(path1, path2):
    with open(path1, 'r') as fid1, open(path2, 'r') as fid2:
        if _n_lines(fid1) != _n_lines(fid2):
            raise ValueError('Files have different number of lines')
        if _n_columns(fid1) != _n_columns(fid2):
            raise ValueError('Headers have different number of columns')
        _values_are_close(zip(fid1, fid2))


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
            if not isclose(float(file1[i]), float(file2[i]), abs_tol=0.01):
                raise ValueError('Error on row {}'.format(row_count))
        row_count += 1
    return True


class CompareDataFiles(TestCase):
    def test_compare_avg_lid_files(self):
        file1 = reference_file('compare_data_files/test_accelmag1.csv')
        file2 = reference_file('compare_data_files/test_accelmag2.csv')
        compare_files(file1, file2)

    def test_compare_mlc_to_converter(self):
        file1 = reference_file('compare_data_files/test_accelmag.csv')
        file2 = reference_file('compare_data_files/test_MA.txt')
        compare_files(file1, file2)
