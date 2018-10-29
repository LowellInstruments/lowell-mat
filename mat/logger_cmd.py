from abc import ABC, abstractmethod


class LoggerCmd(ABC):
    def __init__(self):
        self.tag = self._tag()
        self.length_str = self._length_str()
        self.data = self._data()

    def result(self):
        if self.tag == "ERR":
            return None
        return self.data

    def cmd_str(self):
        return self.tag + ' ' + self.length_str + self.data

    @abstractmethod
    def _tag(self):
        pass

    @abstractmethod
    def _length_str(self):
        pass

    @abstractmethod
    def _data(self):
        pass
