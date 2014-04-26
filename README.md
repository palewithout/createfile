
createfile
====

Deploy
----
Find `edenv.7z` in directory `bin` then extract it into anywhere you like.
Make sure you have Python3 installed. If not, go to
[Python.org](https://www.python.org/ ) and download the latest version of
Python *x64*.
Then read `README.md` in `edenv.7z`.


How to run
----
First activate the virtualenv we created earlier, using
`path/to/your/env/Scripts/activate.bat`.
Then under project root directory, run `python main.py`. You may want
to redirect the output to a text file, in this case, use
`python main.py > a.txt`.
Don't forget to modify the path to the disk image.


Making your own disk image
----
Install VirtualBox and use
`VBoxManage internalcommands converttoraw path/to/your/vdi.vdi output.raw`


Configuring the web interface
----
Modify the stream, address and port variable and use whatever value you like.


Cookbook
----
* To use a partition image:
```python
from stream.img_stream import ImageStream
from drive.fs.fat32 import get_fat32_partition

with ImageStream(path_to_partition_image) as stream:
    partition = get_fat32_partition(stream)
    file, dirs = partition.get_fdt()
```
* To use a disk image:
```python
from stream.img_stream import ImageStream
from drive.disk import get_drive_obj

with ImageStream(path_to_disk_image) as stream:
    for partition in get_drive_obj(f):
        if partition:
            if partition.type == FAT32.type:
                files, dirs = partition.get_fdt()
```

* To use a real disk: replace `from stream.img_stream import ImageStream` to
`from stream.windows_drive import WindowsPhysicalDriveStream` and also replace
the parameter of the `with` statement. Make sure the argument to
`WindowsPhyscialDriveStream` represent the hard disk you want to read.


Licensing
====

Licenced under GNU LGPLv3.

