# encoding: utf-8
from drive.disk import get_drive_obj
from stream import *


class PhysicalDrive(object):

    DEFAULT_READ_BUFFER_SIZE = 1024 * 10

    def __init__(self, stream):
        self.stream = stream




if __name__ == '__main__':
    # drive = PhysicalDrive(WindowsPhysicalDriveStream(0))
    with ImageStream('d:/edt.raw') as f:
        partitions = get_drive_obj(f)
        partition0 = partitions.next()
        # print sorted(partitions.next().fat1.keys())
