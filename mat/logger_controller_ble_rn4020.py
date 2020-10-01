class LoggerControllerBLERN4020:  # pragma: no cover

    def __init__(self, base):
        self.base = base
        self.UUID_S = '00035b03-58e6-07dd-021a-08123a000300'
        self.UUID_C = '00035b03-58e6-07dd-021a-08123a000301'

    def open_post(self):
        pass

    def ble_write(self, data, response=False):  # pragma: no cover
        b_data = [data[i:i + 1] for i in range(len(data))]
        for each in b_data:
            self.base.cha.write(each, withResponse=response)
