
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


Licenced under GNU GPLv3.

