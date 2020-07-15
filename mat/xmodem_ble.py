import time
import crc16


SOH = b'\x01'
STX = b'\x02'
EOT = b'\x04'
ACK = b'\x06'
CAN = b'\x18'
NAK = b'\x15'


# download function, initial purge to start fresh, exception on error
def xmodem_get_file(lc_ble):
    _purge(lc_ble)
    file_built = bytes()
    retries = 0
    sending_c = True

    while True:
        _tx_c_ish(lc_ble, sending_c)

        # control stage: wait 1st byte of incoming frame
        _rx_ctrl_byte(lc_ble)

        # data stage: frame arrived, check byte SOH, STX, CAN...
        ctrl_byte, frame_len = _parse_ctrl_byte(lc_ble)
        if ctrl_byte == EOT:
            return True, file_built

        # data stage: try to receive data, note 'end_time' is shared
        end_time = time.time() + 1
        retries = _rx_frame(lc_ble, frame_len, retries, end_time)
        if not _rx_frame_timeout(lc_ble, sending_c, retries, end_time):
            bunch = _parse_frame(lc_ble, sending_c, retries, file_built)
            sending_c, retries, file_built = bunch


def _tx_c_ish(lc_ble, sending_c):
    lc_ble.delegate.x_buf = bytes()
    if sending_c:
        # print('--> c')
        lc_ble.ble_write(b'C')


def _rx_ctrl_byte(lc_ble):
    timeout = time.time() + 1
    while True:
        if time.time() > timeout:
            # happens very rarely but it does
            # print('K')
            raise XModemException('timeout waiting XMD ctrl byte')
        lc_ble.per.waitForNotifications(1)
        if len(lc_ble.delegate.x_buf) >= 1:
            break


def _parse_ctrl_byte(lc_ble):
    control_byte = bytes([lc_ble.delegate.x_buf[0]])
    if control_byte == SOH:
        # print('<-- s')
        return SOH, 128 + 5
    elif control_byte == STX:
        return STX, 1024 + 5
    elif control_byte == EOT:
        # print('v')
        _ack(lc_ble)
        return EOT, None
    # bad: received CAN or strange control byte
    else:
        # print('W')
        _can(lc_ble)
        raise XModemException('xmodem exception: getting control byte.')


def _rx_frame(lc_ble, frame_len, retries, timeout):
    while True:
        if time.time() > timeout:
            retries += 1
            break
        lc_ble.per.waitForNotifications(0.01)
        if len(lc_ble.delegate.x_buf) >= frame_len:
            break
    # print(lc_ble.delegate.x_buf)
    return retries


def _rx_frame_timeout(lc_ble, sending_c, retries, timeout):
    # easier to restart than recover a lost 'C'
    if time.time() > timeout and sending_c:
        # print('I')
        raise XModemException('xmodem exception: timeout waiting frame post-C')
    # timeout, check retries left
    if time.time() > timeout and retries >= 3:
        # print('F')
        _can(lc_ble)
        raise XModemException('xmodem exception: timeout data, 0 retries left')
    elif time.time() > timeout and retries < 3:
        # print('f', end='')
        _purge(lc_ble)
        _nak(lc_ble)
        # bad: timeout
        return True
    # nice: no timeout during frame receiving
    return False


def _parse_frame(lc_ble, sending_c, retries, whole_file):
    if _frame_check_crc(lc_ble):
        # print('<-- crc ok')
        sending_c = False
        retries = 0
        whole_file += lc_ble.delegate.x_buf[3:-2]
        # print('.', end='')
        _ack(lc_ble)
    else:
        print('x', end='')
        _nak(lc_ble)
    return sending_c, retries, whole_file


def _purge(lc_ble):
    end_time = time.time() + 0.1
    while time.time() < end_time:
        lc_ble.per.waitForNotifications(0.01)


def _ack(lc_ble):
    # print('--> a')
    lc_ble.ble_write(ACK)


def _nak(lc_ble):
    lc_ble.ble_write(NAK)


def _can(lc_ble):
    lc_ble.ble_write(CAN)
    lc_ble.ble_write(CAN)
    lc_ble.ble_write(CAN)


# calculate CRC omitting proper fields
def _frame_check_crc(lc_ble):
    data = lc_ble.delegate.x_buf[3:-2]
    received_crc_bytes = lc_ble.delegate.x_buf[-2:]
    calculated_crc_int = crc16.crc16xmodem(data)
    calculated_crc_bytes = calculated_crc_int.to_bytes(2, byteorder='big')
    # print(len(lc_ble.delegate.x_buf))
    if calculated_crc_bytes == received_crc_bytes:
        return True
    else:
        return False


# xmodem fatal exceptions controlled on app, this file controls non fatal ones
class XModemException(Exception):
    pass
