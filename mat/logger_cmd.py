from mat.logger_controller import CommunicationError
import re


class LoggerCmd:
    def __init__(self, port):
        self.port = port
        self.tag = self._read_real_chars(3)
        self.length_str = self._length_str()
        self.data = self._data()

    def result(self):
        if self.tag == "ERR":
            return None
        return self.data

    def _read_real_chars(self, n_chars):
        """ Skip CR and NL """
        count = 0
        tag = ''
        while count < n_chars:
            inchar = self.port.read(1).decode('IBM437')
            if not inchar:
                raise CommunicationError('Unable to read from port')
            if ord(inchar) in [10, 13]:
                continue
            tag += inchar
            count += 1
        return tag

    def _length_str(self):
        length_str = self._read_real_chars(3)
        length_re = re.search(' ([0-9A-Fa-f]+)', length_str)
        if not length_re:
            raise CommunicationError('Length format is incorrect')
        return length_re.group(1)

    def _data(self):
        try:
            length = int(self.length_str, 16)
        except ValueError:
            raise RuntimeError(
                'Invalid length string, %s, received' % self.length_str)
        data = self.port.read(length).decode('IBM437')
        if length != len(data):
            raise CommunicationError(
                'Incorrect data length. Expecting %d received %d' %
                (length, len(data)))
        return data

    def cmd_str(self):
        return self.tag + ' ' + self.length_str + self.data
