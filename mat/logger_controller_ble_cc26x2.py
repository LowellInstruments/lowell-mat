class LoggerControllerBLECC26X2:  # pragma: no cover

    def __init__(self, base):
        self.base = base
        self.UUID_S = 'f0001130-0451-4000-b000-000000000000'
        self.UUID_C = 'f0001132-0451-4000-b000-000000000000'
        self.UUID_W = 'f0001131-0451-4000-b000-000000000000'
        self.MTU_SIZE = 247

    def open_post(self):
        # notification size up to MTU_SIZE - 3B ATT header
        self.base.per.setMTU(self.MTU_SIZE)
        self.base.cha = self.base.svc.getCharacteristics(self.UUID_W)[0]

    def ble_write(self, data, response=False):
        if len(data) <= self.MTU_SIZE:
            self.base.cha.write(data, withResponse=response)

    def _know_mtu(self):
        return self.base.per.status()['mtu'][0]
