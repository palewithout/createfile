# encoding: utf-8
from collections import defaultdict
from functools import reduce
import logging
import os
from struct import unpack
from construct import *
from datetime import datetime, timezone
from drive.fs import Partition
from drive.keys import *
from misc import STATE_LFN_ENTRY, STATE_DOS_ENTRY, MAGIC_END_SECTION, \
    clear_cur_obj, time_it, SimpleCounter, StateManager, STATE_START
from stream.buffered_cluster_stream import BufferedClusterStream

FAT32BootSector = Struct(k_FAT32BootSector,
    Bytes       (k_jump_instruction, 3),
    String      (k_OEM_name, 8),
    ULInt16     (k_bytes_per_sector),
    ULInt8      (k_sectors_per_cluster),
    ULInt16     (k_number_of_reserved_sectors),
    ULInt8      (k_number_of_FATs),
    ULInt16(None),
    ULInt16(None),
    ULInt8      (k_media_descriptor),
    ULInt16(None),
    ULInt16     (k_sectors_per_track),
    ULInt16     (k_number_of_heads),
    ULInt32     (k_number_of_hidden_sectors),
    ULInt32     (k_number_of_sectors),
    ULInt32     (k_sectors_per_FAT),
    UBInt16     (k_drive_description), # 2 bytes for mirror flags, so use UBInt16
                                       # to keep its raw form
    ULInt16     (k_version),
    ULInt32     (k_cluster_number_of_root_directory_start),
    ULInt16     (k_sector_number_of_FS_info_sector),
    ULInt16     (k_sector_number_of_boot_sectors_backup),
    ULInt32(None),
    ULInt32(None),
    ULInt32(None),
    ULInt8      (k_drive_number),
    ULInt8(None),
    ULInt8      (k_extended_boot_signature),
    ULInt32     (k_volume_id),
    String      (k_volume_label, 11),
    String      (k_filesystem_type, 8),
    RepeatUntil(lambda obj, c: obj == MAGIC_END_SECTION,
                Field(k_ignored, 2)),
    Value(k_ignored, lambda _: MAGIC_END_SECTION),

    allow_overwrite=True
)

FAT32FSInformationSector = Struct(k_ignored,
    Magic(b'\x52\x52\x61\x41'),
    String(None, 0x1fa),
    Magic(MAGIC_END_SECTION),

    allow_overwrite=True
)

