import threading
import time
from mat.logger_controller import STOP_CMD, STATUS_CMD
from mat.logger_controller_ble import LoggerControllerBLE
import queue


def _p(s):
    print(s, flush=True)


def _stringify_dir_ans(_d_a):
    if _d_a == b'ERR':
        return 'ERR'
    # _d_a: {'file.lid': 2182}
    rv = ''
    for k, v in _d_a.items():
        rv += '{} {} '.format(k, v)
    return rv


def _mac(s):
    return s.rsplit(' ', 1)[-1]


def _sp(s, i):
    return s.rsplit(' ')[i]


def _e(s):
    return 'error {}'.format(s)


# can be threaded
class AgentBLE(threading.Thread):
    def __init__(self, threaded, hci_if=0):
        super().__init__()
        self.lc = None
        self.h = hci_if
        # an AgentBLE has no threads
        self.q_in = queue.Queue()
        self.q_out = queue.Queue()
        if not threaded:
            self.loop_ble()

    def _parse(self, s):
        # s: '<cmd> <args> <mac>'
        cmd, *_ = s.split(' ', 1)
        fxn_map = {
            'status': self.status,
            'connect': self.connect,
            'disconnect': self.disconnect,
            'get_time': self.get_time,
            'set_time': self.set_time,
            'ls_lid': self.ls_lid,
            'ls_not_lid': self.ls_not_lid,
            'stop': self.stop,
            'get_file': self.get_file,
            'bye!': self.bye,
            'query': self.query
        }
        fxn = fxn_map[cmd]
        # noinspection PyArgumentList
        return fxn(s)

    def loop_ble(self):
        while 1:
            _in = self.q_in.get()
            _out = self._parse(_in)
            self.q_out.put(_out)
            if _in == 'bye!':
                break

    def run(self):
        self.loop_ble()

    def status(self, s):
        # s: 'status <mac>'
        mac = _mac(s)
        rv = self.connect(mac)
        if rv[0] == 1:
            return rv
        rv = self.lc.command(STATUS_CMD)
        if rv[0] == b'STS' and len(rv[1]) == 4:
            a = 'STS {}'.format(rv[1].decode())
            return 0, a
        return 1, _e(' error STS {}'.format(rv[1].decode()))

    def connect(self, s):
        # s: 'connect <mac>' but it may be already
        mac = _mac(s)
        if self.lc:
            a = self.lc.address
            if a == mac and self.lc.per.getState() == "conn":
                return 0, 'already connected'

        # cut any current connection w/ different mac
        if self.lc:
            self.lc.close()

        # connecting asked mac
        _p('<- connect {} {}'.format(mac, self.h))
        self.lc = LoggerControllerBLE(mac, self.h)
        rv = self.lc.open()
        if rv:
            return 0, 'connected to {}'.format(mac)
        return 1, 'connection fail'

    def disconnect(self, _=None):
        # does not use any parameter
        _p('<- disconnect')
        if self.lc and self.lc.close():
            return 0, 'disconnected'
        return 0, 'was not connected'

    def get_time(self, s):
        # s: 'get_time <mac>'
        mac = _mac(s)
        rv = self.connect(mac)
        if rv[0] == 1:
            return rv
        rv = self.lc.get_time()
        # this already is a string
        if len(str(rv)) == 19:
            return 0, str(rv)
        return 1, _e('error GTM {}'.format(rv[1].decode()))

    def set_time(self, s):
        # s: 'set_time <mac>'
        mac = _mac(s)
        rv = self.connect(mac)
        if rv[0] == 1:
            return rv
        rv = self.lc.sync_time()
        print(rv)
        if rv == [b'STM', b'00']:
            return 0, 'STM 00'
        return 1, _e('error STM {}'.format(rv[1].decode()))

    def ls_lid(self, s):
        mac = _mac(s)
        rv = self.connect(mac)
        if rv[0] == 1:
            return rv
        rv = self.lc.ls_lid()
        if type(rv) == dict:
            return 0, _stringify_dir_ans(rv)
        return 1, rv

    def ls_not_lid(self, s):
        mac = _mac(s)
        rv = self.connect(mac)
        if rv[0] == 1:
            return rv
        rv = self.lc.ls_not_lid()
        if type(rv) == dict:
            return 0, _stringify_dir_ans(rv)
        return 1, rv

    def stop(self, s):
        mac = _mac(s)
        rv = self.connect(mac)
        if rv[0] == 1:
            return rv
        rv = self.lc.command(STOP_CMD)
        if rv == [b'STP', b'00']:
            return 0, 'logger stopped'
        return 1, 'logger not stopped'

    @staticmethod
    def bye(_):
        return 0, 'bye you from ble'

    def query(self, _):
        a = 'agent ble is {}'
        if not self.lc:
            return 0, a.format('empty')
        if not self.lc.per:
            return 0, a.format('empty')
        return 0, a.format(self.lc.per.getState())

    def get_file(self, s):
        # s: 'get_file <file> <fol> <size> <mac>
        mac = _mac(s)
        file = _sp(s, 1)
        fol = _sp(s, 2)
        size = _sp(s, 3)

        rv = self.connect(mac)
        if rv[0] == 1:
            return rv

        # todo: do this and pass sig as parameter
        rv = self.lc.get_file(file, fol, size)
        if rv:
            return 0, 'file {} size {}'.format(file, size)
        return 1, 'err get_file {} size {}'.format(file, 0)

    def close(self):
        return self.disconnect()


