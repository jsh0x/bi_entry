#! python3 -W ignore
# coding=utf-8
__author__ = 'jsh0x'
__version__ = '1.5.0'

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

my_directory = pathlib.WindowsPath(os.environ["PROGRAMFILES"]) / 'BI_Entry'


packages = ['matplotlib', 'numpy', 'PIL', 'psutil', 'win32api',
            'pyautogui', 'pymssql', 'pywinauto', 'win32gui']

FILE_NAME = sys.executable
DIR_NAME = os.path.dirname(sys.executable)
os.environ["TCL_LIBRARY"] = os.path.join(DIR_NAME, r"tcl\tcl8.6")
os.environ["TK_LIBRARY"] = os.path.join(DIR_NAME, r"tcl\tk8.6")

loggers = ['root']
handlers = ['errorHandler', 'infoHandler', 'debugHandler', 'consoleHandler']
formatters = ['errorFormatter', 'infoFormatter', 'debugFormatter']


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
	log_dir.mkdir(exist_ok=True)
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
				                     'qualname': 'root'}},
		                   'formatters':
			                   {'simple':
				                    {'format': '[{asctime}]{levelname!s:^8}| {message}',
				                     'datefmt': '%X',
				                     'style': '{'},
			                    'detailed':
				                    {'format': '[{asctime}]{levelname} | {filename}(Thread-{threadName}) | function:{funcName} | line:{lineno!s} | {message}',
				                     'datefmt': '%x %X',
				                     'style': '{'},
			                    'verbose':
				                    {'format':  '{asctime}.{msecs:0>3.0f}[{levelname!s:<5}] | Thread-{threadName} | {module!s:>8}.{funcName}:{lineno!s:<5} | {message}',
				                     'datefmt': '%X',
				                     'style':   '{'}},
		                   'handlers':
			                   {'errors':
				                    {'class': 'FileHandler',
				                     'level': 'ERROR',
				                     'formatter': 'detailed',
				                     'args': [(log_dir / 'err.log').as_posix(), 'a']},  # 'args': [log_dir.as_posix()]},
			                    'console':
				                    {'class': 'StreamHandler',
				                     'level': 'INFO',
				                     'formatter': 'verbose'},
			                    'info':
				                    {'class': 'FileHandler',
				                     'level': 'INFO',
				                     'formatter': 'simple',
				                     'args': [(log_dir / 'info.log').as_posix(), 'a']},  # 'args': [(log_dir / 'info').as_posix()]},
			                    'debug':
				                    {'class': 'FileHandler',
				                     'level': 'DEBUG',
				                     'formatter': 'detailed',
				                     'args': [(log_dir / 'debug.log').as_posix(), 'a']}}}}
	write_config(config_content, my_directory)


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


config = read_config(my_directory)
logging_config = config['Logging']
from _logging import MyHandler

desktop = pathlib.WindowsPath.home() / 'Desktop'
shortcut = desktop / 'bi_entry.lnk'
if not shortcut.exists():
	create_shortcut(name='bi_entry', exe_path=pathlib.WindowsPath.cwd() / 'bi_entry.exe', startin=pathlib.WindowsPath.home() / 'Desktop' / 'build',
	                icon_path=pathlib.WindowsPath.cwd() / 'bi_entry.ico')
	sys.exit()

if 'config.ini' not in os.listdir(cwd.as_posix()):
	write_config()

# cwd = pathlib.WindowsPath.home() / 'Desktop' / 'build'
config = configparser.ConfigParser()
config.read_file(open('config.ini'))
update_config()

bit = 8 * struct.calcsize("P")
major, minor, micro = version.major, version.minor, version.micro
