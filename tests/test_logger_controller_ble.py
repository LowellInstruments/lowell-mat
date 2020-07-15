import pytest
import bluepy.btle
import sys
import time
import datetime
if sys.platform != 'win32':
    from mat.logger_controller_ble import (
        LoggerControllerBLE,
        Delegate,
        brand_ti,
        brand_microchip
    )
    from tests._test_logger_controller_ble import (
        FakePeripheral,
        FakePeripheralEx,
        FakeCharacteristic
    )


blue_per = 'bluepy.btle.Peripheral'
mac_ti = '80:6f:b0:ff:ff:ff'
mac_mc = '00:1e:c0:ff:ff:ff'
mac_un = 'ff:ff:ff:ff:ff:ff'
cmd = 'mat.logger_controller_ble.LoggerControllerBLE.command'
w_a = 'mat.logger_controller_ble.LoggerControllerBLE._wait_cmd_ans'
_ls = 'mat.logger_controller_ble.LoggerControllerBLE._ls'


@pytest.fixture
def fake_ble_factory(mocker):
    def patch_lc_ble(p=FakePeripheral, m='', rv=''):
        mocker.patch(blue_per, p)
        if m:
            mocker.patch(m, return_value=rv)
        return LoggerControllerBLE

    # returns a LC_BLE class w/ 1 attribute + 1 method patched
    return patch_lc_ble


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
class TestLoggerControllerBLECC26X2:
    def test_buffer_receive_notifications(self):
        d = Delegate()
        d.handleNotification(None, b'\n\rany_data\r\n')
        assert d.buf == b'\n\rany_data\r\n'
        d.file_mode = True
        d.handleNotification(None, b'\n\rany_data\r\n')
        assert d.x_buf == b'\n\rany_data\r\n'

    def test_buffer_clear(self):
        d = Delegate()
        d.buf = b'\n\rany_data\r\n'
        d.x_buf = b'\n\rany_data\r\n'
        d.clr_buf()
        d.clr_x_buf()
        assert d.buf == b''
        assert d.x_buf == b''

    # test switch between command and file mode
    def test_switch_file_mode(self):
        d = Delegate()
        assert not d.file_mode
        d.set_file_mode(False)
        assert not d.file_mode
        d.set_file_mode(True)
        assert d.file_mode

    def test_is_manufacturer_ti(self):
        assert brand_ti('80:6f:b0:')
        assert brand_ti('04:ee:03:')

    def test_is_manufacturer_microchip(self):
        assert brand_microchip('00:1e:c0:')

    def test_constructor_ok(self, fake_ble_factory):
        lc_ble = (fake_ble_factory())(mac_mc)
        assert lc_ble

    def test_constructor_exception(self, fake_ble_factory):
        with pytest.raises(bluepy.btle.BTLEException):
            (fake_ble_factory())(mac_un)

    def test_open_ok(self, fake_ble_factory):
        lc_ble = (fake_ble_factory())(mac_ti)
        lc_ble.open()
        assert lc_ble.per

    def test_open_bad(self, fake_ble_factory):
        lc_ble = (fake_ble_factory(FakePeripheralEx))(mac_ti)
        # provokes to go to Except() line in open()
        lc_ble.open()

    def test_close_ok(self, fake_ble_factory):
        lc_ble = (fake_ble_factory())(mac_ti)
        lc_ble.open()
        assert lc_ble.close()

    def test_close_bad(self, fake_ble_factory):
        lc_ble = (fake_ble_factory())(mac_ti)
        assert not lc_ble.close()

    def test_get_command_wait_time(self, fake_ble_factory):
        lc_ble = (fake_ble_factory())(mac_ti)
        t_s = time.time()
        t_e = time.time() + lc_ble._cmd_wait_time('DIR')
        # WAIT_TIME of this command + 1
        assert 2 <= t_e - t_s <= 3

    def test_command_no_answer_required(self, fake_ble_factory):
        lc_ble = (fake_ble_factory())(mac_ti)
        lc_ble.open()
        lc_ble.characteristic = FakeCharacteristic()
        assert lc_ble._command('sleep') is None

    def test_command_yes_answer_required(self, fake_ble_factory):
        lc_ble = (fake_ble_factory(m=w_a, rv=b'STS\t\t\t0201'))(mac_ti)
        lc_ble.open()
        lc_ble.characteristic = FakeCharacteristic()
        assert lc_ble._command('STS') is not None

    def test_command_answer_internal(self, fake_ble_factory):
        lc_ble = (fake_ble_factory(m=w_a, rv=b'STS\t\t\t0201'))(mac_ti)
        lc_ble.delegate.buf = b'STS\t\t\t0201'
        assert lc_ble._wait_cmd_ans('STS') == b'STS\t\t\t0201'

    def test_command_answer_shortcut(self, fake_ble_factory):
        lc_ble = (fake_ble_factory())(mac_ti)
        lc_ble.delegate.buf = b'GET 00'
        assert lc_ble._done_cmd_ans('GET')
        lc_ble.delegate.buf = b'\x04\n\r'
        assert lc_ble._done_cmd_ans('DIR')

    def test_get_time_ok(self, fake_ble_factory):
        _rv = [b'GTM', b'131999/12/12', b'11:12:13']
        lc_ble = (fake_ble_factory(m=cmd, rv=_rv))(mac_ti)
        expected = datetime.datetime(1999, 12, 12, 11, 12, 13)
        assert lc_ble.get_time() == expected

    def test_get_time_bad(self, fake_ble_factory):
        lc_ble = (fake_ble_factory(m=cmd, rv=False))(mac_ti)
        assert not lc_ble.get_time()

    def test_get_time_exception(self, fake_ble_factory):
        _rv = [b'GTM', b'130/0/0', b'11:12:13']
        lc_ble = (fake_ble_factory(m=cmd, rv=_rv))(mac_ti)
        assert not lc_ble.get_time()

    def test_ls(self, fake_ble_factory):
        lc_ble = (fake_ble_factory(m=cmd, rv=None))(mac_ti)
        assert not lc_ble._ls()

    def test_ls_lid_ok(self, fake_ble_factory):
        _rv = [b'.', b'..', b'a.lid', b'76', b'b.csv', b'10']
        lc_ble = (fake_ble_factory(m=_ls, rv=_rv))(mac_ti)
        assert lc_ble.ls_lid() == {'a.lid': 76}

    def test_ls_lid_ignore(self, fake_ble_factory):
        _rv = [b'.', b'..', b'\x04']
        lc_ble = (fake_ble_factory(m=_ls, rv=_rv))(mac_ti)
        assert lc_ble.ls_lid() == {}

    def test_ls_lid_bad(self, fake_ble_factory):
        _rv = [b'ERR']
        lc_ble = (fake_ble_factory(m=_ls, rv=_rv))(mac_ti)
        assert lc_ble.ls_lid() == [b'ERR']

    def test_ls_lid_none(self, fake_ble_factory):
        _rv = None
        lc_ble = (fake_ble_factory(m=_ls, rv=_rv))(mac_ti)
        assert not lc_ble.ls_lid()

    def test_ls_not_lid_ok(self, fake_ble_factory):
        _rv = [b'.', b'..', b'a.lid', b'76', b'b.csv', b'10']
        lc_ble = (fake_ble_factory(m=_ls, rv=_rv))(mac_ti)
        assert lc_ble.ls_not_lid() == {'b.csv': 10}

    def test_ls_not_lid_ignore(self, fake_ble_factory):
        _rv = [b'.', b'..', b'\x04']
        lc_ble = (fake_ble_factory(m=_ls, rv=_rv))(mac_ti)
        assert lc_ble.ls_not_lid() == {}

    def test_ls_not_lid_bad(self, fake_ble_factory):
        _rv = [b'ERR']
        lc_ble = (fake_ble_factory(m=_ls, rv=_rv))(mac_ti)
        assert lc_ble.ls_not_lid() == [b'ERR']

    def test_ls_not_lid_none(self, fake_ble_factory):
        _rv = None
        lc_ble = (fake_ble_factory(m=_ls, rv=_rv))(mac_ti)
        assert not lc_ble.ls_not_lid()
