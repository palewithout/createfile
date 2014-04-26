# encoding: utf-8
from drive.fs.fat32.structs import FAT32
from drive.keys import *
import os

__all__ = ['get_fat32_obj', 'get_fat32_partition']


def get_fat32_obj(entry, stream):
    first_byte_addr = entry[k_first_byte_address]

    stream.seek(first_byte_addr, os.SEEK_SET)

    return FAT32(stream, preceding_bytes=first_byte_addr)


def get_fat32_partition(stream):
    """use this function if you have partition image"""
    return FAT32(stream, preceding_bytes=0)
