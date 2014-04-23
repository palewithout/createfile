# encoding: utf-8
from functools import reduce
import os

from construct import *
from datetime import datetime
from drive.keys import *
from misc import STATE_LFN_ENTRY, STATE_DOS_ENTRY, MAGIC_END_SECTION

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
                 'create_time', 'modify_time', 'skip']

    def __init__(self, raw, dir_name, state_mgr, current_obj, partition):
        obj = self.__struct__.parse(raw)

        self.skip = False

        self.is_directory = bool(obj[k_attribute] & 0x10)

        self.first_cluster = self._get_first_cluster(obj)
        self.cluster_list = partition.resolve_cluster_list(self.first_cluster)\
                            if not self.is_directory else ()

        try:
            name, ext = self._get_names(obj, state_mgr, current_obj)
            print(dir_name, name, self.first_cluster)
        except UnicodeDecodeError:
            partition.logger.warning('%s unicode decode error', dir_name)
            self.skip = True
            return

        self.full_path = os.path.join(dir_name, name)

        h, m, s = self._get_time(obj[k_create_time],
                                 obj[k_create_time_10ms])
        y, M, d = self._get_date(obj[k_create_date])
        try:
            self.create_time = datetime(y, M, d, h, m, int(s))
        except ValueError:
            partition.logger.warning('%s\\%s: invalid date %s, %s, %s',
                                     dir_name, name, y, M, d)
            self.skip = True
            return

        h, m, s = self._get_time(obj[k_modify_time], 0)
        y, M, d = self._get_date(obj[k_modify_date])
        try:
            self.modify_time = datetime(y, M, d, h, m, int(s))
        except ValueError:
            partition.logger.warning('%s\\%s: invalid date %s, %s, %s',
                                     dir_name, name, y, M, d)
            self.skip = True
            return

    def _get_names(self, obj, state_mgr, current_obj):
        ext = ''
        if state_mgr.is_(STATE_LFN_ENTRY):
            name = current_obj['name'][0]
            if not self.is_directory:
                ext = name.rsplit('.')[-1] if '.' in name else ''

            state_mgr.transit_to(STATE_DOS_ENTRY)
            current_obj['name'] = ''

        else:
            name = obj[k_short_file_name].strip()
            if b'\xe5' in name:
                name = '(deleted) ' + str(name[1:], encoding='ascii')
            else:
                name = str(name, encoding='ascii')

            if not self.is_directory:
                ext = str(obj[k_short_extension].strip(), encoding='ascii')
                name = '.'.join((name, ext)).strip('.')

        return name.strip().lower(), ext.strip().lower()

    @staticmethod
    def _get_checksum(obj):
        # TODO checksum checking is not yet implemented
        return reduce(lambda sum_, c: ((sum_ & 1) << 7 + sum_ >> 1 + ord(c))
                                      & 0xff,
                      '.'.join((obj[k_short_file_name],
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

    def __init__(self, raw, state_mgr, current_obj):
        obj = self.__struct__.parse(raw)

        seq_number = obj[k_sequence_number]
        if seq_number == 0xe5:
            # deleted entry
            state_mgr.transit_to(STATE_LFN_ENTRY)
        elif seq_number & 0x40:
            # first (logically last) LFN entry
            assert not state_mgr.is_(STATE_LFN_ENTRY)

            state_mgr.transit_to(STATE_LFN_ENTRY)
            current_obj['checksum'] = obj[k_checksum]
        else:
            # assert state_mgr.is_(STATE_LFN_ENTRY)
            # assert current_obj['checksum'] == obj[k_checksum]

            seq_number &= 0x1f
            if seq_number == 1:
                # LFN ends
                pass

        current_obj['name'] = self._get_entry_name(obj) + current_obj['name']

    @staticmethod
    def _get_entry_name(obj):
        try:
            return ''.join(map(lambda _: str(_.strip(b'\xff\x00'),
                                             encoding='utf-16'),
                               (obj[k_name_1],
                                obj[k_name_2],
                                obj[k_name_3])))
        except UnicodeDecodeError:
            print('Unicode decode error in _get_entry_name')
            return 'unicode decode error'