class FAT32DirectoryTableEntry:

    """
    This class is a bit ugly due to the __slots__ mechanism, which, however, can
    improve the performance somehow.
    """

    __struct__ = Struct(k_FAT32DirectoryTableEntry,
                        String(k_short_file_name, 8),
                        String(k_short_extension, 3),
                        ULInt8(k_attribute),
                        ULInt8(None),
                        ULInt8(k_create_time_10ms),
                        ULInt16(k_create_time),
                        ULInt16(k_create_date),
                        ULInt16(k_access_date),
                        ULInt16(k_higher_cluster),
                        ULInt16(k_modify_time),
                        ULInt16(k_modify_date),
                        ULInt16(k_lower_cluster),
                        ULInt32(k_file_length))
    __slots__ = ['is_directory', 'cluster_list', 'full_path', 'first_cluster',
                 'create_time', 'create_timestamp',
                 'modify_time', 'modify_timestamp',
                 'skip', 'is_deleted']

    def __init__(self, raw, dir_name, state_mgr, current_obj, partition):
        obj = self.__struct__.parse(raw)

        self.skip = False
        self.is_deleted = b'\xe5' in obj[k_short_file_name]

        self.is_directory = bool(obj[k_attribute] & 0x10)

        self.first_cluster = self._get_first_cluster(obj)
        self.cluster_list = partition.resolve_cluster_list(self.first_cluster)\
                            if not self.is_directory else ()

        try:
            name, ext = self._get_names(obj, state_mgr, current_obj)
            print(dir_name, name, self.first_cluster)
            if name == '.' or name == '..':
                self.skip = True
                return
        except UnicodeDecodeError:
            partition.logger.warning('%s unicode decode error, '
                                     'first cluster: %s, '
                                     'byte address: %s',
                                     dir_name, hex(self.first_cluster),
                                     hex(partition.abs_c2b(self.first_cluster)))
            self.skip = True
            return

        self.full_path = os.path.join(dir_name, name)

        h, m, s = self._get_time(obj[k_create_time],
                                 obj[k_create_time_10ms])
        y, m_, d = self._get_date(obj[k_create_date])
        try:
            self.create_time = datetime(y, m_, d, h, m, int(s))
            self.create_timestamp = (self.create_time.
                                     replace(tzinfo=timezone.utc).
                                     timestamp()
                                     + s - int(s))
        except ValueError:
            partition.logger.warning('%s\\%s: invalid date %s, %s, %s',
                                     dir_name, name, y, m_, d)
            self.skip = True
            return

        h, m, s = self._get_time(obj[k_modify_time], 0)
        y, m_, d = self._get_date(obj[k_modify_date])
        try:
            self.modify_time = datetime(y, m_, d, h, m, int(s))
            self.modify_timestamp = (self.modify_time.
                                     replace(tzinfo=timezone.utc).
                                     timestamp())
        except ValueError:
            partition.logger.warning('%s\\%s: invalid date %s, %s, %s',
                                     dir_name, name, y, m_, d)
            self.skip = True
            return

    def _get_names(self, obj, state_mgr, current_obj):
        ext = ''
        if state_mgr.is_(STATE_LFN_ENTRY):
            name = current_obj['name']
            if not self.is_directory:
                ext = name.rsplit('.')[-1] if '.' in name else ''

            state_mgr.transit_to(STATE_DOS_ENTRY)
            current_obj['name'] = ''

        else:
            name = obj[k_short_file_name].strip()
            if self.is_deleted:
                name = '(deleted) ' + str(name[1:], encoding='ascii')
            else:
                name = str(name, encoding='ascii')

            if not self.is_directory:
                ext = str(obj[k_short_extension].strip(), encoding='ascii')
                name = '.'.join((name, ext)).strip('.')
            name = name.lower()
            ext = ext.lower()

        return name, ext

    @staticmethod
    def _get_checksum(obj):
        # TODO checksum checking is not yet implemented
        return reduce(lambda sum_, c: (0x80 if sum_ & 1 else 0 +
                                       (sum_ >> 1) +
                                       c) & 0xff,
                      b''.join((obj[k_short_file_name],
                                 obj[k_short_extension])),
                      0)

    @staticmethod
    def _get_time(word, byte):
        return ((word & 0xf800) >> 11,
                (word & 0x07e0) >> 5,
                (word & 0x001f) * 2 + byte * .01)

    @staticmethod
    def _get_date(word):
        return (((word & 0xfe00) >> 9) + 1980,
                (word & 0x01e0) >> 5,
                word & 0x001f)

    @staticmethod
    def _get_first_cluster(obj):
        return obj[k_higher_cluster] << 16 | obj[k_lower_cluster]



class FAT32LongFilenameEntry:

    __struct__ = Struct(k_FAT32LongFilenameEntry,
                        ULInt8(k_sequence_number),
                        String(k_name_1, 10),
                        ULInt8(None),
                        ULInt8(k_type),
                        ULInt8(k_checksum),
                        String(k_name_2, 12),
                        ULInt16(None),
                        String(k_name_3, 4))

    __slots__ = ['abort', 'is_deleted']

    def __init__(self, raw, state_mgr, current_obj, partition):
        obj = self.__struct__.parse(raw)

        self.abort = False
        self.is_deleted = False

        seq_number = obj[k_sequence_number]
        if seq_number == 0xe5:
            # deleted entry
            self.is_deleted = True
            state_mgr.transit_to(STATE_LFN_ENTRY)
        elif seq_number & 0x40:
            # first (logically last) LFN entry
            if state_mgr.is_(STATE_LFN_ENTRY):
                partition.logger.warning('detected overwritten LFN')
                clear_cur_obj(current_obj)

            state_mgr.transit_to(STATE_LFN_ENTRY)
            current_obj['checksum'] = obj[k_checksum]
        else:
            # assert state_mgr.is_(STATE_LFN_ENTRY)
            if not state_mgr.is_(STATE_LFN_ENTRY):
                partition.logger.warning('invalid LFN non-starting entry')

            if current_obj['checksum'] != obj[k_checksum]:
                # it's only possible that the checksum of the first entry and the
                # checksum of current_obj are not the same, the following entry
                # has to have the same checksum with the current_obj, there must
                # be something wrong here in this situation, so we choose to
                # abort immediately and consider this subdirectory corrupted
                self.abort = True
                return

            seq_number &= 0x1f
            if seq_number == 1:
                # LFN ends
                pass

        current_obj['name'] = self._get_entry_name(obj) + current_obj['name']

    @staticmethod
    def _get_entry_name(obj):
        try:
            return str(b''.join((obj[k_name_1],
                                 obj[k_name_2],
                                 obj[k_name_3])),
                       encoding='utf-16').split('\x00')[0]
        except UnicodeDecodeError:
            print('Unicode decode error in _get_entry_name')
            return 'unicode decode error'



