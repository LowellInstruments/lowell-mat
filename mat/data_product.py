import numpy as np
from mat.output_stream import output_stream_factory
from abc import ABC, abstractmethod
from mat.utils import roll_pitch_yaw, apply_declination
from collections import namedtuple


# TODO does OUTPUT_TYPE get used anywhere?


SensorDataTime = namedtuple('SensorDataTime', ['data', 'time'])


def data_product_factory(file_path, sensors, parameters):
    """
    Instantiate a data product subclass and pass it the necessary sensors
    """
    special_cases = {'compass': Compass,
                     'current': Current,
                     'ypr': YawPitchRoll,
                     'cable': Cable}
    data_products = []
    output_stream = output_stream_factory(file_path, parameters)

    # special cases and accelmag are mutually exclusive, hence the if elif
    if parameters['output_type'] in special_cases.keys():
        klass = special_cases[parameters['output_type']]
        data_products.append(klass(sensors, parameters, output_stream))

    # Check if any sensors need bundling
    elif set(AccelMag.REQUIRED_SENSORS).issubset([s.name for s in sensors]):
        data_products.append(AccelMag(sensors, parameters, output_stream))

    elif set(DissolvedOxygen.REQUIRED_SENSORS).issubset(
            [s.name for s in sensors]):
        data_products.append(DissolvedOxygen(sensors,
                                             parameters,
                                             output_stream))

    # Convert remaining sensors as discrete channels
    remaining_sensors = _remaining_sensors(sensors, data_products)
    for sensor in remaining_sensors:
        data_products.append(DiscreteChannel(sensor,
                                             parameters,
                                             output_stream))
    return data_products


def _remaining_sensors(sensors, data_products):
    used_sensors = [s for p in data_products for s in p.REQUIRED_SENSORS]
    return [s for s in sensors if s.name not in used_sensors]


class DataProduct(ABC):
    OUTPUT_TYPE = ''
    REQUIRED_SENSORS = []

    def __init__(self, sensors, parameters, output_stream):
        self.sensors = self._get_required_sensors(sensors)
        self.parameters = parameters
        self.output_stream = output_stream
        self.average = parameters['average']
        self.split = parameters['split']
        self.declination = self.parameters['declination']
        self.configure_output_stream()

    def _get_required_sensors(self, sensors):
        sensor_names = [s.name for s in sensors]
        if not set(self.REQUIRED_SENSORS).issubset(sensor_names):
            raise ValueError('Not all required sensors present')
        return [s for s in sensors if s.name in self.REQUIRED_SENSORS]

    def configure_output_stream(self):
        name = self.stream_name()
        self.output_stream.add_stream(name)
        self.output_stream.set_data_format(name, self.data_format())
        self.output_stream.set_column_header(name, self.column_header())

    def convert_sensors(self, data_page, page_time):
        converted = []
        for sensor in self.sensors:
            data, time = sensor.convert(data_page, self.average, page_time)
            converted.append(SensorDataTime(data, time))
        return converted

    @abstractmethod
    def stream_name(self):
        pass  # pragma: no cover

    @abstractmethod
    def data_format(self):
        pass  # pragma: no cover

    @abstractmethod
    def column_header(self):
        pass  # pragma: no cover

    @abstractmethod
    def process_page(self, data_page, page_time):
        pass  # pragma: no cover


class DiscreteChannel(DataProduct):
    OUTPUT_TYPE = 'discrete'
    REQUIRED_SENSORS = []

    def __init__(self, sensor, parameters, output_stream):
        super().__init__([sensor], parameters, output_stream)

    def _get_required_sensors(self, sensors):
        return sensors

    def stream_name(self):
        return self.sensors[0].name

    def data_format(self):
        return self.sensors[0].sensor_spec.format

    def column_header(self):
        return self.sensors[0].sensor_spec.header

    def process_page(self, data_page, page_time):
        converted = self.convert_sensors(data_page, page_time)
        self.output_stream.write(self.sensors[0].name,
                                 converted[0].data,
                                 converted[0].time)


