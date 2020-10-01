from mat.utils import four_byte_int


EXIT_MARKERS = ['##', '\xff\xff']


class LoggerInfoParser:
    def __init__(self, data):
        self.data = data
        self.start = 0

    def next(self, count):
        end = self.start + count
        result = self.data[self.start:end]
        self.start = end
        return result

    def info(self):
        try:
            return self._parse_data()
        except TypeError:
            return {'error': True}

    def _parse_data(self):
        results = {}
        while True:
            tag = self.next(2)
            if tag in EXIT_MARKERS:
                return results
            length = ord(self.next(1))
            results[tag] = _parse_by_tag(tag, self.next(length))


def _parse_by_tag(tag, data):
    if tag == 'CA':
        return four_byte_int(data, True) / 256.0
    elif tag == 'BA' or tag == 'DP':
        return four_byte_int(data)
    return data
