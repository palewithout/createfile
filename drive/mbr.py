# encoding: utf-8

from construct import *
from drive.keys import *


def calc_chs_address(key):
    def _(context):
        h, s, c = context[key]

        head = h
        sector = 0b111111 & s
        cylinder = (0b11000000 & s) << 2 | c

        return cylinder, head, sector
    return _


PartitionEntry = Struct(k_PartitionEntry,
    # status is not needed so we don't parse this attribute
    Byte(k_status),

    # chs address is useful when locating certain partitions
    Array(3, ULInt8(k_starting_chs_address)),
    # parse them into a 3-tuple now
    Value(k_starting_chs_address,
          calc_chs_address(k_starting_chs_address)),

    Byte(k_partition_type),
    Value(k_partition_type, lambda c: {
        0x0: k_ignored,
        0xf: k_ExtendedPartition,
        0xb: k_FAT32,
        0xc: k_FAT32,
        0x7: k_NTFS,
    }[c[k_partition_type]]),

    Array(3, ULInt8(k_ending_chs_address)),
    Value(k_ending_chs_address,
          calc_chs_address(k_ending_chs_address)),

    ULInt32(k_first_sector_address),
    Value(k_first_byte_address,
          lambda c: c[k_first_sector_address] * 512),
    ULInt32(k_number_of_sectors),

    allow_overwrite=True
)

ClassicalMBR = Struct(k_MBR,
    # bootstrap code is not parsed for its less importance
    Bytes(k_bootstrap_code, 0x1be),

    # rename PartitionEntry to its plural form
    Rename(k_PartitionEntries, Array(4, PartitionEntry)),

    Magic(b'\x55\xaa')
)
