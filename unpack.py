#! python3 -W ignore
# coding=utf-8
import zipfile
from __init__ import *

path = 'build/exe.win-amd64-3.6/build.zip'
with zipfile.ZipFile(path) as myzip:
	myzip.extractall(my_directory.as_posix())
create_shortcut(name='BI_Entry', exe_path=my_directory / 'bin' / 'exe.win-amd64-3.6' / 'bi_entry.exe', startin=my_directory / 'bin' / 'exe.win-amd64-3.6',
                icon_path=my_directory / 'bin' / 'exe.win-amd64-3.6' / 'bi_entry.ico')