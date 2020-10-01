from numpy import array
from mat.utils import four_byte_int


LENGTH_TO_COUNT = {
    32: 8,
    40: 10,
}

RAW_SENSOR_NAMES = [
    'temp_raw',
    'ax_raw',
    'ay_raw',
    'az_raw',
    'mx_raw',
    'my_raw',
    'mz_raw',
    'batt',
    'pressure_raw',
    'light_raw',
]

REFINEMENTS = {
    'batt': lambda x: float(x) / 1000,
    'temp_raw': lambda x: x or 1,
}

# Convertername, target channels, include temperature
SENSOR_CONVERTERS = [
    ('accelerometer', ('ax', 'ay', 'az'), True),
    ('magnetometer', ('mx', 'my', 'mz'), True),
    ('light', ('light',), False),
    ('pressure', ('pressure',), False),
]


class SensorParser:
    def __init__(self, data, converter):
        if data is None:
            raise RuntimeError("No sensor data provided")
        self.data = data
        self.converter = converter
        self._sensors = {
            'light_raw': 0,
            'light': 0,
            'pressure_raw': 0,
            'pressure': 0,
        }

    def sensors(self):
        count = self.sensor_count()
        if count is None:
            return None
        self.add_raw_sensors(count)
        self.add_converted_sensors(count)
        return self._sensors

    def sensor_count(self):
        return LENGTH_TO_COUNT.get(len(self.data))

    def add_raw_sensors(self, count):
        for i in range(count):
            name = RAW_SENSOR_NAMES[i]
            self._sensors[name] = self._sensor_value(i, name)

    def _sensor_value(self, index, name):
        start = index * 4
        value = four_byte_int(self.data[start:start + 4],
                              index not in [0, 8])
        if name in REFINEMENTS:
            value = REFINEMENTS[name](value)
        return value

    def add_converted_sensors(self, count):
        temp = self.converter.temperature(self._sensors['temp_raw'])
        self._sensors['temp'] = temp

        for convert_method, targets, temp_comp in SENSOR_CONVERTERS:
            sources = [target + "_raw" for target in targets]
            input = array([[self._sensors[source]] for source in sources])
            input = [input, array([temp])] if temp_comp else [input]
            if any([source in RAW_SENSOR_NAMES[:count]
                    for source in sources]):
                self.convert(convert_method, input, targets)

    def convert(self, convert_method, input, targets):
        result = getattr(self.converter, convert_method)(*input)
        for i, target in enumerate(targets):
            self._sensors[target] = result[i]
