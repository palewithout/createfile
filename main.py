# encoding: utf-8
from drive.disk import get_drive_obj
from stream import *


if __name__ == '__main__':
    with ImageStream('d:/edt.raw') as f:
        partitions = get_drive_obj(f)
        partition0 = next(partitions)

        partition0.get_fdt()
