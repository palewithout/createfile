# encoding: utf-8

from drive.fs.fat32 import get_fat32_obj
from drive.keys import *
from drive.mbr import ClassicalMBR
from stream import ImageStream


def get_ntfs_obj(entry, stream):
    pass


def get_extended_partition_obj(entry, stream):
    pass


def get_drive_obj(stream):
    mbr = ClassicalMBR.parse_stream(stream)

    def get_partition_obj(partition_entry, stream):
        partition_generator = {
            k_FAT32: get_fat32_obj,
            k_NTFS:  get_ntfs_obj,
            k_ExtendedPartition: get_extended_partition_obj,
            k_ignored: lambda _, __: None
        }[partition_entry[k_partition_type]]

        return partition_generator(partition_entry, stream)

    partitions = (get_partition_obj(entry, stream)
                  for entry in mbr[k_PartitionEntries])

    return partitions


if __name__ == '__main__':
    with ImageStream('d:/edt.raw') as f:
        partitions = get_drive_obj(f)
