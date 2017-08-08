# from distutils.core import setup
import os
from cx_Freeze import setup, Executable

os.environ['TCL_LIBRARY'] = r'C:\Users\mfgpc00\AppData\Local\Programs\Python\Python36\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'C:\Users\mfgpc00\AppData\Local\Programs\Python\Python36\tcl\tk8.6'

executables = [Executable(script="bi_entry.py", base="Win32GUI", targetName="bi_entry.exe")]
packages = ['matplotlib', 'numpy', 'PIL', 'psutil', 'win32api',
			'pyautogui', 'pymssql', 'pywinauto', 'win32gui']
options = {
	'build_exe': {
		'packages': packages,
	},
}

setup(
	name='bi_entry',
	options=options,
	version='1.0.0',
	packages=[''],
	url='',
	license='',
	author='Josh Reddington',
	author_email='',
	description='',
	executables=executables
)





