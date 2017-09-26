# from distutils.core import setup
from __init__ import __version__
import configparser
import sys
import os
import subprocess
from cx_Freeze import setup, Executable

os.chdir(os.getcwd() + '\\GitHub\\bi_entry')
config = configparser.ConfigParser()
config.read_file(open('config.ini'))

major, minor, micro = map(int, map(str.strip, __version__.split('.', 3)))
version = f"{major}.{minor}.{micro+1}"

print(os.getcwd())
def update_init(vers):
	from tempfile import mkstemp
	from shutil import move
	from os import fdopen, remove
	# Create temp file
	fh, abs_path = mkstemp()
	with fdopen(fh, 'w') as new_file:
		with open('__init__.py') as old_file:
			for line in old_file:
				if '=' in line:
					k, v = map(str.strip, line.split('=', 1))
					if k == '__version__':
						new_file.write(f"{k} = '{vers}'\n")
					else:
						new_file.write(line)
				else:
					new_file.write(line)
	# Remove original file
	remove('__init__.py')
	# Move new file
	move(abs_path, '__init__.py')


update_init(version)

FILE_NAME = sys.executable
DIR_NAME = os.path.dirname(sys.executable)

os.environ["TCL_LIBRARY"] = os.path.join(DIR_NAME, r"tcl\tcl8.6")
os.environ["TK_LIBRARY"] = os.path.join(DIR_NAME, r"tcl\tk8.6")

executables = [Executable(script="bi_entry.py", base="Win32GUI", targetName="bi_entry.exe", icon="bi_entry1.ico")]
# TODO: 2nd executable for compressing
# executables = [Executable(script="bi_entry.py", base="Console", targetName="bi_entry.exe", icon="bi_entry.ico")]
packages = ['psutil', 'win32api', 'pyautogui',
            'pymssql', 'pywinauto', 'win32gui',
            'easygui', '_mssql', 'uuid', 'subprocess',
            'comtypes', 'sqlite3']
include_files = [r'C:\Users\mfgpc00\AppData\Local\Programs\Python\Python36\DLLs\_ctypes.pyd',
                 r'C:\Users\mfgpc00\AppData\Local\Programs\Python\Python36\Lib\site-packages\_mssql.cp36-win_amd64.pyd']
excludes = ["tkinter", "PyQt4.QtSql", "numpy",
            "scipy.lib.lapack.flapack", "matplotlib",
            "PyQt4.QtNetwork", "PyQt4.QtScript",
            "numpy.core._dotblas", "PyQt5", "PIL",
            "colorama", "pygments", "mpl-data", "email"]

options = {
	'build_exe': {
		'packages': packages,
		'include_files': include_files,
		"excludes": excludes,
		"optimize": 2
		}
}
# TODO: Exclude files

setup(
	name='bi_entry',
	options=options,
	version=version,
	packages=[''],
	url='',
	license='',
	author='Josh Reddington',
	author_email='',
	description='',
	executables=executables
)
# subprocess.run([r'C:\Program Files\7-Zip\7z', 'a', '-mx=9', '-ms=4g', '-mhe=on', '-mmt=2', r'-t7z', 'build.7z', fr'{os.getcwd()}\build'])
# files = [r'C:\Program Files\7-Zip\7zSD.sfx', 'config.txt', 'build.7z']
# with open('bi_entry.exe', mode='w+b') as f:
# 	for fn in files:
# 		with open(fn, mode='rb') as f2:
# 			buffer_ = f2.readline()
# 			while buffer_:
# 				f.write(buffer_)
# 				buffer_ = f2.readline()
# subprocess.run([r'C:\Program Files\UPX\upx', '--ultra-brute', '--compress-icons=1', 'bi_entry.exe'])
