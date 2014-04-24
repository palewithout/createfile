# encoding: utf-8
from drive.disk import get_drive_obj
from drive.fs.fat32 import FAT32
from stream import ImageStream, WindowsPhysicalDriveStream

stream = ImageStream('d:/edt.raw')
address, port = '127.0.0.1', 8000

partitions = []
for partition in get_drive_obj(stream):
    if partition:
        if partition.type == FAT32.type:
            partitions.append(partition)
