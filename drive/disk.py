# encoding: utf-8

from drive.fs.fat32 import get_fat32_obj
from drive.keys import *
from drive.mbr import ClassicalMBR
from stream import ImageStream


def get_NTFS_obj(stream):
    pass


def get_ExtendedPartition_obj(stream):
    pass


def get_drive_obj(stream):
    classical_MBR = ClassicalMBR.parse_stream(stream)

    def get_partition_obj(partition_entry, stream):
        partition_generator = {
            k_FAT32: get_fat32_obj,
            k_NTFS:  get_NTFS_obj,
            k_ExtendedPartition: get_ExtendedPartition_obj,
            k_ignored: lambda _: _
        }[partition_entry[k_partition_type]]

        return partition_generator(partition_entry, stream)

    partitions = (get_partition_obj(entry, stream)
                  for entry in classical_MBR[k_PartitionEntries])

    return partitions


if __name__ == '__main__':
    with ImageStream('d:/edt.raw') as f:
        partitions = get_drive_obj(f)
