# encoding: utf-8

from construct import *
from drive.keys import *
from misc import Skip

FAT32BootSector = Struct(k_FAT32BootSector,
    Bytes       (k_jump_instruction, 3),
    String      (k_OEM_name, 8),
    ULInt16     (k_bytes_per_sector),
    ULInt8      (k_sectors_per_cluster),
    ULInt16     (k_number_of_reserved_sectors),
    ULInt8      (k_number_of_FATs),
Skip(cons=[
    ULInt16,
    ULInt16
]),
    ULInt8      (k_media_descriptor),
Skip(cons=[
    ULInt16
]),
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
Skip(cons=[
    ULInt32,
    ULInt32,
    ULInt32,
]),
    ULInt8      (k_drive_number),
Skip(cons=[
    ULInt8
]),
    ULInt8      (k_extended_boot_signature),
    ULInt32     (k_volume_id),
    String      (k_volume_label, 11),
    String      (k_filesystem_type, 8),
    RepeatUntil(lambda obj, c: obj == '\x55\xaa',
                Field(k_ignored, 2)),
    Value(k_ignored, lambda _: '\x55\xaa'),

    allow_overwrite=True
)

FAT32FSInformationSector = Struct(k_ignored,
    Magic('\x52\x52\x61\x41'),
    Skip(length=0x1fa),
    Magic('\x55\xaa'),

    allow_overwrite=True
)

FAT32DirectoryTableEntry = Struct(k_FAT32DirectoryTableEntry,
    String(k_short_file_name, 8),
    String(k_short_extension, 3),
    ULInt8(k_attribute),
    Skip(2),
    ULInt16(k_create_time),
    ULInt16(k_create_date),
    ULInt16(k_access_date),
    ULInt16(k_higher_cluster),
    ULInt16(k_modify_time),
    ULInt16(k_modify_date),
    ULInt16(k_lower_cluster),
    ULInt32(k_file_length),
)

FAT32LongFilenameEntry = Struct(k_FAT32LongFilenameEntry,
    ULInt8(k_sequence_number),
    String(k_name_1, 10),
    Const(ULInt8(k_attribute), 0xf),
    ULInt8(k_type),
    ULInt8(k_checksum),
    String(k_name_2, 12),
    Const(ULInt16(k_first_cluster), 0x0),
    String(k_name_3, 4),
)
