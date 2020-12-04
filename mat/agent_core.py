import socket
import threading
import time
import pynng
from mat.agent_ble import AgentBLE
from pynng import Pair0


PORT_CORE_SERVER = 12804


def _p(s):
    print(s, flush=True)


def _good_core_prefix(s):
    if not s or len(s) < 4:
        return False
    if s == 'bye!':
        return s
    if s[:4] in ('ble ', 'gps ', 'ngr '):
        return s[4:]


def _check_url_syntax(s):
    _transport = s.split(':')[0]
    _adr = s.split('//')[0]
    if _adr.startswith('localhost') or _adr.startswith('127.0'):
        _p('careful, localhost not same as IP')
    assert _transport in ['tcp4', 'tcp6']
    assert _transport not in ['tcp']


class AgentCore:
    def __init__(self, core_url):
        self.sk = None
        self.url = core_url
        self.core_loop()

    def _in_core_cmd(self):
        """ receive NLE client commands, silent timeouts """
        try:
            _in = self.sk.recv()
            if _in:
                _in = _in.decode()
                _p('core in -> {}'.format(_in))
        except pynng.Timeout:
            _in = None
        return _in

    def _out_core_ans(self, a):
        # agents return (int_rv, s)
        try:
            self.sk.send(a[1].encode())
        except pynng.Timeout:
            # _p('_s_out timeout')
            pass

    def core_loop(self):
        while 1:
            # create socket and BLE thread
            _check_url_syntax(self.url)
            self.sk = Pair0(send_timeout=1000)
            self.sk.listen(self.url)
            self.sk.recv_timeout = 1000
            th_ble = AgentBLE()
            th_ble.start()

            _p('ag_core listening on {}'.format(self.url))
            while 1:
                # just parse format, not much content
                _in = self._in_core_cmd()
                _in = _good_core_prefix(_in)
                if not _in:
                    # _p('bad core prefix {}'.format(_in))
                    continue

                # good core command for our threads
                th_ble.q_in.put(_in)
                _out = th_ble.q_out.get()
                self._out_core_ans(_out)
                if _in == 'bye!':
                    break


class TestAgentCore:
    u = 'tcp4://localhost:{}'.format(PORT_CORE_SERVER)
    m = '60:77:71:22:c8:18'
    # m = '60:77:71:22:c8:08'

    def test_core_constructor(self):
        th_c = threading.Thread(target=AgentCore, args=(self.u,))
        th_c.start()
        list_of_cmd = ['bye!']
        _fake_client_send_n_wait(self.u, list_of_cmd, 1000, self.m)

    def test_core_commands(self):
        th_c = threading.Thread(target=AgentCore, args=(self.u,))
        th_c.start()
        list_of_cmd = ['query', 'status', 'get_time', 'ls_lid',
                       'query', 'bye!']
        _fake_client_send_n_wait(self.u, list_of_cmd, 20 * 1000, self.m)


def _fake_client_send_n_wait(_url, list_out, timeout_ms: int, mac):
    # todo: do BLE_TIMEOUT_CALCULATION_CMD function
    _ = pynng.Pair0(send_timeout=timeout_ms)
    _.recv_timeout = timeout_ms
    _.dial(_url)
    now = time.perf_counter()
    for o in list_out:
        o = 'ble {} {}'.format(o, mac)
        _.send(o.encode())
        _in = _.recv()
        print('\t{}'.format(_in.decode()))
    _p('done in {}'.format(time.perf_counter() - now))
