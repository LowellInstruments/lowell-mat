import time
import crc16


SOH = b'\x01'
STX = b'\x02'
EOT = b'\x04'
ACK = b'\x06'
CAN = b'\x18'
NAK = b'\x15'
g_verbose = False


def _xmd_print(s):
    if g_verbose:
        print(s)


# download function, initial purge to start fresh, exception on error
def xmodem_get_file(lc, sig=None, verbose=False):
    global g_verbose
    g_verbose = verbose
    _purge(lc)
    file_built = bytes()
    _data_retries = 0
    sending_c = True

    while True:
        # steps here may raise Exception and return False
        ctrl_byte, frame_len = _ctrl_stage(lc, sending_c)
        if ctrl_byte == EOT:
            _xmd_print('-> EOT from logger')
            return True, file_built

        # data stage: try to receive data, note 'end_time' is shared
        _till = time.time() + 1
        _data_retries = _rx_frame(lc, frame_len, _data_retries, _till)
        if not _rx_frame_timeout(lc, sending_c, _data_retries, _till):
            bunch = _parse_frame(lc, sending_c, _data_retries, file_built)
            sending_c, _data_retries, file_built = bunch

        # for GUIs feedback, if any
        if sig:
            sig.emit()


def _tx_c_char(lc, sending_c):
    lc.dlg.x_buf = bytes()
    if sending_c:
        _xmd_print('--> c')
        lc.ble_write(b'C')


def _ctrl_stage(lc, sending_c):
    timeout = time.time() + 3
    while True:
        if time.time() > timeout:
            _xmd_print('K')
            raise XModemException('XMD: timeout rx ctrl')
        _tx_c_char(lc, sending_c)
        lc.per.waitForNotifications(1)
        if not len(lc.dlg.x_buf):
            continue
        _in_b = bytes([lc.dlg.x_buf[0]])
        if _in_b == SOH:
            _xmd_print('<- soh')
            return SOH, 128 + 5
        elif _in_b == STX:
            _xmd_print('<- stx')
            return STX, 1024 + 5
        elif _in_b == EOT:
            _xmd_print('<- eot')
            _ack(lc)
            return EOT, None
        else:
            _xmd_print('<- can_ctrl')
            _can(lc)
            raise XModemException('xmodem exception: getting control byte.')


def _rx_frame(lc_ble, frame_len, retries, timeout):
    while True:
        if time.time() > timeout:
            retries += 1
            break
        lc_ble.per.waitForNotifications(0.001)
        if len(lc_ble.dlg.x_buf) >= frame_len:
            break
    return retries


def _rx_frame_timeout(lc_ble, sending_c, retries, timeout):
    # easier to restart than recover a lost 'C'
    if time.time() > timeout and sending_c:
        _xmd_print('I')
        raise XModemException('XMD: timeout rx post-C')
    # timeout, check retries left
    if time.time() > timeout and retries >= 3:
        _xmd_print('F')
        _can(lc_ble)
        raise XModemException('XMD: timeout rx data, 0 retries left')
    elif time.time() > timeout and retries < 3:
        _xmd_print('f')
        _purge(lc_ble)
        _nak(lc_ble)
        # bad: timeout, but still retries left
        return True
    # nice: no timeout during frame receiving
    return False


def _parse_frame(lc_ble, sending_c, retries, whole_file):
    if _frame_check_crc(lc_ble):
        # print('<- crc ok')
        sending_c = False
        retries = 0
        whole_file += lc_ble.dlg.x_buf[3:-2]
        # print('.', end='')
        _ack(lc_ble)
    else:
        _xmd_print('bad_crc -> nak')
        _nak(lc_ble)
    return sending_c, retries, whole_file


def _purge(lc_ble):
    end_time = time.time() + 0.1
    while time.time() < end_time:
        lc_ble.per.waitForNotifications(0.01)


def _ack(lc_ble):
    _xmd_print('-> ack')
    lc_ble.ble_write(ACK)


def _nak(lc_ble):
    _xmd_print('-> nak')
    lc_ble.ble_write(NAK)


def _can(lc_ble):
    _xmd_print('-> can')
    lc_ble.ble_write(CAN)
    _xmd_print('-> can')
    lc_ble.ble_write(CAN)
    _xmd_print('-> can')
    lc_ble.ble_write(CAN)


# calculate CRC omitting proper fields
def _frame_check_crc(lc_ble):
    data = lc_ble.dlg.x_buf[3:-2]
    received_crc_bytes = lc_ble.dlg.x_buf[-2:]
    calculated_crc_int = crc16.crc16xmodem(data)
    calculated_crc_bytes = calculated_crc_int.to_bytes(2, byteorder='big')
    # print(len(lc_ble.dlg.x_buf))
    if calculated_crc_bytes == received_crc_bytes:
        return True
    else:
        return False


class XModemException(Exception):
    pass
