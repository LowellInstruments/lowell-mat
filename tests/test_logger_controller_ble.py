from contextlib import contextmanager
from unittest.mock import patch, Mock
from unittest import TestCase
from mat.logger_controller_ble import (
    LoggerControllerBLE,
    Delegate,
    LCBLEException,
    XModemException
)


class FakeOutStream:
    def seek(self, a, b):
        pass

    def tell(self):
        return 12345

    def truncate(self, size):
        pass


class FakeOutStreamTellIsWrong(FakeOutStream):
    def tell(self):
        return 0


class FakeData:
    def __init__(self, index):
        self.valHandle = index

    def write(self, data, withResponse=False):
        pass


class FakeDataException:
    def __init__(self, index):
        self.valHandle = index

    def write(self, data, withResponse=False):
        raise LCBLEException


class FakeDataIndexable:
    def __init__(self):
        pass

    def __getitem__(self, index):
        return FakeData(index)

class FakeDataIndexableException:
    def __init__(self):
        pass

    def __getitem__(self, index):
        return FakeDataException(index)

class FakeService:
    def __init__(self):
        pass

    def getCharacteristics(self, charact):
        pass
        return FakeDataIndexable()

class FakeServiceException:
    def __init__(self):
        pass

    def getCharacteristics(self, charact):
        pass
        return FakeDataIndexableException()


class FakeDelegateAscii:

    def __init__(self):
        self.xmodem_mode = False

    def handleNotification(self, handle, data):
        pass


class FakePeripheral():
    def __init__(self, mac_string):
        pass

    def setDelegate(self, delegate_to_fxn):
        pass

    def getServiceByUUID(self, uuid):
        pass
        return FakeService()

    def writeCharacteristic(self, where, value):
        pass

    def waitForNotifications(self, value):
        return True

    def disconnect(self):
        pass

class FakePeripheralException():
    def __init__(self, mac_string):
        pass

    def setDelegate(self, delegate_to_fxn):
        pass

    def getServiceByUUID(self, uuid):
        pass
        return FakeServiceException()

    def writeCharacteristic(self, where, value):
        pass

    def waitForNotifications(self, value):
        return True

    def disconnect(self):
        pass


class FakePeripheralCmdTimeout(FakePeripheral):
    def waitForNotifications(self, value):
        return False


