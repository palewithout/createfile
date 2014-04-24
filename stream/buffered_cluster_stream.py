# encoding: utf-8
from io import BytesIO
from itertools import chain
import os
from stream.read_only_stream import ReadOnlyStream


class MethodNotSupportedError(BaseException):
    pass


class BufferedClusterStream(ReadOnlyStream):
    def __init__(self, origin_stream, cluster_list, abs_c2b):
        """
        abs_c2b: a function which calculates the absolute byte address of the
        cluster, usually given `self.abs_c2b' in FAT32
        """
        super(BufferedClusterStream, self).__init__()

        self._stream = origin_stream
        self.clusters = chain.from_iterable(map(lambda args: range(args[0],
                                                                   args[1] + 1),
                                                 cluster_list))
        self._abs_c2b = abs_c2b

        self._buffer = BytesIO()

    def _load_next_cluster(self):
        self._stream.seek(self._abs_c2b(next(self.clusters)), os.SEEK_SET)
        self._buffer = BytesIO(self._stream.read())

    def read(self, size=ReadOnlyStream.DEFAULT_READ_BUFFER_SIZE):
        buf = self._buffer.read(size)
        buf_len = len(buf)

        if buf_len < size:
            # current cluster finished, jump to next cluster
            self._load_next_cluster()
            buf += self._buffer.read(size - buf_len)

        return buf

    def close(self):
        self._buffer.close()

    def seek(self, pos, whence=os.SEEK_SET):
        raise MethodNotSupportedError('BufferedClusterStream does '
                                      'not support seek')

    def tell(self):
        raise MethodNotSupportedError('BufferedClusterStream does '
                                      'not support tell')
