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
            raise IOError('Error reading disk when utilizing ReadFile.')

        return _buf

    def seek(self, pos, whence=os.SEEK_SET):
        if whence == os.SEEK_SET:
            last_sector_pos = (pos // self.BYTES_PER_SECTOR
                               * self.BYTES_PER_SECTOR)
            self._set_file_pointer(last_sector_pos, whence)
            self._buffer = BytesIO(self._read_file())
            self._buffer.seek(pos - last_sector_pos, os.SEEK_CUR)

        elif whence == os.SEEK_CUR:
            if pos >= 0:
                # it's a bit complicated, and here's how this works
                # suppose we want to seek +(2 * buf_size + 500) relatively and
                # we have the following buffer now:
                # |-----^----------|
                #       |
                #       +- self._buffer.tell()
                # what we'd better do is add 500 and pointer of self._buffer
                # together, thus the actual offset will be
                # pos = +(2 * buf_size + 500 + self._buffer.tell()) relative to
                # the start of the buffer, like this
                # |---------^------|
                #           |
                #           +- pos % buf_size
                # and then we move the pointer forwards for 2 buffers, i.e.
                # |----------------|----------------|---------^------|
                #                                   |         |      |
                #                                   |         +- pos |
                #                                   |<-self._buffer->|
                # to achieve this, calculate how many buffers we should skip by
                # times = pos // buf_size - 1,
                # inter_buffer_offset = times * buf_size,
                # then use self._set_file_pointer to set fp
                # note that it's also possible to support negative offset, but
                # the case is so rare that I think it's a waste of time
                buffer_size = ReadOnlyStream.DEFAULT_READ_BUFFER_SIZE

                pos += self._buffer.tell()
                inter_buffer_offset = (pos // buffer_size - 1) * buffer_size
                intra_buffer_offset = pos % buffer_size

                self._set_file_pointer(inter_buffer_offset, FILE_CURRENT)
                self._buffer = BytesIO(self._read_file())
                self._buffer.seek(intra_buffer_offset, os.SEEK_CUR)
            else:
                raise ValueError('Negative offset not supported.')

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
