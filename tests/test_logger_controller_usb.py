from contextlib import contextmanager
from calendar import timegm
from time import strptime
from numpy import array
from numpy.testing import assert_array_almost_equal
from unittest.mock import patch
from unittest import TestCase
from serial import SerialException
from mat.converter import Converter
from mat.logger_controller import (
    RESET_CMD,
    SIMPLE_CMDS,
)
from mat.logger_controller_usb import (
    LoggerControllerUSB
)
from mat.v2_calibration import V2Calibration

COM_PORT = "1234"
COM_NAME = "COM" + COM_PORT
COM_VALUE = [[COM_NAME]]
SERIAL_NUMBER = "123456789"
TTY_NAME = "ttyACM0"
TTY_VALUE = [[TTY_NAME]]
TIME_FORMAT = "%Y/%m/%d %H:%M:%S"
TIME_STAMP = "2018/09/18 14:36:00"
EXPECTED_SENSOR_READINGS_32_BYTES = {
    'ax': array([-4.26757812]),
    'ax_raw': array([-4370]),
    'ay': array([-4.26757812]),
    'ay_raw': array([-4370]),
    'az': array([-4.26757812]),
    'az_raw': array([-4370]),
    'batt': array([-4.37]),
    'light': 0,
    'light_raw': 0,
    'mx': array([-4370.]),
    'mx_raw': array([-4370]),
    'my': array([-4370.]),
    'my_raw': array([-4370]),
    'mz': array([-4370.]),
    'mz_raw': array([-4370]),
    'pressure': 0,
    'pressure_raw': 0,
    'temp': -26.170648093957993,
    'temp_raw': 61166,
}
EXPECTED_SENSOR_READINGS_40_BYTES = {
    'ax': array([-4.26757812]),
    'ax_raw': -4370,
    'ay': array([-4.26757812]),
    'ay_raw': -4370,
    'az': array([-4.26757812]),
    'az_raw': -4370,
    'batt': -4.37,
    'light': array([206.68945312]),
    'light_raw': -4370,
    'mx': array([-4370.]),
    'mx_raw': -4370,
    'my': array([-4370.]),
    'my_raw': -4370,
    'mz': array([-4370.]),
    'mz_raw': -4370,
    'pressure': array([100.8656]),
    'pressure_raw': 61166,
    'temp': array([-26.17064809]),
    'temp_raw': 61166,
}
EXPECTED_SENSOR_READINGS_40_ZERO_BYTES = {
    'ax': array([0.]),
    'ax_raw': array([0]),
    'ay': array([0.]),
    'ay_raw': array([0]),
    'az': array([0.]),
    'az_raw': array([0]),
    'batt': array([0.]),
    'light': array([100.]),
    'light_raw': 0,
    'mx': array([0.]),
    'mx_raw': array([0]),
    'my': array([0.]),
    'my_raw': array([0]),
    'mz': array([0.]),
    'mz_raw': array([0]),
    'pressure': 3.0,
    'pressure_raw': 0,
    'temp': 1194.0891079879839,
    'temp_raw': 1,
}


class FakeExceptionSerial:
    def __init__(self, path, baud=9600):
        raise SerialException


class FakeSerial:
    close_count = 0

    def __init__(self, path, baud=9600):
        self.path = path
        self.baud = baud

    def close(self):
        FakeSerial.close_count += 1
        pass

    def reset_input_buffer(self):
        pass

    def write(self, *args):
        pass


class FakeSerialReader(FakeSerial):
    data = b'ERR'

    def __init__(self, path, baud=9600):
        super().__init__(path, baud)
        self.start = 0

    def read(self, count):
        end = self.start + count
        result = self.data[self.start:end]
        self.start = end
        return result


class FakeSerialExceptionReader(FakeSerialReader):
    def read(self, count):
        raise SerialException


class FakeSerialErr(FakeSerialReader):
    data = b'\n\rERR 04boom'


class FakeSerialEmpty(FakeSerialReader):
    data = b''


class FakeSerialForCommand(FakeSerialReader):
    cmds = ["ERR"]

    def __init__(self, path, baud=9600):
        super().__init__(path, baud)
        self.data = ''.join(self.cmds).encode()


