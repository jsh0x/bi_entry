#! python3 -W ignore
# coding=utf-8
import compileall
import configparser
import glob
import os
import sys
import pathlib
import subprocess
import zipfile
import shutil
import tempfile

# Compiles the sourcecode
for f in glob.iglob('*.py'):
	compileall.compile_file(f, force=True)
compileall.compile_dir(os.getcwd() + '\\processes', force=True)
compileall.compile_dir(os.getcwd() + '\\utils', force=True)

from cx_Freeze import setup, Executable

config = configparser.ConfigParser()
config.read_file(open('config.ini'))
__version__ = '1.5.1'
major, minor, micro = map(int, map(str.strip, __version__.split('.', 3)))
version = f"{major}.{minor}.{micro}"


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


# update_init(version)

FILE_NAME = sys.executable
DIR_NAME = os.path.dirname(sys.executable)

os.environ['TCL_LIBRARY'] = os.path.join(DIR_NAME, r'tcl\tcl8.6')
os.environ['TK_LIBRARY'] = os.path.join(DIR_NAME, r'tcl\tk8.6')
home = pathlib.WindowsPath.home()
main_dir = pathlib.WindowsPath.cwd()

def build_dist():
	with tempfile.TemporaryDirectory() as temp_dir:
		shutil.copytree('processes', temp_dir + '/processes')
		shutil.copytree('utils', temp_dir + '/utils')

		[shutil.copy2(str(fp), temp_dir + '/' + str(fp.name)) for fp in main_dir.glob('*.py') if 'unpack' not in str(fp) and 'setup' not in str(fp)]
		shutil.copy2(str(main_dir / 'images' / 'bi_entry2.ico'), temp_dir + '/bi_entry.ico')
		os.chdir(temp_dir)
		executables = [Executable(script='__main__.py', base='Win32GUI', targetName='bi_entry.exe', icon='bi_entry.ico')]  # , shortcutName='BI_Entry', shortcutDir='DesktopFolder'
		# https://msdn.microsoft.com/en-us/library/aa370905(v=vs.85).aspx#System_Folder_Properties
		packages = ['psutil', 'win32api', 'pyautogui',
		            'pymssql', 'pywinauto', 'win32gui',
		            'easygui', '_mssql', 'uuid', 'subprocess',
		            'comtypes', 'sqlite3', 'numpy']
		include_files = [home / r'AppData\Local\Programs\Python\Python36\DLLs\_ctypes.pyd',
						 home / r'AppData\Local\Programs\Python\Python36\DLLs\_sqlite3.pyd',
		                 home / r'AppData\Local\Programs\Python\Python36\Lib\site-packages\_mssql.cp36-win_amd64.pyd',
						 home / r'AppData\Local\Programs\Python\Python36\DLLs\sqlite3.dll',
		                 'bi_entry.ico']
		excludes = ['tkinter', 'PyQt4.QtSql',
		            'scipy.lib.lapack.flapack', 'matplotlib',
		            'PyQt4.QtNetwork', 'PyQt4.QtScript', 'PyQt5',
		            'colorama', 'pygments', 'mpl-data', 'email']
		options = {
			'build_exe': {
				'packages':      packages,
				'include_files': include_files,
				'excludes':      excludes
				}
			}
		""",
			'bdist_msi': {
				'add_to_path': False,
				'initial_target_dir'
				}"""
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
		# FIXME: PyZipFile? - Get suffixes to check
		with zipfile.ZipFile(str(main_dir / 'build.zip'), 'w') as myzip:
			path = pathlib.WindowsPath(temp_dir) / 'build'
			path.rename('bin')
			path = pathlib.WindowsPath(temp_dir) / 'bin'
			[myzip.write(str(subpath.relative_to(temp_dir))) for subpath in path.rglob('*')]
			os.chdir(str(main_dir))
	return main_dir / 'build.zip'


