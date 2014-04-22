# encoding: utf-8
from drive.disk import get_drive_obj
from drive.fs.fat32 import FAT32
from stream import *


if __name__ == '__main__':
    with WindowsPhysicalDriveStream(2) as f:
        for partition in get_drive_obj(f):
            if partition:
                if partition.type == FAT32.type:
                    partition.get_fdt()
