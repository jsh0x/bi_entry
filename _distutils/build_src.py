# coding=utf-8
import tempfile, shutil, os, pathlib, zipfile
from cx_Freeze import setup, Executable


def build_source(fp_list, base_dir, version):
	cwd = pathlib.Path.cwd()
	home = pathlib.WindowsPath.home()
	with tempfile.TemporaryDirectory() as temp_dir:
		temp_dir = pathlib.Path(temp_dir)
		for fp in fp_list:
			fp = pathlib.Path(str(fp))
			shutil.copytree(fp.relative_to(pathlib.Path.cwd()).as_posix(), str(temp_dir / fp.stem))
		[shutil.copy2(str(pyfile.relative_to(pathlib.Path.cwd())), str(temp_dir / str(pyfile.name))) for pyfile in base_dir.glob('*.py')]  # Copy Python files
		shutil.copy2(str(base_dir / 'images' / 'bi_entry2.ico'), str(temp_dir / 'bi_entry.ico'))  # Copy icon
		os.chdir(str(temp_dir))
		executables = [Executable(script='__init__.py', base='Win32GUI', targetName='bi_entry.exe', icon='bi_entry.ico'),
		               Executable(script='_checker.py', base='Win32GUI', targetName='checker.exe', icon='bi_entry.ico')]  # , shortcutName='BI_Entry', shortcutDir='DesktopFolder'
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

		with zipfile.ZipFile(str(cwd / 'src.zip'), 'w') as myzip:
			path = pathlib.WindowsPath(temp_dir) / 'build'
			path.rename('bin')
			path = pathlib.WindowsPath(temp_dir) / 'bin'
			[myzip.write(str(subpath.relative_to(temp_dir))) for subpath in path.rglob('*')]
			os.chdir(str(cwd))
		return cwd / 'src.zip'

__all__ = ['build_source']
