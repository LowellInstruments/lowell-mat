class LoggerCmd:
    def __init__(self, port):
        self.port = port
        self.tag = self._tag()
        self.length_str = self._length_str()
        self.data = self._data()

    def result(self):
        if self.tag == "ERR":
            return None
        return self.data

    def _tag(self):
        return self._first_real_char() + self.port.read(2).decode('IBM437')

    def _first_real_char(self):
        inchar = self.port.read(1).decode('IBM437')
        while inchar and ord(inchar) in [10, 13]:
            inchar = self.port.read(1).decode('IBM437')
        if not inchar:
            raise RuntimeError("Unable to read from port")
        return inchar

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

    def cmd_str(self):
        return self.tag + ' ' + self.length_str + self.data
