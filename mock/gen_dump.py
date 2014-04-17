# encoding: utf-8
from drive.disk import get_drive_obj
from stream import ImageStream

if __name__ == '__main__':
    print('dumping')
    with ImageStream('d:/edt.raw') as f:
        partitions = get_drive_obj(f)
        partition0 = next(partitions)
        partition0.dump()