class TestLoggerControllerBLE(TestCase):

    # test constructor, patch with stub class, FakePeripheral() gets called
    @patch('bluepy.btle.Peripheral', FakePeripheral)
    def test_lc_ble_constructor(self):
        assert LoggerControllerBLE('ff:ff:ff:ff:ff:ff') is not None

    # test mock usage, patch with mock class, MagicMock() gets called
    @patch('bluepy.btle.Peripheral')
    def test_mock_usage_success(self, my_mock):
        LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
        LoggerControllerBLE('aa:bb:cc:dd:ee:ff')
        assert my_mock.call_count == 2

    # test for receiving answers and results to commands()
    def test_handleNotification_ascii(self):
        d = Delegate()
        d.xmodem_mode = False
        d.handleNotification(None, b'\n\rany_ascii_string\r\n')
        assert len(d.read_buffer) == 1

    # test for receiving initial 'GET' answer while in xmodem format
    def test_handleNotification_xmodem_not_sentC(self):
        d = Delegate()
        d.xmodem_mode = True
        d.sentC = False
        d.handleNotification(None, b'\n\rGET 00\r\n')
        assert len(d.buffer) == 10

    # test for receiving file while in xmodem format
    def test_handleNotification_xmodem_yes_sentC(self):
        d = Delegate()
        d.xmodem_mode = True
        d.sentC = True
        d.handleNotification(None, b'\x02\x01\xfe\x00\xff')
        assert len(d.xmodem_buffer) == 5

    # test for parsing while in ascii mode
    def test_read_line_no_read_buffer(self):
        self.assertRaises(IndexError, Delegate().read_line)

    # test for parsing while in ascii mode
    def test_read_line_read_buffer(self):
        d = Delegate()
        d.handleNotification(None, b'\n\rany_ascii_string\r\n')
        assert ''.join(d.read_line()) == 'any_ascii_string'

    # test for open method
    def test_open_close(self):
        with _peripheral_patch():
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            lc_ble.open()
            assert lc_ble.close() == 'ok'

    # test for a command which requires no answer
    def test_command_no_answer_required(self):
        with _command_patch(None, ''):
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            assert lc_ble.command('sleep', None) is None

    # test for a command which requires answer but timeouts
    def test_command_timeout(self):
        with _command_patch_timeout():
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            self.assertRaises(LCBLEException, lc_ble.command, 'STS', None)

    # test for a command which performs perfectly
    def test_command_answer_ok(self):
        with _command_patch(True, 'STS'):
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            assert lc_ble.command('STS') is 'STS'

    # test for exception when logger answering 'INV' to a command
    def test_command_answer_inv(self):
        with _command_patch(True, 'INV'):
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            self.assertRaises(LCBLEException, lc_ble.command, 'STS')

    # test for exception when logger answering 'ERR' to a command
    def test_command_answer_err(self):
        with _command_patch(True, 'ERR'):
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            self.assertRaises(LCBLEException, lc_ble.command, 'STS')

    # test for a control_command to RN4020 which performs perfectly
    def test_control_command_answer_ok(self):
        with _command_patch(True, 'CMDAOKMLDP'):
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            assert lc_ble.control_command('data_X', '1.8.68') is 'CMDAOKMLDP'

    # test for a control_command to RN4020 missing some parameter
    def test_control_command_answer_no_fw_parameter(self):
        with _command_patch(True, 'CMDAOKMLDP'):
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            self.assertRaises(LCBLEException, lc_ble.control_command,
                              'data_x', '')

    # test for a control_command to RN4020 with old firmware
    def test_control_command_answer_old_fw(self):
        with _command_patch_timeout():
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            lc_ble.fw_version = '1.7.27'
            assert lc_ble.control_command('data_X', '1') is 'assume_CMDAOKMLDP'

    # test for a control_command to RN4020 with new fw which does not goes well
    def test_control_command_answer_new_fw_but_error(self):
        with _command_patch_timeout():
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            lc_ble.fw_version = '1.7.28'
            self.assertRaises(LCBLEException, lc_ble.control_command,
                              'data_x', '1.7.28')

    # test for writing characteristics, used by command(), must do nothing
    def test_write(self):
        with _peripheral_patch():
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            lc_ble.write('hello')

    # test for the special command 'DIR' when logger answers wrongly
    def test_list_files_answer_wrong(self):
        with _command_patch(True, 'file_with_no_size.fil'):
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            self.assertRaises(LCBLEException, lc_ble.list_files)

    # test for command 'DIR' when logger answers timeouts
    def test_list_files_answer_timeout(self):
        with _command_patch_timeout():
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            self.assertRaises(LCBLEException, lc_ble.list_files)

    # test for command 'DIR' when logger answers perfectly but empty list
    def test_list_files_answer_empty(self):
        with _command_patch(True, '\x04'):
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            assert lc_ble.list_files() == []

    # test for command 'DIR' when logger answers a populated file list
    def test_list_files_answer_ok(self):
        rl_answers = Mock(side_effect=['one.h\t12', 'two.dat\t2345', '\x04'])
        with _command_patch_dir(True, rl_answers):
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            assert lc_ble.list_files() == [('one.h', 12), ('two.dat', 2345)]

    # test for command 'GET' when logger sends a file correctly
    def test_get_files_answer_ok(self):
        with _command_patch_get(True, 'GET 00'):
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            assert lc_ble.get_file('want_file', 12345, FakeOutStream()) is None

    # test for command 'GET' when logger timeouts while sending
    def test_get_files_answer_timeout(self):
        with _command_patch_get(False, None):
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            self.assertRaises(LCBLEException, lc_ble.get_file,
                              'want_file', 12345, FakeOutStream())

    # test for command 'GET' when logger sends a file too-small
    def test_get_files_answer_too_small(self):
        with _command_patch_get(True, 'GET 00'):
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            self.assertRaises(XModemException, lc_ble.get_file,
                              'want_file', 12345, FakeOutStreamTellIsWrong())

    # test for getc() function
    def test_getc(self):
        with _peripheral_patch():
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            lc_ble.delegate.xmodem_buffer = b'\x02\x01\xfe'
            assert lc_ble.getc(2) == b'\x02\x01'

    # test for getc() function, timeout, some bytes left
    def test_getc_timeout_bytes_left(self):
        with _peripheral_patch():
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            lc_ble.delegate.xmodem_buffer = b'\x02\x01\xfe'
            assert lc_ble.getc(2, timeout=0) == b'\x02\x01\xfe'

    # test for getc() function, timeout, no bytes left
    def test_getc_timeout_no_bytes_left(self):
        with _peripheral_patch():
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            assert lc_ble.getc(2, timeout=0) is None

    # test for putc() function, ascii mode, sent 'C'
    def test_putc_not_sentC(self):
        with _command_patch(None, None):
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            lc_ble.delegate.sentC = False
            assert lc_ble.putc('C') == 1

    # test for putc() function, xmodem mode, sent data
    def test_putc_yes_sentC(self):
        with _command_patch(None, None):
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            lc_ble.delegate.sentC = True
            assert lc_ble.putc(b'\x06') == 1

   # test for putc() function, xmodem mode, if raise Exception
   #  def test_putc_exception(self):
   #      with _write_char_exception_patch():
   #          lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
   #          self.assertRaises(LCBLEException, lc_ble.putc, 'data')

    # test for putc() function, xmodem mode, if managed Exception
    def test_putc_exception_managed(self):
        with _write_char_exception_patch():
            lc_ble = LoggerControllerBLE('ff:ff:ff:ff:ff:ff')
            assert lc_ble.putc(b'\x06') == 0


