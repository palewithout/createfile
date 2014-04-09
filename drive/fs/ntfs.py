# encoding: utf-8
from construct import *
from drive.keys import *

NTFS = Struct(k_NTFS,
    Bytes(k_ignored, 1),
)

