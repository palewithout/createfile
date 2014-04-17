# encoding: utf-8
import os

from stream.read_only_stream import ReadOnlyStream


class ImageStream(ReadOnlyStream):

    def __init__(self, img_path):
        super(ImageStream, self).__init__()

        self.img_path = img_path
        self.img = open(img_path, 'rb')

    def read(self, size=ReadOnlyStream.DEFAULT_READ_BUFFER_SIZE):
        return self.img.read(size)

    def seek(self, pos, whence=os.SEEK_SET):
        self.img.seek(pos, whence)

    def close(self):
        self.img.close()

    def tell(self):
        return self.img.tell()