def build_installer(dist_file: pathlib.Path):
	with tempfile.TemporaryDirectory() as temp_dir:
		[shutil.copy2(str(fp), temp_dir + '/' + str(fp.name)) for fp in main_dir.glob('*.py') if 'unpack' in str(fp)]
		shutil.copy2(str(main_dir / 'config.txt'), temp_dir + '/' + 'config.txt')
		os.chdir(temp_dir)
		executables = [Executable(script='unpack.py', base='Win32GUI', targetName='install.exe')]

		include_files = [dist_file.as_posix()]

		excludes = ['tkinter', 'PyQt4.QtSql',
		            'scipy.lib.lapack.flapack', 'matplotlib',
		            'PyQt4.QtNetwork', 'PyQt4.QtScript',
		            'numpy.core._dotblas', 'PyQt5',
		            'colorama', 'pygments', 'mpl-data', 'email',
		            'numpy', 'sqlite3', 'PIL']
		options = {
			'build_exe': {
				'include_files': include_files,
				'excludes':      excludes
				}
			}
		# TODO: Exclude files

		setup(
				name='installer',
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

		subprocess.run([r'C:\Program Files\7-Zip\7z', 'a', '-mx=9', '-ms=4g', '-mhe=on', '-mmt=2', r'-t7z', 'installer.7z', temp_dir + '/build'])
		files = [r'C:\Program Files\7-Zip\7zSD.sfx', 'config.txt', 'installer.7z']
		with open('BIEntry_Installer.exe', mode='w+b') as f:
			for fn in files:
				with open(fn, mode='rb') as f2:
					buffer_ = f2.readline()
					while buffer_:
						f.write(buffer_)
						buffer_ = f2.readline()
		shutil.copy2('BIEntry_Installer.exe', str(main_dir / 'BIEntry_Installer.exe'))
		# shutil.copy2('installer.7z', str(main_dir / 'installer.7z'))
		os.chdir(str(main_dir))
		# subprocess.run([r'.\req\UPX\upx', '--ultra-brute', 'BIEntry_Installer.exe'])
		# TODO: Run UPX on sfx module 'C:\Program Files\7-Zip\7zSD.sfx'

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

def build():
	with tempfile.TemporaryDirectory() as temp_dir:
		shutil.copytree('processes', temp_dir + '/processes')
		shutil.copytree('utils', temp_dir + '/utils')

		[shutil.copy2(str(fp), temp_dir + '/' + str(fp.name)) for fp in main_dir.glob('*.py') if 'unpack' not in str(fp) and 'setup' not in str(fp)]
		shutil.copy2(str(main_dir / 'images' / 'bi_entry2.ico'), temp_dir + '/bi_entry.ico')
		os.chdir(temp_dir)
		executables = [Executable(script='__main__.py', base='Win32GUI', targetName='bi_entry.exe', icon='bi_entry.ico')]  # , shortcutName='BI_Entry', shortcutDir='DesktopFolder'
		# https://msdn.microsoft.com/en-us/library/aa370905(v=vs.85).aspx#System_Folder_Properties
		packages = ['psutil', 'win32api', 'pyautogui',
		            'pymssql', 'pywinauto', 'win32gui',
		            'easygui', '_mssql', 'uuid', 'subprocess',
		            'comtypes', 'sqlite3']
		include_files = [home / r'AppData\Local\Programs\Python\Python36\DLLs\_ctypes.pyd',
						 home / r'AppData\Local\Programs\Python\Python36\DLLs\_sqlite3.pyd',
		                 home / r'AppData\Local\Programs\Python\Python36\Lib\site-packages\_mssql.cp36-win_amd64.pyd',
						 home / r'AppData\Local\Programs\Python\Python36\DLLs\sqlite3.dll',
		                 'bi_entry.ico']
		excludes = ['tkinter', 'PyQt4.QtSql',
		            'scipy.lib.lapack.flapack', 'matplotlib',
		            'PyQt4.QtNetwork', 'PyQt4.QtScript',
		            'numpy.core._dotblas', 'PyQt5',
		            'colorama', 'pygments', 'mpl-data', 'email']
		options = {
			'build_exe': {
				'packages':      packages,
				'include_files': include_files,
				'excludes':      excludes
				}
			}
		""",
			'bdist_msi': {
				'add_to_path': False,
				'initial_target_dir'
				}"""
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
		# FIXME: PyZipFile? - Get suffixes to check
		with tempfile.TemporaryDirectory() as temp_dir2:
			with zipfile.ZipFile(temp_dir2 + '/build.zip', 'w') as myzip:
				path = pathlib.WindowsPath(temp_dir) / 'build'
				path.rename('bin')
				path = pathlib.WindowsPath(temp_dir) / 'bin'
				[myzip.write(str(subpath.relative_to(temp_dir))) for subpath in path.rglob('*')]
			dist_file = temp_dir2 + '/build.zip'
			with tempfile.TemporaryDirectory() as temp_dir:
				[shutil.copy2(str(fp), temp_dir + '/' + str(fp.name)) for fp in main_dir.glob('*.py') if 'unpack' in str(fp) or '__init__' in str(fp)]
				shutil.copy2(str(main_dir / 'config.txt'), temp_dir + '/' + 'config.txt')
				os.chdir(temp_dir)
				executables = [Executable(script='unpack.py', base='Console', targetName='install.exe')]

				include_files = [dist_file]

				excludes = ['tkinter', 'PyQt4.QtSql',
				            'scipy.lib.lapack.flapack', 'matplotlib',
				            'PyQt4.QtNetwork', 'PyQt4.QtScript',
				            'numpy.core._dotblas', 'PyQt5',
				            'colorama', 'pygments', 'mpl-data', 'email',
				            'numpy', 'sqlite3', 'PIL']
				options = {
					'build_exe': {
						'include_files': include_files,
						'excludes':      excludes
						}
					}
				# TODO: Exclude files

				setup(
						name='installer',
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

				subprocess.run([r'C:\Program Files\7-Zip\7z', 'a', '-mx=9', '-ms=4g', '-mhe=on', '-mmt=2', r'-t7z', 'installer.7z', fr'{os.getcwd()}\build'])
				files = [r'C:\Program Files\7-Zip\7zSD.sfx', 'config.txt', 'installer.7z']
				with open('BIEntry_Installer.exe', mode='w+b') as f:
					for fn in files:
						with open(fn, mode='rb') as f2:
							buffer_ = f2.readline()
							while buffer_:
								f.write(buffer_)
								buffer_ = f2.readline()
				shutil.copy2('BIEntry_Installer.exe', str(main_dir / 'BIEntry_Installer.exe'))
				os.chdir(str(main_dir))
				print(temp_dir, temp_dir2)
		subprocess.run([r'.\req\UPX\upx', '--ultra-brute', 'BIEntry_Installer.exe'])


dist = build_dist()
build_installer(dist)
os.remove(str(dist.relative_to(main_dir)))
# build()
