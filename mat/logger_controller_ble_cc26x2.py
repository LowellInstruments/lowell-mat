import bluepy.btle as ble
import json
import time
from mat.logger_controller_ble import LoggerControllerBLE, Delegate


class LoggerControllerBLECC26X2(LoggerControllerBLE):

    def open(self):
        try:
            self.peripheral = ble.Peripheral()
            self.delegate = Delegate()
            self.peripheral.setDelegate(self.delegate)
            self.peripheral.connect(self.address)
            # set_mtu() needs some time
            # https://github.com/IanHarvey/bluepy/issues/325
            time.sleep(1)
            self.peripheral.setMTU(240)
            # project_zero DS_STREAM characteristic notification
            uuid_service = 'f0001130-0451-4000-b000-000000000000'
            uuid_char = 'f0001132-0451-4000-b000-000000000000'
            self.service = self.peripheral.getServiceByUUID(uuid_service)
            self.characteristic = self.service.getCharacteristics(uuid_char)[0]
            descriptor = self.characteristic.valHandle + 1
            self.peripheral.writeCharacteristic(descriptor, b'\x01\x00')
            # project_zero DS_STRING characteristic
            uuid_char = 'f0001131-0451-4000-b000-000000000000'
            self.characteristic = self.service.getCharacteristics(uuid_char)[0]
            return True
        except AttributeError:
            return False

    def ble_write(self, data, response=False):  # pragma: no cover
        # todo: study this length but it is better than byte by byte
        if len(data) < 200:
            self.characteristic.write(data, withResponse=response)

    def send_cfg(self, cfg_file_as_json_dict):  # pragma: no cover
        cfg_file_as_string = json.dumps(cfg_file_as_json_dict)
        return self.command("CFG", cfg_file_as_string, retries=1)

    def know_mtu(self):
        return self.peripheral.status()['mtu'][0]