# vars useful for context managers
peripheral_class = 'bluepy.btle.Peripheral'
lc_ble_write_method = 'mat.logger_controller_ble.LoggerControllerBLE.write'
d_in_waiting_property = 'mat.logger_controller_ble.Delegate.in_waiting'
d_read_line_method = 'mat.logger_controller_ble.Delegate.read_line'
xmodem_recv_method = 'xmodem.XMODEM.recv'


@contextmanager
def _peripheral_patch():
    with patch(peripheral_class, FakePeripheral):
        yield


@contextmanager
def _command_patch(rv_in_waiting, rv_read_line):
    with patch(peripheral_class, FakePeripheral):
        with patch(lc_ble_write_method):
            with patch(d_in_waiting_property, return_value=rv_in_waiting):
                with patch(d_read_line_method, return_value=rv_read_line):
                    yield


# this one provides different answers on successive calls of read_line()
@contextmanager
def _command_patch_dir(rv_in_waiting, rl_method):
    with patch(peripheral_class, FakePeripheral):
        with patch(lc_ble_write_method):
            with patch(d_in_waiting_property, return_value=rv_in_waiting):
                with patch(d_read_line_method, rl_method):
                    yield


@contextmanager
def _command_patch_get(rv_in_waiting, rv_read_line):
    with _command_patch(rv_in_waiting, rv_read_line):
        with patch(xmodem_recv_method):
            yield


@contextmanager
def _command_patch_timeout():
    with patch(peripheral_class, FakePeripheralCmdTimeout):
        with patch(lc_ble_write_method):
            yield


@contextmanager
def _write_char_exception_patch():
    with patch(peripheral_class, FakePeripheralException):
            yield