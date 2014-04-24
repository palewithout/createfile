# encoding: utf-8
import os


class ReadOnlyStream:

    DEFAULT_READ_BUFFER_SIZE = 1024 * 4

    def __init__(self):
        pass

    def read(self, size=DEFAULT_READ_BUFFER_SIZE):
        raise NotImplementedError

    def seek(self, pos, whence=os.SEEK_SET):
        raise NotImplementedError

    def tell(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def test(self):
        print(self.read(512).encode('hex'))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
