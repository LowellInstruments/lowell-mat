import threading
import time
import subprocess as sp
import pika
from coverage.annotate import os
from getmac import get_mac_address
from pika.exceptions import AMQPError, ProbableAccessDeniedError


def _p(s):
    print(s, flush=True)


def _u():
    url = 'amqps://{}:{}/{}'
    _user = 'dfibpovr'
    _rest = 'rqMn0NIFEjXTBtrTwwgRiPvcXqfCsbw9@chimpanzee.rmq.cloudamqp.com'
    return url.format(_user, _rest, _user)


def _get_ngrok_bin_name() -> str:
    _s = os.uname().nodename
    _m = os.uname().machine
    if _m == 'armv7l':
        return 'ngrok_rpi'
    if _s == 'rasberrypi' or _s == 'rpi':
        return 'ngrok_rpi'
    return 'ngrok_x64'


def _mq_get_ch():
    url = _u()
    _pars = pika.URLParameters(url)
    _pars.socket_timeout = 5
    _conn = pika.BlockingConnection(_pars)
    return _conn.channel()


def mq_exchange_for_slaves():
    _ch = _mq_get_ch()
    _ch.exchange_declare(exchange='li_slaves', exchange_type='fanout')
    return _ch


def mq_exchange_for_masters():
    _ch = _mq_get_ch()
    _ch.exchange_declare(exchange='li_masters', exchange_type='fanout')
    return _ch


def _who(_, macs):
    return 0, ' '.join([m for m in macs if m and m != '*'])


def _bye(_, macs):
    return 0, 'bye you from lnmp in {}'.format(macs)


def _query(_, macs):
    _grep = 'ps aux | grep nxserver | grep -v grep'
    _rv = sp.run(_grep, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    cond_nx = _rv.returncode == 0
    _grep = 'ps aux | grep _____name___agent___ | grep -v grep'
    _rv = sp.run(_grep, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    cond_ag = _rv.returncode == 0
    s = 'NX {} agent {} at {}'.format(cond_nx, cond_ag, macs)
    return 0, s


def _start_nx(_, macs):
    return 0, 'fake nx started at {}'.format(macs)


def _start_agent(_, macs):
    return 0, 'fake agent started at {}'.format(macs)


def _kill(_, macs):
    ngrok_bin = _get_ngrok_bin_name()
    cmd = 'killall {}'.format(ngrok_bin)
    _rv = sp.run([cmd], shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    return 0, '{} done at {}'.format(cmd, macs)


def _parse(s: bytes):
    if not s:
        return b'error lnp: cmd empty'

    # parse lnp stuff
    s = s.decode().split(' ')

    # who am I
    _my_macs = [get_mac_address(interface='wlo1'),
                get_mac_address(interface='wlan0'),
                '*']

    # is this frame for us
    if len(s) >= 2:
        # todo: do this for more universal mac names
        mac = s[1]
        if mac not in _my_macs:
            return b'error lnp: cmd not for us'

    # search the function
    cmd = s[0]
    fxn_map = {
        'bye!': _bye,
        'who': _who,
        'query': _query,
        'start_nx': _start_nx,
        'start_agent': _start_agent,
        'kill': _kill
    }
    fxn = fxn_map[cmd]
    # noinspection PyArgumentList
    return fxn(s, _my_macs)


class AgentLLP(threading.Thread):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.ch_pub = None
        self.ch_sub = None

    def _get_ch_pub(self):
        self.ch_pub = mq_exchange_for_slaves()

    def _get_ch_sub(self):
        self.ch_sub = mq_exchange_for_masters()

    def run(self):
        while 1:
            try:
                self._sub_n_rx()
                print('agent loop end')
            except (Exception, AMQPError) as e:
                print('agent_lnmp rx_exc -> {}'.format(e))

    def _pub(self, _what):
        self._get_ch_pub()
        self.ch_pub.basic_publish(exchange='li_slaves', routing_key='', body=_what)
        print('<- slave  pub: {}'.format(_what))
        self.ch_pub.close()

    def _sub_n_rx(self):
        def _rx_cb(ch, method, properties, body):
            print('-> slave  rx_cb: {}'.format(body))
            ans = _parse(body)
            # and" (0, description)
            self._pub(ans[1])

        self._get_ch_sub()
        rv = self.ch_sub.queue_declare(queue='', durable=True, exclusive=True)
        q = rv.method.queue
        self.ch_sub.queue_bind(exchange='li_masters', queue=q)
        self.ch_sub.basic_consume(queue=q, on_message_callback=_rx_cb, auto_ack=True)
        self.ch_sub.start_consuming()


class ClientLLP:
    # pubs to 'li_masters', subs from 'li_slaves'
    def __init__(self, url, sig=None):
        self.url = url
        self.ch_pub = None
        self.ch_sub = None
        self.th_sub = threading.Thread(target=self._sub_n_rx)
        self.th_sub.start()
        self.tx_last = None
        self.sig = sig

    def _get_ch_pub(self):
        self.ch_pub = mq_exchange_for_masters()

    def _get_ch_sub(self):
        self.ch_sub = mq_exchange_for_slaves()

    def tx(self, _what: str):
        try:
            self._get_ch_pub()
            self.ch_pub.basic_publish(exchange='li_masters', routing_key='', body=_what)
            _p('<- master pub: {}'.format(_what))
            self.tx_last = _what
            self.ch_pub.close()
        except ProbableAccessDeniedError:
            e = 'error AMQP'
            self.sig.emit(self.tx_last, e)

    # careful: this may collect answers from forgotten nodes :)
    def _sub_n_rx(self):
        def _rx_cb(ch, method, properties, body):
            s = body.decode()
            _p('-> master rx_cb: {}'.format(s))

        self._get_ch_sub()
        rv = self.ch_sub.queue_declare(queue='', exclusive=True)
        q = rv.method.queue
        self.ch_sub.queue_bind(exchange='li_slaves', queue=q)
        self.ch_sub.basic_consume(queue=q, on_message_callback=_rx_cb, auto_ack=True)
        self.ch_sub.start_consuming()


class MyTestLLPAgent:
    _url = _u()

    def my_test_llp_cmd(self):
        ag = AgentLLP(self._url)
        ag.start()
        time.sleep(2)
        list_of_cmd = ['who', 'query']
        ac = ClientLLP(self._url)
        for cmd in list_of_cmd:
            ac.tx(cmd)


if __name__ == '__main__':
    _t = MyTestLLPAgent()
    _t.my_test_llp_cmd()
