#! python3 -W ignore
# coding=utf-8
__author__ = 'jsh0x'
__version__ = '1.5.3'

import json
import os
import pathlib
import struct
import sys
from os import fdopen, remove
from shutil import move
import io
import traceback
from sys import version_info as version
from tempfile import mkstemp
from typing import Sequence, Union
from win32com.client import Dispatch
import json
import os
import pathlib
from typing import Any, Dict, Iterable, Union

from constants import REGEX_NUMERIC_RANGES
from _config import write_config, read_config
from _logging import initialize_logger

# my_directory = pathlib.WindowsPath(os.environ["PROGRAMFILES"]) / 'BI_Entry'
my_directory = pathlib.WindowsPath(os.environ["PROGRAMDATA"]) / 'BI_Entry'
file_bytes = 104800000

packages = ['matplotlib', 'numpy', 'PIL', 'psutil', 'win32api',
            'pyautogui', 'pymssql', 'pywinauto', 'win32gui']

FILE_NAME = sys.executable
DIR_NAME = os.path.dirname(sys.executable)
os.environ["TCL_LIBRARY"] = os.path.join(DIR_NAME, r"tcl\tcl8.6")
os.environ["TK_LIBRARY"] = os.path.join(DIR_NAME, r"tcl\tk8.6")

def find_file(name, path="C:/"):
	for root, dirs, files in os.walk(path):
		if name in files:
			return str(os.path.join(root, name)).replace('\\', '/')
	else:
		return None

def find_SyteLine() -> pathlib.WindowsPath:
	path = pathlib.WindowsPath.home() / 'AppData' / 'Local' / 'Apps'
	res = [i for i in path.rglob('winstudio.exe') if i.parent.name.startswith('sl8') and '_none_' not in i.parent.name]
	if res:
		return res[0]
	else:
		return None

def update_config():
	# Create temp file
	fh, abs_path = mkstemp()
	with fdopen(fh, 'w') as new_file:
		with open('config.ini') as old_file:
			for line in old_file:
				if '=' in line:
					k, v = map(str.strip, line.split('=', 1))
					if k == 'version':
						new_file.write(f"{k} = {__version__}\n")
					else:
						new_file.write(line)
				else:
					new_file.write(line)
	# Remove original file
	remove('config.ini')
	# Move new file
	move(abs_path, 'config.ini')


def create_config(usr, pwd):
	sl8_fp = find_SyteLine()
	log_dir = my_directory / 'logs'
	log_dir.mkdir(parents=True, exist_ok=True)
	module_list = packages
	config_content = {'Default':
		                  {'version': __version__},
	                  'Schedule':
		                  {'active_days': list(range(7))[1:],
		                   'active_hours': list(range(0, 2)) + list(range(5, 16)) + list(range(18, 24))},
	                  'Paths':
		                  {'syteline_exe': sl8_fp.as_posix()},
	                  'Login':
		                  {'username': usr,
		                   'password': pwd},
	                  'Logging':
		                  {'version': 1,
		                   'loggers':
			                   {'root':
				                    {'level': 'DEBUG',
				                     'handlers': ['errors', 'info', 'debug', 'console'],
				                     'qualname': 'root'},
			                    'UnitLogger':
				                    {'level':    'DEBUG',
				                     'handlers': ['errors', 'unitInfo'],
				                     'qualname': 'UnitLogger'},
			                    'SQLLogger':
				                    {'level':   'DEBUG',
				                     'handlers': ['errors', 'sqlInfo'],
				                     'qualname': 'SQLLogger'}},
		                   'formatters':
			                   {'simple':
				                    {'format': '[{asctime}]{levelname!s:>5}| {message}',
				                     'datefmt': '%X',
				                     'style': '{'},
			                    'error':
				                    {'format': '[{asctime}]{levelname} | {filename}(Thread-{threadName}) | function:{funcName} | line:{lineno!s} | {message}\n',
				                     'datefmt': '%x %X',
				                     'style': '{'},
			                    'verbose':
				                    {'format':  '{asctime}.{msecs:0>3.0f}[{levelname!s:<5}] | Thread-{threadName} | {module!s:>8}.{funcName}:{lineno!s:<5} | {message}',
				                     'datefmt': '%X',
				                     'style':   '{'},
			                    'unitSpecialized':
				                    {'format': '{asctime}.{msecs:0>3.0f}|{message}',
				                     'datefmt': '%X',
				                     'style': '{'},
			                    'sqlSpecialized':
				                    {'format':  '{asctime}.{msecs:0>3.0f}{levelname!s:>5}| {message}',
				                     'datefmt': '%X',
				                     'style':   '{'}},
		                   'handlers':
			                   {'errors':
				                    {'class': 'RotatingFileHandler',
				                     'level': 'ERROR',
				                     'formatter': 'error',
				                     'args': [(log_dir / 'err.log').as_posix(), 'a', file_bytes, 5]},  # 'args': [log_dir.as_posix()]},
			                    'console':
				                    {'class': 'StreamHandler',
				                     'level': 'DEBUG',
				                     'formatter': 'verbose'},
			                    'info':
				                    {'class': 'RotatingFileHandler',
				                     'level': 'INFO',
				                     'formatter': 'simple',
				                     'args': [(log_dir / 'info.log').as_posix(), 'a', file_bytes, 5]},  # 'args': [(log_dir / 'info').as_posix()]},
			                    'debug':
				                    {'class': 'RotatingFileHandler',
				                     'level': 'DEBUG',
				                     'formatter': 'verbose',
				                     'args': [(log_dir / 'debug.log').as_posix(), 'a', file_bytes, 5]},
			                    'unitInfo':
				                    {'class': 'RotatingFileHandler',
				                     'level': 'DEBUG',
				                     'formatter': 'unitSpecialized',
				                     'args': [(log_dir / 'unit.log').as_posix(), 'a', file_bytes, 5]},
			                    'sqlInfo':
				                    {'class':     'RotatingFileHandler',
				                     'level':     'DEBUG',
				                     'formatter': 'sqlSpecialized',
				                     'args':      [(log_dir / 'sql.log').as_posix(), 'a', file_bytes, 5]}}}}
	write_config(config_content, my_directory)
