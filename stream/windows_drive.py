# encoding: utf-8
import os

from win32file import *
from stream.read_only_stream import ReadOnlyStream
from io import BytesIO


class WindowsPhysicalDriveStream(ReadOnlyStream):

    BYTES_PER_SECTOR = 512

    def __init__(self,
                 number,
                 default_buffer_size=ReadOnlyStream.DEFAULT_READ_BUFFER_SIZE):
        super(WindowsPhysicalDriveStream, self).__init__()

        self._dev = self._create_file(r'\\.\PhysicalDrive%s' % number)
        self._buffer = BytesIO()

        self.default_buffer_size = default_buffer_size

    @staticmethod
    def _create_file(path):
        return CreateFile(path,
                          GENERIC_READ,
                          FILE_SHARE_READ | FILE_SHARE_WRITE,
                          None,
                          OPEN_EXISTING,
                          FILE_ATTRIBUTE_NORMAL,
                          None)

    def _set_file_pointer(self, pos, whence):
        return SetFilePointer(self._dev, pos, whence)

    def _read_file(self, size=ReadOnlyStream.DEFAULT_READ_BUFFER_SIZE):
        err, _buf = ReadFile(self._dev, size)
        if err:
            raise IOError('Error reading disk when utilizing ReadFile')

        return _buf

    def seek(self, pos, whence=os.SEEK_SET):
        if whence != os.SEEK_SET:
            raise TypeError('Seek type not supported')
        whence = {os.SEEK_SET: FILE_BEGIN,
                  os.SEEK_CUR: FILE_CURRENT,
                  os.SEEK_END: FILE_END}[whence]

        last_sector_pos = pos // self.BYTES_PER_SECTOR * self.BYTES_PER_SECTOR

        self._set_file_pointer(last_sector_pos, whence)
        self._buffer = BytesIO(self._read_file())
        self._buffer.seek(pos - last_sector_pos, os.SEEK_CUR)

    def read(self, size=ReadOnlyStream.DEFAULT_READ_BUFFER_SIZE):
        buf = self._buffer.read(size)

        buf_len = len(buf)
        if buf_len < size:
            _win32_read_file_buf = self._read_file(self.default_buffer_size)
            self._buffer = BytesIO(_win32_read_file_buf)

            buf += self._buffer.read(size - buf_len)

        return buf

    def close(self):
        self._dev.close()

    def tell(self):
        return self._set_file_pointer(0, FILE_CURRENT)
