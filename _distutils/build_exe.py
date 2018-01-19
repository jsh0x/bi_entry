# coding=utf-8
import os
import sys
import pathlib
import subprocess
import zipfile
import shutil
import tempfile
from cx_Freeze import setup, Executable


def build_installer(src_file: pathlib.Path, base_dir, dist_dir, version):
	cwd = pathlib.Path.cwd()
	with tempfile.TemporaryDirectory() as temp_dir:
		[shutil.copy2(str(fp), temp_dir + '/' + str(fp.name)) for fp in dist_dir.glob('*.py') if 'unpack' in str(fp)]
		shutil.copy2(str(base_dir / 'config.txt'), temp_dir + '/' + 'config.txt')
		os.chdir(temp_dir)
		executables = [Executable(script='unpack.py', base='Win32GUI', targetName='update.exe')]

		include_files = [src_file.as_posix()]

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
		shutil.copy2('BIEntry_Installer.exe', str(cwd / 'BIEntry_Installer.exe'))
		# shutil.copy2('installer.7z', str(main_dir / 'installer.7z'))
		os.chdir(str(cwd))
		# subprocess.run([r'.\req\UPX\upx', '--ultra-brute', 'BIEntry_Installer.exe'])
		# TODO: Run UPX on sfx module 'C:\Program Files\7-Zip\7zSD.sfx'


__all__ = ['build_installer']