#

def create_shortcut(name: str, exe_path: Union[str, bytes, pathlib.Path, os.PathLike], startin: Union[str, bytes, pathlib.Path, os.PathLike], icon_path: Union[str, bytes, pathlib.Path, os.PathLike]):
	shell = Dispatch('WScript.Shell')
	# shortcut_file = pathlib.WindowsPath.home() / 'Desktop' / name + '.lnk'
	home = pathlib.WindowsPath.home()
	desktop = tuple(home.glob('./Desktop'))[0] if tuple(home.glob('./Desktop')) else None
	assert desktop is not None
	shortcut_file = desktop / (name + '.lnk')
	exe_path = exe_path.as_posix() if issubclass(type(exe_path), pathlib.Path) else exe_path
	startin = startin.as_posix() if issubclass(type(startin), pathlib.Path) else startin
	icon_path = icon_path.as_posix() if issubclass(type(icon_path), pathlib.Path) else icon_path
	shortcut = shell.CreateShortCut(shortcut_file.as_posix())
	shortcut.Targetpath = exe_path
	shortcut.WorkingDirectory = startin
	shortcut.IconLocation = icon_path
	shortcut.save()

try:
	config = read_config(my_directory)
except FileNotFoundError:
	my_name = os.environ['COMPUTERNAME']
	if my_name == 'BIGBERAESEW10':
		create_config('BISync03', 'Gue$$!ngN0')
	elif my_name == 'MFGW10PC-1':
		create_config('jredding', 'JRSep17!')
	elif my_name == 'MFGPC89':
		create_config('BISync01', 'Trans@cti0nsN0')
	elif my_name == 'MFGW10PC-27':
		create_config('BISync02', 'Re@s0nsN0')
	else:
		create_config('jredding', 'JRSep17!')
	if False:
		create_config('bigberae', 'W!nter17')
	config = read_config(my_directory)
try:
	initialize_logger(config['Logging'])
except ModuleNotFoundError:
	pass

# desktop = pathlib.WindowsPath.home() / 'Desktop'
# shortcut = desktop / 'bi_entry.lnk'
# if not shortcut.exists():
# 	create_shortcut(name='BI_Entry', exe_path=my_directory / 'bin' / 'exe.win-amd64-3.6' / 'bi_entry.exe', startin=my_directory,
# 	                icon_path=my_directory / 'bin' / 'exe.win-amd64-3.6' / 'bi_entry.ico')
# 	sys.exit()

bit = 8 * struct.calcsize("P")
major, minor, micro = version.major, version.minor, version.micro