class TestLoggerControllerUSB(TestCase):
    def test_create(self):
        assert LoggerControllerUSB()

    def test_open_port_on_posix(self):
        with _grep_patch(TTY_VALUE, name="posix"):
            _open_controller()

    def test_open_port_on_nt(self):
        with _grep_patch(COM_VALUE, name="nt"):
            _open_controller()

    def test_open_port_with_empty_grep(self):
        with _grep_patch(None, name="posix"):
            with self.assertRaises(RuntimeError):
                _open_controller()

    def test_open_port_on_unknown(self):
        with _grep_patch(COM_VALUE, name="unknown"):
            with self.assertRaises(RuntimeError):
                _open_controller()

    def test_open_port_twice(self):
        with _serial_patch(FakeSerial):
            controller = _open_controller(com_port="1")
            close_count = FakeSerial.close_count
            assert controller.open_port(com_port="1")
            assert FakeSerial.close_count > close_count

    def test_open_port_exception(self):
        with _serial_patch(FakeExceptionSerial):
            _open_controller(com_port="1", expectation=False)

    def test_empty_command(self):
        with _serial_patch(FakeSerial):
            controller = _open_controller(com_port="1")
            with self.assertRaises(IndexError):
                controller.command()

    def test_simple_command_port_closed(self):
        controller = LoggerControllerUSB()
        assert controller.command("SIT") is None

    def test_command_with_data_port_closed(self):
        controller = LoggerControllerUSB()
        assert controller.command("WAIT", "1") is None

    def test_sleep_command(self):
        with _serial_patch(FakeSerial):
            assert _command("sleep") is None

    def test_sit_command(self):
        with _command_patch("SIT 04down"):
            assert _command("SIT") == "down"

    def test_short_command2(self):
        with _command_patch("SIT 04dow"):
            controller = _open_controller(com_port="1")
            with self.assertRaises(RuntimeError):
                controller.command("SIT")

    def test_sit_command_with_callbacks(self):
        with _command_patch("SIT 04down"):
            assert self.command_with_callbacks() == "down"

    def test_sit_command_with_bad_length(self):
        with _command_patch("SIT down"):
            controller = _open_controller(com_port="1")
            with self.assertRaises(RuntimeError):
                controller.command("SIT")

    def test_err_command_with_callbacks(self):
        with _serial_patch(FakeSerialErr):
            assert self.command_with_callbacks() is None

    def command_with_callbacks(self):
        controller = LoggerControllerUSB()
        controller.set_callback("tx", _do_nothing)
        controller.set_callback("rx", _do_nothing)
        assert controller.open_port(com_port="1")
        return controller.command("SIT")

    def test_exception_command(self):
        with _serial_patch(FakeSerialExceptionReader):
            assert _open_controller(com_port="1").command("SIT") is None

    def exception_command(self):
        assert _open_controller(com_port="1").command("SIT") is None

    def test_load_calibration(self):
        with _command_patch("RHS 04down" * 10):
            self.load_calibration()

    def test_load_calibration_empty(self):  # For coverage
        with _command_patch("RHS 00" * 10):
            _open_controller(com_port="1")
            self.load_calibration()

    def load_calibration(self):
        controller = _open_controller(com_port="1")
        assert controller.calibration is None
        assert controller.load_calibration() is None
        assert isinstance(controller.calibration, V2Calibration)
        assert isinstance(controller.converter, Converter)
        return controller

    def test_load_logger_info_bad(self):
        with _command_patch("RLI 03bad" * 3):
            controller = _open_controller(com_port="1")
            assert len(controller.logger_info) == 0
            assert controller.load_logger_info() is None
            assert controller.logger_info['error'] is True

    def test_load_logger_ca_info(self):
        with _command_patch("RLI 09CA\x04FFFF##" * 3):
            controller = _open_controller(com_port="1")
            assert len(controller.logger_info) == 0
            assert controller.load_logger_info() is None
            assert controller.logger_info["CA"] != 0

    def test_load_logger_ba_info(self):
        with _command_patch("RLI 09BA\x04FFFF##" * 3):
            controller = _open_controller(com_port="1")
            assert len(controller.logger_info) == 0
            assert controller.load_logger_info() is None
            assert controller.logger_info["BA"] != 0

    def test_load_logger_ba_info_short(self):
        with _command_patch("RLI 07BA\x02FF##" * 3):
            controller = _open_controller(com_port="1")
            assert len(controller.logger_info) == 0
            assert controller.load_logger_info() is None
            assert controller.logger_info["BA"] == 0

    def test_get_timestamp(self):
        with _command_patch("GTM 13" + TIME_STAMP):
            expectation = timegm(strptime(TIME_STAMP, TIME_FORMAT))
            assert (_open_controller(com_port="1").get_timestamp() ==
                    expectation)

    def test_get_empty_logger_settings(self):
        with _command_patch("GLS 00"):
            assert _open_controller(com_port="1").get_logger_settings() == {}

    def test_get_logger_settings_on(self):
        with _command_patch("GLS 1e" + "01" * 15):
            settings = _open_controller(com_port="1").get_logger_settings()
            assert settings['ACL'] is True
            assert settings['BMN'] == 257

    def test_get_logger_settings_off(self):
        with _command_patch("GLS 1e" + "00" * 15):
            settings = _open_controller(com_port="1").get_logger_settings()
            assert settings['ACL'] is False
            assert settings['BMN'] == 0

    def test_reset(self):
        with _command_patch(RESET_CMD):
            assert _open_controller(com_port="1").command(RESET_CMD) is None

    def test_commands_that_return_empty_string(self):
        for cmd in SIMPLE_CMDS:
            with _command_patch(cmd + " 00"):
                assert _open_controller(com_port="1").command(cmd) == ""

    def test_cmd_with_no_data(self):
        with _serial_patch(FakeSerialEmpty):
            with self.assertRaises(RuntimeError):
                _open_controller(com_port="1").command(SIMPLE_CMDS[0])

    def test_stop_with_string(self):
        with _command_patch("SWS 00"):
            assert _open_controller(com_port="1").stop_with_string("") == ""

    def test_get_sensor_readings_closed_port(self):
        with _command_patch("GSR 00" + "RHS 00" * 10):
            controller = _open_controller(com_port="1")
            controller.close()
            with self.assertRaises(RuntimeError):
                controller.get_sensor_readings()

    def test_get_sensor_readings_empty(self):
        with _command_patch("GSR 00" + "RHS 00" * 10):
            assert _open_controller(com_port="1").get_sensor_readings() is None

    def test_get_sensor_readings_32_bytes(self):
        # Note: "F" causes a ZeroDivisionError
        readings = self.get_sensor_readings(32, "E")
        [assert_array_almost_equal(EXPECTED_SENSOR_READINGS_32_BYTES[key],
                                   readings[key])
         for key in EXPECTED_SENSOR_READINGS_32_BYTES.keys()]

    def test_get_sensor_readings_40_bytes(self):
        readings = self.get_sensor_readings(40, "E")
        [assert_array_almost_equal(EXPECTED_SENSOR_READINGS_40_BYTES[key],
                                   readings[key])
         for key in EXPECTED_SENSOR_READINGS_40_BYTES.keys()]

    def test_get_sensor_readings_40_zero_bytes(self):
        readings = self.get_sensor_readings(40, "0")
        [assert_array_almost_equal(EXPECTED_SENSOR_READINGS_40_ZERO_BYTES[key],
                                   readings[key])
         for key in EXPECTED_SENSOR_READINGS_40_ZERO_BYTES.keys()]

    def get_sensor_readings(self, bytes, value):
        controller = None
        with _command_patch(["RHS 00",
                             "GSR %02s%s" % (hex(bytes)[2:], value * bytes)]):
            controller = self.load_calibration()
            return controller.get_sensor_readings()

    def test_get_sd_capacity_empty(self):
        with _command_patch("CTS 00"):
            assert _open_controller(com_port="1").get_sd_capacity() is None

    def test_get_sd_capacity(self):
        capacity = 128
        with _command_patch("CTS 05%dKB" % capacity):
            assert _open_controller(com_port="1").get_sd_capacity() == capacity

    def test_get_sd_capacity_bad_data(self):
        with _command_patch("CTS 02XY"):
            assert _open_controller(com_port="1").get_sd_capacity() is None

    def test_get_sd_free_space_empty(self):
        with _command_patch("CFS 00"):
            assert _open_controller(com_port="1").get_sd_free_space() is None

    def test_get_sd_free_space(self):
        free_space = 128
        with _command_patch("CFS 05%dKB" % free_space):
            assert (_open_controller(com_port="1").get_sd_free_space() ==
                    free_space)

    def test_get_sd_free_space_bad_data(self):
        with _command_patch("CFS 02XY"):
            assert _open_controller(com_port="1").get_sd_free_space() is None

    def test_get_sd_file_size(self):
        size = 128
        with _command_patch("FSZ 03%d" % size):
            assert _open_controller(com_port="1").get_sd_file_size() == size

    def test_get_sd_file_size_empty(self):
        with _command_patch("FSZ 00"):
            assert _open_controller(com_port="1").get_sd_file_size() is None

    def test_sync_time(self):
        with _command_patch("STM 00"):
            assert _open_controller(com_port="1").sync_time() == ""


# def _check_ports(port):
#     controller = LoggerControllerUSB()
#     assert controller.check_ports() == [port]


@contextmanager
def _grep_patch(grep_return, name="nt"):
    with patch("mat.logger_controller_usb.Serial", FakeSerial):
        with patch("mat.logger_controller_usb.grep", return_value=grep_return):
            with patch("mat.logger_controller_usb.os.name", name):
                yield


@contextmanager
def _serial_patch(serial_class, name="nt"):
    with patch("mat.logger_controller_usb.Serial", serial_class):
        with patch("mat.logger_controller_usb.os.name", name):
            yield


@contextmanager
def _command_patch(cmds, name="nt"):
    if not isinstance(cmds, list):
        cmds = [cmds]
    with _serial_patch(fake_for_command(cmds), name):
        yield


def fake_for_command(cmds):
    # create a new type object
    return type("FakeSerial", (FakeSerialForCommand,), {"cmds": cmds})


def _open_controller(com_port=None, expectation=True):
    controller = LoggerControllerUSB()
    assert bool(controller.open_port(com_port=com_port)) is expectation
    return controller


def _command(cmd):
    controller = _open_controller(com_port="1")
    return controller.command(cmd)


def _do_nothing(*args):
    pass
