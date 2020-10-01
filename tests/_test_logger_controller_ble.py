class FakeCharacteristic:
    def __init__(self, index=0):
        self.valHandle = index

    def write(self, data, withResponse=False):
        pass


class FakeCharacteristicIndexable:
    def __getitem__(self, index):
        return FakeCharacteristic(index)


class FakeService:
    def getCharacteristics(self, which_char):
        return FakeCharacteristicIndexable()


class FakePeripheral:
    def __init__(self, mac, iface=0, timeout=10):
        self.mac = mac

    def setDelegate(self, delegate_to_fxn):
        pass

    def writeCharacteristic(self, where, value):
        pass

    def disconnect(self):
        pass

    def status(self):
        return {'mtu': (247,)}

    def setMTU(self, value):
        pass

    def getServiceByUUID(self, uuid):
        return FakeService()

    def waitForNotifications(self, timeout):
        return False


class FakePeripheralEx(FakePeripheral):
    def writeCharacteristic(self, where, value):
        import bluepy.btle as b
        raise b.BTLEException('ex')
