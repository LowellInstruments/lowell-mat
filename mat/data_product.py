from os import path
from mat.output_stream import output_stream_factory
import numpy as np


def data_product_factory(sensors, parameters):
    """
    Instantiate a data product subclass and pass it the necessary sensors
    """
    data_products = []

    # Special cases first
    for class_ in [Current, Compass]:
        if class_.OUTPUT_TYPE == parameters['output_type']:
            # there should be an exception of this fails
            required_sensors = _sensor_from_name(sensors,
                                                 class_.REQUIRED_SENSORS)
            sensors = remove_sensors(sensors, required_sensors)
            data_product = class_(required_sensors, parameters)

            data_products.append(data_product)
            break  # there can be only one special case

    try:
        required_sensors = _sensor_from_name(sensors,
                                             AccelMag.REQUIRED_SENSORS)
        sensors = remove_sensors(sensors, required_sensors)
        data_product = AccelMag(required_sensors, parameters)
        data_products.append(data_product)
    except ValueError:
        pass

    # Convert remaining sensors as discrete channels
    for sensor in sensors:
        data_product = DiscreteChannel(sensor, parameters)
        data_products.append(data_product)

    return data_products


def remove_sensors(sensors, sensors_to_remove):
    return [s for s in sensors if s not in sensors_to_remove]


def _sensor_from_name(sensors, names):
    requested_sensors = [s for s in sensors if s.name in names]
    if len(requested_sensors) < len(names):
        raise ValueError('Required sensor not in sensors')
    return requested_sensors

class DataProduct:
    OUTPUT_TYPE = ''
    REQUIRED_SENSORS = []

    def __init__(self, sensors, parameters):
        # TODO I think I can just pass in output_format instead of parameters
        self.sensors = sensors
        self.parameters = parameters
        filename = path.basename(parameters['path'])
        dir_name = path.dirname(parameters['path'])
        destination = parameters['output_directory'] or dir_name
        self.output_stream = output_stream_factory(parameters['output_format'],
                                                   filename,
                                                   destination)
        self.configure_output_stream()

    def configure_output_stream(self):
        pass  # pragma: no cover

    def process_page(self, data_page, page_time):
        pass  # pragma: no cover


class DiscreteChannel(DataProduct):
    OUTPUT_TYPE = 'discrete'
    REQUIRED_SENSORS = []

    def configure_output_stream(self):
        name = self.sensors.name
        self.output_stream.add_stream(name)
        self.output_stream.set_data_format(name, self.sensors.spec.format)
        self.output_stream.set_header_string(name, self.sensors.spec.header)
        self.output_stream.set_time_format(name,
                                           self.parameters['time_format'])
        self.output_stream.write_header(name)

    def process_page(self, data_page, page_time):
        raw_data = self.sensors.parse(data_page)
        data = self.sensors.apply_calibration(raw_data)
        time = page_time + self.sensors.sample_times()
        self.output_stream.write(self.sensors.name, time, data)


class AccelMag(DataProduct):
    OUTPUT_TYPE = 'discrete'
    REQUIRED_SENSORS = ['Accelerometer', 'Magnetometer']
    NAME = 'AccelMag'

    def configure_output_stream(self):
        self.output_stream.add_stream(self.NAME)
        data_format = (self.sensors[0].spec.format + ','
                       + self.sensors[1].spec.format)
        self.output_stream.set_data_format(self.NAME, data_format)
        header_string = (self.sensors[0].spec.header + ','
                         + self.sensors[1].spec.header)
        self.output_stream.set_header_string(self.NAME, header_string)
        self.output_stream.set_time_format(self.NAME,
                                           self.parameters['time_format'])
        self.output_stream.write_header(self.NAME)

    def process_page(self, data_page, page_time):
        data_matrix = None
        time = page_time + self.sensors[0].sample_times()
        for sensor in self.sensors:
            raw_data = sensor.parse(data_page)
            data = sensor.apply_calibration(raw_data)
            if data_matrix is None:
                data_matrix = data
            else:
                data_matrix = np.vstack((data_matrix, data))
        self.output_stream.write(self.NAME, time, data_matrix)


class Current(DataProduct):
    OUTPUT_TYPE = 'current'
    REQUIRED_SENSORS = ['Accelerometer', 'Magnetometer']

    def process_page(self, data_page, page_time):
        pass


class Compass(DataProduct):
    OUTPUT_TYPE = 'compass'
    REQUIRED_SENSORS = ['Accelerometer', 'Magnetometer']

    def process_page(self, data_page, page_time):
        pass
