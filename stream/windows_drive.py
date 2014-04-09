# encoding: utf-8
import os

from win32file import *
from stream.read_only_stream import ReadOnlyStream
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class WindowsPhysicalDriveStream(ReadOnlyStream):

    def __init__(self,
                 number,
                 default_buffer_size=ReadOnlyStream.DEFAULT_READ_BUFFER_SIZE):
        super(WindowsPhysicalDriveStream, self).__init__()

        self._dev = self._create_file(r'\\.\PhysicalDrive%s' % number)
        self._buffer = StringIO()

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

    def seek(self, pos, whence=os.SEEK_SET):
        return SetFilePointer(self._dev, pos, {os.SEEK_SET: FILE_BEGIN,
                                               os.SEEK_CUR: FILE_CURRENT,
                                               os.SEEK_END: FILE_END}[whence])

    def read(self, size=ReadOnlyStream.DEFAULT_READ_BUFFER_SIZE):
        buf = self._buffer.read(size)

        buf_len = len(buf)
        if buf_len < size:
            err, _win32_read_file_buf = ReadFile(self._dev,
                                                 self.default_buffer_size)
            if err:
                raise IOError('Error reading utilizing ReadFile')

            self._buffer = StringIO(_win32_read_file_buf)
            buf += self._buffer.read(size - buf_len)

        return buf

    def close(self):
        self._dev.close()

    def tell(self):
        return self.seek(0, os.SEEK_CUR)
