# from distutils.core import setup
import configparser
import sys
import os
from cx_Freeze import setup, Executable


config = configparser.ConfigParser()
config.read_file(open('config.ini'))

FILE_NAME = sys.executable
DIR_NAME = os.path.dirname(sys.executable)

os.environ["TCL_LIBRARY"] = os.path.join(DIR_NAME, r"tcl\tcl8.6")
os.environ["TK_LIBRARY"] = os.path.join(DIR_NAME, r"tcl\tk8.6")

executables = [Executable(script="bi_entry.py", base="Win32GUI", targetName="bi_entry.exe", icon="bi_entry.ico")]
# executables = [Executable(script="bi_entry.py", base="Console", targetName="bi_entry.exe", icon="bi_entry.ico")]
packages = ['matplotlib', 'numpy', 'PIL', 'psutil', 'win32api',
			'pyautogui', 'pymssql', 'pywinauto', 'win32gui',
            'easygui']
include_files = [r'C:\Users\mfgpc00\AppData\Local\Programs\Python\Python36\DLLs\_ctypes.pyd',
                 r'C:\Users\mfgpc00\AppData\Local\Programs\Python\Python36\Lib\site-packages\_mssql.cp36-win_amd64.pyd',
                 'config.ini']
excludes = ["tkinter", "PyQt4.QtSql", "sqlite3",
		             "scipy.lib.lapack.flapack",
		             "PyQt4.QtNetwork",
		             "PyQt4.QtScript",
		             "numpy.core._dotblas",
		             "PyQt5"]
options = {
	'build_exe': {
		'packages': packages,
		'include_files': include_files
		}
}
""",
"excludes": excludes,
"optimize": 2"""

# TODO: Exclude files

setup(
	name='bi_entry',
	options=options,
	version=config.get('DEFAULT', 'version'),
	packages=[''],
	url='',
	license='',
	author='Josh Reddington',
	author_email='',
	description='',
	executables=executables
)





