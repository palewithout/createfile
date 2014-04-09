# encoding: utf-8
import os
from struct import unpack
from drive.fs.fat32.structs import *
from misc import time_it

__all__ = ['get_fat32_obj']



class FAT32(object):

    _ul_int32 = ULInt32(None)

    def __init__(self, stream, preceding_bytes, read_fat2=False):
        self.stream = stream

        self.boot_sector = FAT32BootSector.parse_stream(stream)
        self.bytes_per_sector = self.boot_sector[k_bytes_per_sector]
        assert self.bytes_per_sector == 512

        FAT32FSInformationSector.parse_stream(stream)

        fat_abs_pos = self.s2b(self.boot_sector[k_number_of_reserved_sectors])
        fat_abs_pos += preceding_bytes
        stream.seek(fat_abs_pos, os.SEEK_SET)

        self.fat1 = self.get_fat()
        if not read_fat2:
            self._jump(self.size_of_fat())
            self.fat2 = self.fat1
        else:
            self.fat2 = self.get_fat()

        self.fdt = self.get_fdt()

    def _jump(self, size):
        self.stream.seek(size, os.SEEK_CUR)

    def s2b(self, n):
        """sector to byte"""
        return self.bytes_per_sector * n

    def size_of_fat(self):
        return self.s2b(self.boot_sector[k_sectors_per_FAT])

    def _next_ul_int32(self):
        return unpack('<I', self.stream.read(4))[0]

    _eoc_magic = 0x0ffffff8
    def _is_eoc(self, n):
        return n & self._eoc_magic == self._eoc_magic

    @time_it
    def get_fat(self):
        _1 = self._next_ul_int32()
        _2 = self._next_ul_int32()
        assert _1 == self._eoc_magic
        assert _2 == 0xffffffff

        number_of_fat_items = self.size_of_fat() / 4 - 2
        counter = 0

        cluster_lists = {}
        cur_cluster_list = []

        percentage_done = 0.

        def update_percentage():
            percentage_done = float(counter) / number_of_fat_items * 100
            print '\r%0.2f%% done.' % percentage_done,

        def pop_cluster_list():
            cluster_lists[cur_cluster_list[0]] = cur_cluster_list[:]
            cur_cluster_list[:] = []

        while counter < number_of_fat_items:
            _ = self._next_ul_int32()
            cur_cluster_list.append(_)
            counter += 1

            if self._is_eoc(_):
                pop_cluster_list()

            if counter % 1000 == 0:
                update_percentage()

        # it's not clear whether the last cluster list be popped, which
        # does not ends with EOC
        pop_cluster_list()

        update_percentage()
        print
        print len(cluster_lists), 'cluster lists found'

        return cluster_lists

    def get_fdt(self):
        files = {}
        while True:
            entry = FAT32DirectoryTableEntry.parse_stream(self.stream)
            if entry[k_short_file_name] == '\x00' * 8:
                break

            attribute = entry[k_attribute]
            if attribute == 0xf:
                # LFN entry
                pass
            elif attribute & 0x10:
                # directory
                pass
            else:
                # regular 8.3 entry
                pass



def get_fat32_obj(entry, stream):
    first_byte_addr = entry[k_first_byte_address]

    stream.seek(first_byte_addr, os.SEEK_SET)

    return FAT32(stream, preceding_bytes=first_byte_addr)
