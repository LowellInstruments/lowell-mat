from abc import ABC, abstractmethod


class Meter(ABC):
    @abstractmethod
    def __init__(self, hs):
        pass  # pragma: no cover

    @abstractmethod
    def convert(self, raw_meter, temperature=None):
        pass  # pragma: no cover
