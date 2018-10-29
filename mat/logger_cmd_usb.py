from mat.logger_cmd import LoggerCmd


class LoggerCmdUsb(LoggerCmd):
    def __init__(self, port):
        # order is important
        self.port = port
        super(LoggerCmdUsb, self).__init__()

    def _tag(self):
        return self._first_real_char() + self.port.read(2).decode('IBM437')

    def _first_real_char(self):
        in_char = self.port.read(1).decode('IBM437')
        while in_char and ord(in_char) in [10, 13]:
            in_char = self.port.read(1).decode('IBM437')
        if not in_char:
            raise RuntimeError("Unable to read from port")
        return in_char

    def _length_str(self):
        return self.port.read(3).decode('IBM437')[1:]

    def _data(self):
        try:
            length = int(self.length_str, 16)
        except ValueError:
            raise RuntimeError(
                'Invalid length string, %s, received' % self.length_str)
        data = self.port.read(length).decode('IBM437')
        if length != len(data):
            raise RuntimeError(
                'Incorrect data length. Expecting %d received %d' %
                (length, len(data)))
        return data
