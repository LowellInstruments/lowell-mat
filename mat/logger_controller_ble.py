import bluepy.btle as bluepy
import json
from datetime import datetime
import time
from mat.logger_controller import LoggerController
from mat.logger_controller_ble_cc26x2 import LoggerControllerBLECC26X2
from mat.logger_controller_ble_rn4020 import LoggerControllerBLERN4020
from mat.xmodem_ble import xmodem_get_file, XModemException


class Delegate(bluepy.DefaultDelegate):
    def __init__(self):
        bluepy.DefaultDelegate.__init__(self)
        self.buf = bytes()
        self.x_buf = bytes()
        self.file_mode = False

    def handleNotification(self, c_handle, data):
        if not self.file_mode:
            self.buf += data
        else:
            self.x_buf += data

    def clr_buf(self):
        self.buf = bytes()

    def clr_x_buf(self):
        self.x_buf = bytes()

    def set_file_mode(self, state):
        self.file_mode = state


class LoggerControllerBLE(LoggerController):

    WAIT = {
        'BTC': 3, 'GET': 3, 'RWS': 2, 'GDO': 3.2,
        'DIR': 2, 'FRM': 2, 'CFG': 2, '#T1': 10
    }

    def __init__(self, mac):
        super().__init__(mac)
        self.address = mac
        self.per = None
        self.svc = None
        self.cha = None
        # set underlying BLE class
        if brand_ti(mac):
            self.und = LoggerControllerBLECC26X2(self)
        elif brand_microchip(mac):
            self.und = LoggerControllerBLERN4020(self)
        else:
            raise bluepy.BTLEException('unknown brand')
        self.delegate = Delegate()

    def open(self):
        for counter in range(3):
            try:
                self.per = bluepy.Peripheral(self.address)
                # connection update request from cc26x2 takes 1000 ms
                time.sleep(1.1)
                self.per.setDelegate(self.delegate)
                self.svc = self.per.getServiceByUUID(self.und.UUID_S)
                self.cha = self.svc.getCharacteristics(self.und.UUID_C)[0]
                desc = self.cha.valHandle + 1
                self.per.writeCharacteristic(desc, b'\x01\x00')
                self.open_after()
                return True
            except (AttributeError, bluepy.BTLEException):
                pass
        return False

    def ble_write(self, data, response=False):  # pragma: no cover
        self.und.ble_write(data, response)

    def open_after(self):
        self.und.open_after()

    def close(self):
        try:
            self.per.disconnect()
            return True
        except AttributeError:
            return False

    def _command(self, *args):
        # reception vars
        self.delegate.clr_buf()
        self.delegate.set_file_mode(False)

        # transmission vars
        cmd = str(args[0])
        arg = str(args[1]) if len(args) == 2 else ''
        n = '{:02x}'.format(len(arg)) if arg else ''
        to_send = cmd + ' ' + n + arg

        # send binary command
        if cmd in ('sleep', 'RFN'):
            to_send = cmd
        to_send += chr(13)
        self.ble_write(to_send.encode())

        # wait, or not, for command answer
        if cmd in ('RST', 'sleep', 'BSL'):
            return None

        # answer as list of bytes() objects
        ans = self._wait_cmd_ans(cmd).split()
        return ans

    def command(self, *args, retries=3):    # pragma: no cover
        for retry in range(retries):
            try:
                ans = self._command(*args)
                if ans:
                    return ans
            except bluepy.BTLEException:
                # to be managed by app
                s = 'BLE command() exception'
                raise bluepy.BTLEException(s)
        return None

    def _done_cmd_ans(self, cmd):
        # not all commands do this, recall race conditions
        if cmd == 'GET' and self.delegate.buf == b'GET 00':
            return True
        if cmd == 'DIR' and self.delegate.buf.endswith(b'\x04\n\r'):
            return True

    def _cmd_wait_time(self, tag):
        return self.WAIT[tag] if tag in self.WAIT else 1

    def _wait_cmd_ans(self, cmd):    # pragma: no cover
        tag = cmd[:3]
        till = time.time() + self._cmd_wait_time(tag)
        while time.time() < till:
            if self.per.waitForNotifications(0.1):
                # useful for multiple answer commands
                till += 0.1
            if self._done_cmd_ans(tag):
                break
        return self.delegate.buf

    def get_time(self):
        self.delegate.clr_buf()
        ans = self.command('GTM')
        if not ans:
            return False
        try:
            _time = ans[1].decode()[2:] + ' '
            _time += ans[2].decode()
            return datetime.strptime(_time, '%Y/%m/%d %H:%M:%S')
        except (ValueError, IndexError):
            print(ans)
            return False

    def get_file(self, filename, folder, size):  # pragma: no cover
        self.delegate.clr_buf()
        self.delegate.clr_x_buf()
        self.delegate.set_file_mode(False)
        ans = self.command('GET', filename)

        try:
            file_dl = self._save_file(ans, filename, folder, size)
        except XModemException:
            file_dl = False
        finally:
            self.delegate.set_file_mode(False)

        # do not remove, gives logger's XMODEM time to end
        time.sleep(2)
        return file_dl

    def _save_file(self, ans_get, path, folder, s):   # pragma: no cover
        if ans_get is not None and ans_get[0] == b'GET':
            self.delegate.set_file_mode(True)
            r, bytes_rx = xmodem_get_file(self)
            if r:
                full_path = folder + '/' + path
                with open(full_path, 'wb') as f:
                    f.write(bytes_rx)
                    f.truncate(int(s))
            return True
        return False

    # wrapper function for DIR command
    def _ls(self):
        self.delegate.clr_buf()
        # e.g. [b'.', b'..', b'a.lid', b'76', b'b.csv', b'10']
        return self.command('DIR 00', retries=1)

    def ls_ext(self, ext):
        ans = self._ls()
        if ans in [[b'ERR'], None]:
            # e.g. logger not stopped
            return ans
        return _ls_ext_build(ans, ext)

    def ls_lid(self):
        return self.ls_ext(b'lid')

    def ls_gps(self):
        return self.ls_ext(b'gps')

    def ls_not_lid(self):
        ans = self._ls()
        if ans in [[b'ERR'], None]:
            # e.g. logger not stopped
            return ans
        return _ls_not_lid_build(ans)

    def send_cfg(self, cfg_file_as_json_dict):  # pragma: no cover
        _as_string = json.dumps(cfg_file_as_json_dict)
        return self.command("CFG", _as_string, retries=1)


# utilities
def _ls_ext_build(lis, ext):
    files, idx = {}, 0
    while idx < len(lis):
        name = lis[idx]
        if name in [b'\x04']:
            break
        if name.endswith(ext) and name not in [b'.', b'..']:
            files[name.decode()] = int(lis[idx + 1])
        idx += 2
    return files


def _ls_not_lid_build(lis):
    files, idx = {}, 0
    while idx < len(lis):
        name = lis[idx]
        if name in [b'\x04']:
            break
        if not name.endswith(b'lid') and name not in [b'.', b'..']:
            files[name.decode()] = int(lis[idx + 1])
        idx += 2
    return files


def brand_ti(mac):
    return not brand_microchip(mac)


def brand_microchip(mac):
    mac = mac.lower()
    return mac.startswith('00:1e:c0:')
