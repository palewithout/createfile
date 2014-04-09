# encoding: utf-8
from attest import Tests
from drive.drive_ import Drive
from drive.keys import *
from stream import ImageStream

fat32 = Tests()


@fat32.context
def build_fs():
    with ImageStream('d:/edt.raw') as s:
        c = Drive.parse_stream(s)

        yield c['%s%s' % (k_Partition, 0)]


@fat32.test
def test_fat32(c):
    assert c[k_FAT32BootSector][k_filesystem_type] == 'FAT32   '



if __name__ == '__main__':
    fat32.main()