from mat.logger_controller_ble import (
    LoggerControllerBLE,
    XModemException,
    LogCtrlBLEException
)
import bluepy.btle as btle
import time
import logging
import datetime
import os


# enable more verbose logging of errors to console
logging.basicConfig()
# minimum num. of seconds between consecutive connects
CONNECTION_INTERVAL = 10
# enable file dumping upon connection
DUMPING = True


# MAC_FILTER python list, minor case letters, needs an empty [] case
MAC_FILTER = []
MAC_FILTER = ['00:1e:c0:3d:7a:cb', 'e1:e4:04:40:43:35']
MAC_FILTER = ['00:1e:c0:3d:7a:cb']


# loop
if __name__ == "__main__":
    scanner = btle.Scanner()
    past_connections = {}
    count = 0

    while True:
        # keep-alive indicator
        print(count),
        count = count + 1

        # filter list of advertisers for only MAT1W
        scan_list = scanner.scan(3.0)
        scan_list = [device for device in scan_list if device.addr in MAC_FILTER]

        # now, build list of required connections (devices not queried recently)
        need_connections = {}
        for dev in scan_list:

            # time() returns epoch time in seconds
            now = time.time()

            # add any new device detected (not on the list)
            if dev.addr not in past_connections:
                past_connections[dev.addr] = now
                need_connections[dev.addr] = now
            else:
                # if already on the list, add if not seen for a long time
                if now - past_connections.get(dev.addr) > CONNECTION_INTERVAL:
                    past_connections[dev.addr] = now
                    need_connections[dev.addr] = now

        # so, here we have a list of filtered MACs which require connection
        for mac in need_connections.keys():
            # actual BLE connection
            my_ble_logger = LoggerControllerBLE(mac)

            # start sending commands to BLE peripheral
            try:
                # get logger status after unknown but required delay in msp430
                time.sleep(1)
                answer = my_ble_logger.command("STS")
                print('BLE Logger Status: {}'.format(answer))

                # stop logger measurement for RF reliability, leave time to write SD
                answer = my_ble_logger.command("STP")
                time.sleep(2)
                print('BLE Logger Stopped: {}'.format(answer))

                # set BLE RN4020 latency to minimum, wait it to be effective
                answer = my_ble_logger.control_command('T,0006,0000,0064')
                time.sleep(2)
                print('BLE Logger data speed-up: {}'.format(answer))

                # logger clock check
                now = datetime.datetime.now()
                clocks = None
                try:
                    answer = my_ble_logger.command("GTM")
                    clocks = datetime.datetime.strptime(answer[6:], '%Y/%m/%d %H:%M:%S')
                    print('BLE Logger Time: current clock is {}'.format(clocks))
                except ValueError:
                    print('BLE Logger Time: invalid value returned.')
                else:
                    # sync clock if more than 1 minute off compared to local machine
                    if abs(now - clocks).total_seconds() > 60:
                        answer = my_ble_logger.command("STM", now.strftime('%Y/%m/%d %H:%M:%S'))
                        print('BLE Logger Time: synced to local.'.format(answer))

                # get a list of tuples (files) on the ODLW, problems if > 55 files
                files = my_ble_logger.list_files()
                print(files)

                # this flag allows skipping file dumping step easily for faster testing
                if DUMPING:

                    # create a folder with logger's unique mac address as name
                    folder = mac.replace(':', '-').lower()
                    if not os.path.exists(folder):
                        os.makedirs(folder)
                    '''
                    # ".lid" files processing stage
                    for name, size in files:
                        if not name.endswith('.lid'):
                            continue
    
                        # check if ".lid" file exists locally and get its size
                        file_path = os.path.join(folder, name)
                        local_size = None
                        if os.path.isfile(file_path):
                            local_size = os.path.getsize(file_path)
    
                        # if sizes differ, download it
                        if not local_size or local_size != size:
                            with open(file_path, 'wb') as outstream:
                                print('Downloading ' + name)
                                started = time.time()
                                my_ble_logger.get_file(name, size, outstream)
                                ended = time.time()
                                m = '{} downloaded: ({} B, {:0.2f} B/sec.)'
                                print(m.format(name, size, size / ended - started))

                    '''
                    # ".lis" files processing stage
                    for name, size in files:
                        if not name.endswith('.lis'):
                            continue
                        if size <= 1024:
                            continue

                        # check if current ".lis" file exists locally and its size
                        file_path = os.path.join(folder, name)
                        local_size = None
                        if os.path.isfile(file_path):
                            local_size = os.path.getsize(file_path)

                        # download it if we do not have it locally or size does not match
                        if not local_size or local_size != size:
                            print("BLE Logger File: trying to download {}, size {}.". format(name, size))
                            with open(file_path, 'wb') as outstream:
                                started = time.time()
                                my_ble_logger.get_file(name, size, outstream)
                                ended = time.time()
                                m = "BLE Logger File: {} downloaded ({} B, {:0.2f} B/sec.)"
                                print(m.format(name, size, size / ended - started))

                # done downloading, give time to write header of new data file
                answer = my_ble_logger.command("RUN")
                time.sleep(2)
                print("BLE Logger Restarted: {}".format(answer))

                # timestamp last interaction with this device and disconnect
                past_connections[mac] = time.time()
                answer = my_ble_logger.disconnect()
                print("BLE Logger Disconnected.")

            except btle.BTLEException as error:
                print(str(error))
            except XModemException as error:
                print(str(error))
            except LogCtrlBLEException as error:
                print(str(error))
