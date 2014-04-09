# encoding: utf-8
from attest import Tests
from stream import ImageStream
from drive.keys import *
from drive.mbr import ClassicalMBR


mbr = Tests()

@mbr.context
def instantiate_stream():
    stream = ImageStream('d:/edt.raw')
    c = ClassicalMBR.parse_stream(stream)

    yield c

    stream.close()

@mbr.test
def test_mbr(c):
    assert '\x33\xc0\x8e\xd0\xbc' in c[k_bootstrap_code]


@mbr.test
def test_partition_entry(c):
    partition_entry_0 = c[k_PartitionEntries][0]
    assert partition_entry_0[k_status] == 0x80
    assert partition_entry_0[k_starting_chs_address] == (0, 1, 1)
    assert partition_entry_0[k_partition_type] == k_FAT32
    assert partition_entry_0[k_ending_chs_address] == (652, 254, 63)
    assert partition_entry_0[k_first_sector_address] == 63
    assert partition_entry_0[k_first_byte_address] == 63 * 512
    assert partition_entry_0[k_number_of_sectors] == 10490382


if __name__ == '__main__':
    mbr.run()
