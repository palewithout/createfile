# encoding: utf-8
from collections import defaultdict
import logging
from struct import unpack
from drive.fs import Partition
from drive.fs.fat32.structs import *
from misc import time_it, SimpleCounter, StateManager, STATE_START
from mock.fat32 import memory_dump
from stream import ImageStream

__all__ = ['get_fat32_obj']


class FAT32(Partition):

    type = 'FAT32'

    _ul_int32 = ULInt32(None)

    __DEBUG_ATTR__ = ['logger', 'boot_sector', 'fat2', 'stream']

    def __getstate__(self):
        if not isinstance(self.stream, ImageStream):
            raise TypeError('incompatible stream type')
        d = dict(self.__dict__)
        for attr in self.__DEBUG_ATTR__:
            del d[attr]

        d['stream_path'] = self.stream.img_path
        d['last_pos'] = self.stream.tell()
        return d

    def __setstate__(self, d):
        self.stream = ImageStream(d['stream_path'])
        self.stream.seek(d['last_pos'])
        del d['stream_path']
        del d['last_pos']

        self.__dict__.update(d)

        self.setup_logger()

    def __init__(self, stream, preceding_bytes, read_fat2=False):
        super(FAT32, self).__init__(FAT32.type)

        self.logger = None
        self.setup_logger()

        self.stream = stream

        self.logger.info('reading boot sector')
        self.boot_sector = FAT32BootSector.parse_stream(stream)

        self.bytes_per_sector = self.boot_sector[k_bytes_per_sector]
        self.bytes_per_cluster = self.bytes_per_sector *\
                                 self.boot_sector[k_sectors_per_cluster]
        self.logger.info('read boot sector, bytes per sector is %d, '
                         'bytes per cluster is %d',
                         self.bytes_per_sector, self.bytes_per_cluster)
        # assert self.bytes_per_sector == 512

        self.bytes_per_fat = self.s2b(self.boot_sector[k_sectors_per_FAT])

        self.logger.info('reading fs info sector')
        FAT32FSInformationSector.parse_stream(stream)

        fat_abs_pos = self.s2b(self.boot_sector[k_number_of_reserved_sectors])
        fat_abs_pos += preceding_bytes
        stream.seek(fat_abs_pos, os.SEEK_SET)
        self.logger.info('stream jumped to %d and ready to read FAT',
                         fat_abs_pos)

        self.logger.info('reading FAT')
        res1 = self.fat1, self.number_of_eoc_1 = self.get_fat()
        self.logger.info('read FAT, size of FAT is %d, number of EOCs is %d',
                         self.bytes_per_fat, self.number_of_eoc_1)
        if not read_fat2:
            self._jump(self.bytes_per_fat)
            self.fat2, self.number_of_eoc_2 = res1
        else:
            self.fat2, self.number_of_eoc_2 = self.get_fat()

        self.data_section_offset = fat_abs_pos + 2 * self.bytes_per_fat

        self.fdt = {}

    @memory_dump
    def dump(self):
        yield self

    def setup_logger(self):
        self.logger = logging.getLogger('fat32')
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s: %(message)s'
        ))
        self.logger.addHandler(handler)

    def read_fdt(self):
        self.logger.info('reading FDT')
        self.fdt = self.get_fdt()

    def _jump(self, size):
        self.stream.seek(size, os.SEEK_CUR)

    def s2b(self, n):
        """sector to byte"""
        return self.bytes_per_sector * n

    def c2b(self, n):
        """cluster to byte"""
        return self.bytes_per_cluster * n

    def _next_ul_int32(self):
        return unpack('<I', self.stream.read(4))[0]

    _eoc_magic = 0x0ffffff8
    def _is_eoc(self, n):
        return n & self._eoc_magic == self._eoc_magic

    @time_it
    def get_fat(self):
        """
        get file allocation table from current stream position,
        returns the table represented in dict and number of EOCs
        """
        _1 = self._next_ul_int32()
        _2 = self._next_ul_int32()
        assert _1 == self._eoc_magic
        assert _2 == 0xffffffff

        number_of_fat_items = self.bytes_per_fat // 4

        number_of_eoc = SimpleCounter()

        def _(x, i):
            if self._is_eoc(x):
                number_of_eoc.inc()

            if i % 1000 == 0 or i == number_of_fat_items - 1:
                print('\r%0.2f%% done. %d EOC(s) found' % (
                    i * 1. / number_of_fat_items * 100,
                    int(number_of_eoc)
                ), end='')
            return x

        cluster_head = {}
        obj = defaultdict(list)

        def _operate(i):
            c = self._next_ul_int32()
            _(c, i)

            head = cluster_head.pop(i, i)

            if self._is_eoc(c):
                return

            cluster_list = obj[head]
            if not cluster_list:
                cluster_list.append([c, c])
            else:
                last_segment = cluster_list[-1]
                if last_segment[-1] == c - 1:
                    last_segment[-1] = c
                else:
                    cluster_list.append([c, c])

            cluster_head[c] = head

        [_operate(i) for i in range(2, number_of_fat_items)]

        print()
        print(len(cluster_head))

        return obj, number_of_eoc

    def get_fdt(self, root_dir_name='/', abs_start_pos=0):
        # task := (directory_name, fdt_abs_start_byte_pos)
        __tasks__ = [(root_dir_name,
                      abs_start_pos or self.data_section_offset)]

        files = {}

        while __tasks__:
            dir_name, pos = __tasks__.pop(0)
            if dir_name.startswith(u'\u00e5'):
                continue
            self.stream.seek(pos, os.SEEK_SET)

            files.update(self._discover(__tasks__, dir_name))

        return files

    def resolve_cluster_list(self, first_cluster, fat=None):
        fat = fat or self.fat1

        if first_cluster in fat:
            return fat[first_cluster]
        else:
            return ()

    def _discover(self, tasks, dir_name):
        if '\u00e5' in dir_name:
            return {}
        elif 'system volume information' in dir_name:
            return {}

        __blank__ = b'\x00' * 8

        __state__ = StateManager(STATE_START)
        __cur_obj__ = {'name': '', 'checksum': 0}

        files = {}

        while True:
            raw = self.stream.read(32)
            if len(raw) < 32:
                break
            elif raw.startswith(__blank__):
                break

            attribute = raw[0xb]
            if attribute == 0xf:
                FAT32LongFilenameEntry(raw,
                                       __state__,
                                       __cur_obj__)
            else:
                entry = FAT32DirectoryTableEntry(raw, dir_name,
                                                 __state__,
                                                 __cur_obj__,
                                                 self)
                if entry.skip:
                    continue

                if entry.is_directory:
                    # append new directory task to tasks
                    tasks.append((entry.full_path,
                                  self.c2b(entry.first_cluster) +\
                                  self.data_section_offset))
                else:
                    # regular 8.3 entry
                    files[entry.full_path] = entry

        return files



def get_fat32_obj(entry, stream):
    first_byte_addr = entry[k_first_byte_address]

    stream.seek(first_byte_addr, os.SEEK_SET)

    return FAT32(stream, preceding_bytes=first_byte_addr)