class TestBLEAgent:
    # m = '60:77:71:22:c8:08'
    m = '60:77:71:22:c8:18'

    def test_disconnect_was_not_connected(self):
        ag = AgentBLE(threaded=1)
        ag.start()
        # skip connect() on purpose
        mac = self.m
        s = '{} {}'.format('disconnect', mac)
        rv = _q(ag, s)
        assert rv[1] == 'was not connected'
        _q(ag, 'bye!')

    def test_connect_disconnect(self):
        ag = AgentBLE(threaded=1)
        ag.start()
        mac = self.m
        s = '{} {}'.format('disconnect', mac)
        _q(ag, s)
        s = '{} {}'.format('connect', mac)
        rv = _q(ag, s)
        assert rv[0] == 0
        s = '{} {}'.format('disconnect', mac)
        rv = _q(ag, s)
        assert rv[0] == 0
        assert rv[1] == 'disconnected'
        _q(ag, 'bye!')

    def test_connect_error(self):
        # may take a bit more time, 3 retries connect
        ag = AgentBLE(threaded=1)
        ag.start()
        mac = '11:22:33:44:55:66'
        s = '{} {}'.format('disconnect', mac)
        _q(ag, s)
        s = '{} {}'.format('connect', mac)
        rv = _q(ag, s)
        assert rv[0] == 1
        _q(ag, 'bye!')

    def test_connect_already(self):
        mac = self.m
        ag = AgentBLE(threaded=1)
        ag.start()
        s = '{} {}'.format('disconnect', mac)
        _q(ag, s)
        s = '{} {}'.format('connect', mac)
        _q(ag, s)
        s = '{} {}'.format('connect', mac)
        rv = _q(ag, s)
        assert rv[1] == 'already connected'
        _q(ag, 'bye!')

    def test_get_time_thrice_few_time_same_connection(self):
        ag = AgentBLE(threaded=1)
        ag.start()
        mac = self.m
        s = '{} {}'.format('disconnect', mac)
        _q(ag, s)
        # the first command implicitly connects so takes > 1 second
        now = time.perf_counter()
        s = '{} {}'.format('get_time', mac)
        rv = _q(ag, s)
        assert rv[0] == 0
        el = time.perf_counter() - now
        assert el > 1
        _p('1st GTM {} took {}'.format(rv[1], el))
        # the next 2 are much faster
        now = time.perf_counter()
        s = '{} {}'.format('get_time', mac)
        rv = _q(ag, s)
        assert rv[0] == 0
        s = '{} {}'.format('get_time', mac)
        rv = _q(ag, s)
        assert rv[0] == 0
        el = time.perf_counter() - now
        _p('2nd & 3rd GTM {} took {}'.format(rv[1], el))
        assert el < .5
        _q(ag, 'bye!')

    def test_set_time(self):
        mac = self.m
        ag = AgentBLE(threaded=1)
        ag.start()
        s = '{} {}'.format('disconnect', mac)
        _q(ag, s)
        s = '{} {}'.format('set_time', mac)
        rv = _q(ag, s)
        assert rv[0] == 0
        _q(ag, 'bye!')

    def test_get_file(self):
        # this long test may take a long time
        mac = self.m
        ag = AgentBLE(threaded=1)
        ag.start()
        s = '{} {}'.format('disconnect', mac)
        _q(ag, s)
        file = '2006671_low_20201004_132205.lid'
        size = 299950
        fol = '.'
        s = 'get_file {} {} {} {}'.format(file, fol, size, mac)
        rv = _q(ag, s)
        assert rv[0] == 0
        _q(ag, 'bye!')

    def test_ls_lid(self):
        mac = self.m
        ag = AgentBLE(threaded=1)
        ag.start()
        s = 'disconnect {}'.format(mac)
        _q(ag, s)
        s = 'ls_lid {}'.format(mac)
        rv = _q(ag, s)
        _p(rv)
        assert rv[0] == 0
        _q(ag, 'bye!')

    def test_ls_not_lid(self):
        mac = self.m
        ag = AgentBLE(threaded=1)
        ag.start()
        s = 'disconnect {}'.format(mac)
        _q(ag, s)
        s = 'ls_not_lid {}'.format(mac)
        rv = _q(ag, s)
        _p(rv)
        assert rv[0] == 0
        _q(ag, 'bye!')

    def test_stop(self):
        mac = self.m
        ag = AgentBLE(threaded=1)
        ag.start()
        s = 'stop {}'.format(mac)
        rv = _q(ag, s)
        assert rv[0] == 0
        _q(ag, 'bye!')


def _q(_ag, _in):
    _ag.q_in.put(_in)
    # needed because of testing threads
    if _in == 'bye!':
        return
    _out = _ag.q_out.get()
    return _out