class FAT32(Partition):

    type = 'FAT32'

    _ul_int32 = ULInt32(None)

    def __init__(self, stream, preceding_bytes,
                 read_fat2=False):
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
        _0 = self._next_ul_int32()
        _1 = self._next_ul_int32()
        assert _0 == self._eoc_magic
        assert _1 == 0xffffffff or _1 == 0xfffffff

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
            # _(c, i)

            head = cluster_head.pop(i, i)

            if self._is_eoc(c):
                if not obj[head]:
                    obj[head].append([head, head])

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

        return obj, number_of_eoc

    def get_fdt(self, root_dir_name='/'):
        # task := (directory_name, fdt_abs_start_byte_pos)
        __tasks__ = [(root_dir_name,
                      self.resolve_cluster_list(2))]

        files = {}
        directories = {}

        while __tasks__:
            dir_name, cluster_list = __tasks__.pop(0)

            directories[dir_name] = cluster_list

            if dir_name.startswith(u'\u00e5'):
                continue

            files.update(self._discover(__tasks__, dir_name, cluster_list))

        self.logger.info('found %s files and dirs in total', len(files) +
                                                             len(directories))

        return files, directories

    def resolve_cluster_list(self, first_cluster, fat=None):
        fat = fat or self.fat1

        if first_cluster in fat:
            # a bit ugly, may be refactored later
            clusters, pre_append = fat[first_cluster], []
            if first_cluster != clusters[0][0]:
                pre_append.append([first_cluster, first_cluster])
            return pre_append + clusters
        else:
            return ()

    def abs_c2b(self, cluster):
        return self.c2b(cluster - 2) + self.data_section_offset

    def _discover(self, tasks, dir_name, cluster_list):
        if 'System Volume Information' in dir_name:
            return {}

        __blank__ = b'\x00'

        __state__ = StateManager(STATE_START)
        __cur_obj__ = {'name': '', 'checksum': 0}

        files = {}

        with BufferedClusterStream(self.stream,
                                   cluster_list,
                                   self.abs_c2b) as stream:
            while True:
                try:
                    raw = stream.read(32)
                except StopIteration:
                    self.logger.warning('cluster list exhausted at %s',
                                        dir_name)
                    break

                if len(raw) < 32:
                    break
                elif raw.startswith(__blank__):
                    break

                attribute = raw[0xb]
                if attribute == 0xf:
                    entry = FAT32LongFilenameEntry(raw,
                                                   __state__,
                                                   __cur_obj__,
                                                   self)
                    if entry.abort:
                        break
                else:
                    entry = FAT32DirectoryTableEntry(raw, dir_name,
                                                     __state__,
                                                     __cur_obj__,
                                                     self)
                    if attribute == 0xb:
                        print('label: %s' % entry.full_path[1:])

                    if entry.skip or entry.is_deleted:
                        continue

                    if entry.is_directory:
                        # append new directory task to tasks
                        tasks.append((entry.full_path,
                                      self.fat1[entry.first_cluster]))
                    else:
                        # regular 8.3 entry
                        files[entry.full_path] = entry

        return files