class Current(DataProduct):
    OUTPUT_TYPE = 'current'
    REQUIRED_SENSORS = ['Accelerometer', 'Magnetometer']

    def __init__(self, sensors, parameters, output_stream):
        super().__init__(sensors, parameters, output_stream)
        self.tilt_curve = self.parameters['tilt_curve']

    def stream_name(self):
        return 'Current'

    def data_format(self):
        return '{:0.2f},{:0.2f},{:0.2f},{:0.2f}'

    def column_header(self):
        return ('Speed (cm/s),'
                'Heading (degrees),'
                'Velocity-N (cm/s),'
                'Velocity-E (cm/s)')

    def _calc_tilt_and_heading(self, accel, mag):
        roll, pitch, yaw = roll_pitch_yaw(accel, mag)
        x = -np.cos(roll) * np.sin(pitch)
        y = np.sin(roll)

        tilt = np.arccos(
            accel[2] / np.sqrt(accel[0] ** 2 + accel[1] ** 2 + accel[2] ** 2))
        is_usd = tilt > np.pi / 2
        tilt[is_usd] = np.pi - tilt[is_usd]

        heading = np.arctan2(y, x) + yaw
        heading = np.mod(heading + np.deg2rad(self.declination), 2 * np.pi)
        return tilt, heading

    def process_page(self, data_page, page_time):
        converted = self.convert_sensors(data_page, page_time)
        accel = converted[0].data
        mag = converted[1].data
        tilt, heading = self._calc_tilt_and_heading(accel, mag)
        speed = self.tilt_curve.speed_from_tilt(np.degrees(tilt))

        velocity_n = speed * np.cos(heading)
        velocity_e = speed * np.sin(heading)

        data = np.vstack((speed, np.degrees(heading), velocity_n, velocity_e))

        self.output_stream.write(self.stream_name(), data, converted[0].time)


class Compass(DataProduct):
    OUTPUT_TYPE = 'compass'
    REQUIRED_SENSORS = ['Accelerometer', 'Magnetometer']

    def stream_name(self):
        return 'Heading'

    def data_format(self):
        return '{:0.2f}'

    def column_header(self):
        return 'Heading (degrees)'

    def process_page(self, data_page, page_time):
        converted = self.convert_sensors(data_page, page_time)
        accel = converted[0].data
        mag = converted[1].data
        m = np.array([[0, 0, 1], [0, -1, 0], [1, 0, 0]])
        accel = np.dot(m, accel)
        mag = np.dot(m, mag)
        roll, pitch, heading = roll_pitch_yaw(accel, mag)
        heading = apply_declination(np.degrees(heading), self.declination)
        heading = np.mod(heading, 360)
        heading = np.reshape(heading, (1, -1))
        self.output_stream.write(self.stream_name(),
                                 heading,
                                 converted[0].time)


class YawPitchRoll(DataProduct):
    OUTPUT_TYPE = 'ypr'
    REQUIRED_SENSORS = ['Accelerometer', 'Magnetometer']

    def stream_name(self):
        return 'YawPitchRoll'

    def data_format(self):
        return '{:0.2f},{:0.2f},{:0.2f}'

    def column_header(self):
        return 'Yaw (degrees),Pitch (degrees),Roll (degrees)'

    def process_page(self, data_page, page_time):
        converted = self.convert_sensors(data_page, page_time)
        accel = converted[0].data
        mag = converted[1].data
        roll, pitch, yaw = roll_pitch_yaw(accel, mag)
        yaw = apply_declination(np.degrees(yaw), self.declination)
        yaw = np.reshape(yaw, (1, -1))
        data = np.vstack((yaw, np.degrees(pitch), np.degrees(roll)))
        self.output_stream.write(self.stream_name(), data, converted[0].time)


class Cable(DataProduct):
    OUTPUT_TYPE = 'cable'
    REQUIRED_SENSORS = ['Accelerometer']

    def stream_name(self):
        return 'CableAttitude'

    def data_format(self):
        return '{:0.2f},{:0.2f}'

    def column_header(self):
        return 'Rotation From Level (degrees),Axial Rotation (degrees)'

    def process_page(self, data_page, page_time):
        converted = self.convert_sensors(data_page, page_time)
        accel = converted[0].data
        axial = np.arctan2(-accel[0, :], accel[1, :])
        pitch = np.arctan2(
            accel[2, :],
            -(accel[0, :] * np.sin(axial) - accel[1, :] * np.cos(axial))
        )
        data = np.vstack((np.degrees(pitch), np.degrees(axial)))
        self.output_stream.write(self.stream_name(), data, converted[0].time)


class CompoundProduct(DataProduct):
    """
    CompoundProducts present multiple sensors in the same output file.
    """

    def _join_spec_fields(self, field):
        fields = [getattr(x.sensor_spec, field) for x in self.sensors]
        return ','.join(fields)

    def process_page(self, data_page, page_time):
        converted = self.convert_sensors(data_page, page_time)
        shortest = min([np.size(x.data) for x in converted])
        data = np.vstack([x.data[:, :shortest] for x in converted])
        self.output_stream.write(self.stream_name(),
                                 data,
                                 converted[0].time[:shortest])

    def data_format(self):
        return self._join_spec_fields('format')

    def column_header(self):
        return self._join_spec_fields('header')


class DissolvedOxygen(CompoundProduct):
    OUTPUT_TYPE = 'dissolved_oxygen'
    REQUIRED_SENSORS = ['DissolvedOxygen',
                        'DissolvedOxygenPercentage',
                        'DissolvedOxygenTemperature']

    def stream_name(self):
        return 'DissolvedOxygen'


class AccelMag(CompoundProduct):
    OUTPUT_TYPE = 'accelmag'
    REQUIRED_SENSORS = ['Accelerometer', 'Magnetometer']

    def stream_name(self):
        return 'AccelMag'
