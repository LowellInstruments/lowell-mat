from os import path
from .time_converter import create_time_converter
from pathlib import Path
import h5py
from datetime import datetime


def output_stream_factory(file_path, parameters):
    output_types = {'csv': CsvStream, 'hdf5': HDF5Stream}
    stream_class = output_types.get(parameters['output_format'])
    if stream_class is None:
        raise ValueError('Unknown output type' + parameters['output_format'])
    return stream_class(file_path, parameters)


class OutputStream:
    def __init__(self, file_path, parameters):
        self.file_path = file_path
        self.parameters = parameters
        self.streams = {}
        self.time_converter = create_time_converter(parameters['time_format'])

    def add_stream(self, data_product):
        pass  # pragma: no cover

    def set_column_header(self, stream, column_header):
        column_header = self.time_converter.header_str() + ',' + column_header
        self.streams[stream].column_header = column_header

    def set_data_format(self, stream, data_format):
        self.streams[stream].data_format = data_format

    def write(self, stream, data, time):
        time = self.time_converter.convert(time)
        self.streams[stream].write(data, time)


class CsvStream(OutputStream):
    def add_stream(self, data_product):
        self.streams[data_product] = CsvFile(
            self.file_path, data_product, self.parameters
        )


class HDF5Stream(OutputStream):
    def __init__(self, file_path, parameters):
        super().__init__(file_path, parameters)
        self.hdf_file = None

    def file(self):
        if not self.hdf_file:
            self.create_hdf_file()
        return h5py.File(self.hdf_file, 'r+')

    def create_hdf_file(self):
        file_path = Path(self.file_path)
        if self.parameters['output_directory']:
            parent = Path(self.parameters['output_directory'])
        else:
            parent = file_path.parent
        hdf_path = (parent / file_path.stem).with_suffix('.hdf5')
        if hdf_path.exists() and not self.parameters['overwrite']:
            raise FileExistsError(str(file_path.name))
        with h5py.File(hdf_path, 'w') as file:
            file.attrs['Source File'] = file_path.name
            file.attrs['Conversion Date'] = datetime.now().isoformat()[:-7]
        self.hdf_file = hdf_path

    def add_stream(self, data_product):
        with self.file() as file:
            file.create_group(data_product)

    def set_column_header(self, stream, column_header):
        with self.file() as file:
            file[stream].create_dataset(
                'Time',
                (0, ),
                maxshape=(None, ),
                dtype='float64',
                # dtype='S23',
                compression='gzip',
                shuffle=True
            )
            file[stream]['Time'].attrs['Time format'] = \
                'Seconds since 1970-01-01T00:00:00'

            channels = column_header.split(',')
            file[stream].create_dataset(
                'Data',
                (0, len(channels)),
                maxshape=(None, len(channels)),
                compression='gzip',
                shuffle=True
            )
            file[stream]['Data'].attrs['Columns'] = column_header

    def write(self, stream, data, time):
        with self.file() as file:
            ds_data = file[stream]['Data']
            ds_time = file[stream]['Time']

            ds_shape = ds_data.shape
            new_length = ds_shape[0] + data.shape[1]

            ds_data.resize((new_length, ds_shape[1]))
            ds_time.resize((new_length, ))
            ds_data[ds_shape[0]:, :] = data.T
            # ds_time[ds_shape[0]:] = \
            #     np.string_(self.time_converter.convert(time))
            ds_time[ds_shape[0]:] = time

    def set_data_format(self, stream, data_format):
        # not required in hdf5
        pass


class CsvFile:
    def __init__(self, file_path, stream_name, parameters):
        self.file_path = file_path
        self.stream_name = stream_name
        self.parameters = parameters
        self.column_header = ''
        self.data_format = ''
        self.split = parameters['split'] or 100000
        self.write_count = 0
        self.output_file_name = ''
        self.output_path = ''

    def next_file_path(self):
        dir_name = path.dirname(self.file_path)
        destination = self.parameters['output_directory'] or dir_name
        if self.parameters['file_name']:
            file_prefix = self.parameters['file_name']
        else:
            file_prefix = path.basename(self.file_path).split('.')[0]
        file_num = self.write_count // self.split
        file_num_str = '_{}'.format(file_num) if self.split != 100000 else ''
        self.output_file_name = '{}_{}{}.csv'.format(file_prefix,
                                                     self.stream_name,
                                                     file_num_str)
        self.output_path = path.join(destination, self.output_file_name)

    def write(self, data, time):
        if self.write_count % self.split == 0:
            self.next_file_path()
            if path.exists(self.output_path) \
                    and not self.parameters['overwrite']:
                raise FileExistsError(self.output_file_name)
            self._write_header()

        data_format = '{},' + self.data_format + '\n'
        with open(self.output_path, 'a') as fid:
            for i in range(data.shape[1]):
                fid.write(data_format.format(time[i], *data[:, i]))
        self.write_count += 1

    def _write_header(self):
        with open(self.output_path, 'w') as fid:
            fid.write(self.column_header + '\n')
