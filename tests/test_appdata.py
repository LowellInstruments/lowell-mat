from os import environ
from filecmp import cmp
from shutil import rmtree
from contextlib import contextmanager
from unittest.mock import patch
from unittest import TestCase
from tests.utils import reference_file
from mat.appdata import (
    POSIX_SUBDIR,
    get_userdata,
    set_userdata,
    userdata_path,
)


class TestSensorDataFile(TestCase):
    def test_userdata_path_unknown(self):
        with _name_patch(name="unknown"):
            with self.assertRaises(SystemError):
                userdata_path()

    def test_userdata_path_posix(self):
        with _name_patch(name="posix"):
            environ["HOME"] = reference_file("appdata_dir/")
            assert POSIX_SUBDIR in userdata_path()

    def test_set_userdata(self):
        with _name_patch():
            appdata_path = reference_file("appdata_dir/")
            environ["APPDATA"] = appdata_path
            filename = "appdata.test"
            set_userdata(filename, "field", "data")
            assert cmp(userdata_path(filename),
                       reference_file("appdata.test.expect"))
            assert "field" in get_userdata(filename)
            rmtree(appdata_path)


@contextmanager
def _name_patch(name="nt"):
    with patch("mat.appdata.os.name", name):
        yield
