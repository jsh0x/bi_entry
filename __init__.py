__author__ = 'jsh0x'
__version__ = '1.5.0'

import configparser
import os
import pathlib
import struct
import sys
from os import fdopen, remove
from shutil import move
from sys import version_info as version
from tempfile import mkstemp
from typing import Sequence, Union

from win32com.client import Dispatch

packages = ['matplotlib', 'numpy', 'PIL', 'psutil', 'win32api',
            'pyautogui', 'pymssql', 'pywinauto', 'win32gui']

FILE_NAME = sys.executable
DIR_NAME = os.path.dirname(sys.executable)
os.environ["TCL_LIBRARY"] = os.path.join(DIR_NAME, r"tcl\tcl8.6")
os.environ["TK_LIBRARY"] = os.path.join(DIR_NAME, r"tcl\tk8.6")

loggers = ['root']
handlers = ['errorHandler', 'infoHandler', 'debugHandler', 'consoleHandler']
formatters = ['errorFormatter', 'infoFormatter', 'debugFormatter']
cwd = pathlib.WindowsPath.cwd()
log_dir = cwd / 'logs'


def list_to_string(iterable: Sequence, sep: str = ','):
	retval = ''
	delimiter_length = len(sep)
	for i in iterable:
		retval += str(i) + sep
	return retval[:-delimiter_length]


def find_file(name, path="C:/"):
	for root, dirs, files in os.walk(path):
		if name in files:
			return str(os.path.join(root, name)).replace('\\', '/')
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


def write_config(usr: str = '???', pwd: str = '???', fp: str = None):
	fp = find_file('WinStudio.exe', pathlib.Path.home().as_posix()) if fp is None else fp
	path = (os.path.dirname(sys.executable)).replace('\\', '/') + "/Scripts/pip3.6.exe"
	log_dir.mkdir(exist_ok=True)
	info_log_dir = log_dir / 'info.log'
	debug_log_dir = log_dir / 'dbg.log'
	config = configparser.ConfigParser(interpolation=None)
	module_list = packages
	# for mod in get_outdated_modules(path).keys():
	# 	if mod in module_list:
	# 		pass  # Update it
	config['DEFAULT'] = {'version':          __version__,
	                     'table':            '0',
	                     'flow':             'ASC',
	                     'process':          'None',
	                     'printer':          'None',
	                     'min_sl_instances': '1',
	                     'max_sl_instances': '1',
	                     'multiprocess':     'False'}
	config['Schedule'] = {'active_days':  '1,2,3,4,5,6',
	                      'active_hours': '0,1,5,6,7,8,9,10,11,12,13,14,15,18,19,20,21,22,23'
	                      }
	config['Paths'] = {'sl_exe':  fp,
	                   'pip_exe': path,
	                   'cwd':     cwd.as_posix()}
	config['Login'] = {'username': usr,
	                   'password': pwd}
	config['loggers'] = {'keys': list_to_string(loggers)}
	config['handlers'] = {'keys': list_to_string(handlers)}
	config['formatters'] = {'keys': list_to_string(formatters)}
	config['formatter_errorFormatter'] = {'format':  "[{asctime}][{levelname}][{filename}, function:{funcName}, line:{lineno!s}]  {message}",
	                                      'datefmt': "%X",
	                                      'style':   "{",
	                                      'class':   "logging.Formatter"}
	config['formatter_infoFormatter'] = {'format':  "[{asctime}]{levelname!s:<8} {message}",
	                                     'datefmt': "%x %X",
	                                     'style':   "{",
	                                     'class':   "logging.Formatter"}
	config['formatter_debugFormatter'] = {'format':  "[{asctime}.{msecs:0>3.0f}] {levelname!s:<5} {module!s:>8}.{funcName}:{lineno!s:<5} {message}",
	                                      'datefmt': "%X",
	                                      'style':   "{",
	                                      'class':   "logging.Formatter"}
	config['handler_errorHandler'] = {'class':     "StreamHandler",
	                                  'level':     "WARNING",
	                                  'formatter': "errorFormatter",
	                                  'args':      "(sys.stdout,)"}
	config['handler_infoHandler'] = {'class':     "handlers.TimedRotatingFileHandler",
	                                 'level':     "INFO",
	                                 'formatter': "infoFormatter",
	                                 'args':      f"('{info_log_dir.as_posix()}', 'D', 7, 3)"}
	config['handler_debugHandler'] = {'class':     "FileHandler",
	                                  'level':     "DEBUG",
	                                  'formatter': "debugFormatter",
	                                  'args':      f"('{debug_log_dir.as_posix()}', 'w')"}
	config['handler_consoleHandler'] = {'class':     "StreamHandler",
	                                    'level':     "DEBUG",
	                                    'formatter': "debugFormatter",
	                                    'args':      "()"}
	config['logger_root'] = {'level':    'DEBUG',
	                         'handlers': list_to_string(handlers[:4]),
	                         'qualname': 'root'}
	with open(cwd / 'config.ini', 'w') as configfile:
		config.write(configfile)


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
