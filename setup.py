#! python3 -W ignore
# coding=utf-8

import os
import sys
import pathlib

from _distutils import *
from version import version

try:
	from __version__ import full_version
	dev_version = int(full_version.rsplit('.', 1)[1]) + 1
except ImportError:
	dev_version = 0


def write_version_file(base_dir, major: int, minor: int, micro: int, dev: int, release: bool):
	version_string = '%d.%d.%d.%d' % (major, minor, micro, dev)
	file = base_dir / '__version__.py'
	content = f"""# coding=utf-8
# THIS FILE IS GENERATED FROM BI_ENTRY SETUP.PY
# To compare versions robustly, use 'bi_entry.utils.BIEntryVersion'

short_version = '{major}.{minor}.{micro}'
full_version = '{major}.{minor}.{micro}.{dev}'
version = short_version
release = {release}

if not release:
	version = full_version

__all__ = ['version']
"""
	file.write_text(content)

"""In my opinion - it should be deployed to QSystem as a click once application just like BISync is.
Its installed from QSystem to create a local instance of it.
However BISync launches it from Qsystem, but since its already installed it'll run it off of the computer.
Whenever it is updated, updates are automatically installed.
Kind of like a hybrid network deployment"""

major, minor, micro = version.split('.')

FILE_NAME = sys.executable
DIR_NAME = os.path.dirname(sys.executable)

os.environ['TCL_LIBRARY'] = os.path.join(DIR_NAME, r'tcl\tcl8.6')
os.environ['TK_LIBRARY'] = os.path.join(DIR_NAME, r'tcl\tk8.6')
home = pathlib.WindowsPath.home()
main_dir = pathlib.WindowsPath.cwd()
dist_dir = pathlib.Path.cwd() / '_distutils'
# '''subprocess.run([r'C:\Program Files\7-Zip\7z', 'a', '-mx=9', '-ms=4g', '-mhe=on', '-mmt=2', r'-t7z', 'installer.7z', fr'{os.getcwd()}\build'])
# 		files = [r'C:\Program Files\7-Zip\7zSD.sfx', 'config.txt', 'installer.7z']
# 		with open('BIEntry_Installer.exe', mode='w+b') as f:
# 			for fn in files:
# 				with open(fn, mode='rb') as f2:
# 					buffer_ = f2.readline()
# 					while buffer_:
# 						f.write(buffer_)
# 						buffer_ = f2.readline()
# 		shutil.copy2('BIEntry_Installer.exe', str(main_dir / 'BIEntry_Installer.exe'))
# 		os.chdir(str(main_dir))
# 		subprocess.run([r'.\req\UPX\upx', '--ultra-brute', '--compress-icons=1', 'BIEntry_Installer.exe'])'''

write_version_file(main_dir, int(major), int(minor), int(micro), int(dev_version), False)
# compile_it()
src_file = build_source([main_dir / 'utils', main_dir / 'processes', main_dir / 'core', main_dir / 'config'], main_dir, f"{major}.{minor}.{micro}.{dev_version}")
build_installer(src_file, main_dir, dist_dir, f"{major}.{minor}.{micro}.{dev_version}")
