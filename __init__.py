__author__ = 'jsh0x'
__version__ = '1.0.0'

import struct
import subprocess
import configparser
from sys import version_info as version
import os
import sys
from typing import Iterable, Sequence
import logging.config
import logging.handlers
import pathlib
packages = ['matplotlib', 'numpy', 'PIL', 'psutil', 'win32api',
			'pyautogui', 'pymssql', 'pywinauto', 'win32gui']
loggers = ['root', 'logTime', 'logControl']
handlers = ['errorHandler', 'infoHandler', 'debugHandler', 'consoleHandler', 'timeHandler', 'controlHandler']
formatters = ['errorFormatter', 'infoFormatter', 'debugFormatter', 'timeFormatter']
log_dir = pathlib.WindowsPath.cwd()/'logs'
log_dir.mkdir(exist_ok=True)
time_dir = pathlib.WindowsPath.cwd()/'time_logs'
time_dir.mkdir(exist_ok=True)
ctrl_dir = pathlib.WindowsPath.cwd()/'control_logs'
ctrl_dir.mkdir(exist_ok=True)

info_log_dir = str(log_dir/'info.log').replace('\\', '/')
debug_log_dir = str(log_dir/'dbg.log').replace('\\', '/')
time_log_dir = str(time_dir/'completed.log').replace('\\', '/')
control_log_dir = str(ctrl_dir/'controls.log').replace('\\', '/')

def list_to_string(iterable: Sequence, sep: str=','):
	retval = ''
	delimiter_length = len(sep)
	for i in iterable:
		retval += str(i)+sep
	return retval[:-delimiter_length]


def find_file(name, path="C:/"):
	for root, dirs, files in os.walk(path):
		if name in files:
			return str(os.path.join(root, name)).replace('\\', '/')
	else:
		return None


def get_outdated_modules(pip_dir) -> dict:
	retval = {}
	mods = str(subprocess.Popen([pip_dir, 'list', '--format=legacy', '--outdated'], stdout=subprocess.PIPE).communicate()[0])
	mods = (mods.split("'")[1]).split('\\r\\n')
	for mod in mods:
		try:
			mod = mod.split(' ')
			name, old, new = mod[0], (mod[1].rstrip(')')).lstrip('('), mod[4]
			retval[name] = (old, new)
		except:
			continue
	return retval


def write_config():
	path = (os.path.dirname(sys.executable)).replace('\\', '/')+"/Scripts/pip3.6.exe"
	config = configparser.ConfigParser(interpolation=None)
	module_list = packages
	for mod in get_outdated_modules(path).keys():
		if mod in module_list:
			pass  # Update it
	config['DEFAULT'] = {'printer': 'None',
						 'min_sl_instances': '1',
						 'max_sl_instances': '1',
						 'multiprocess': 'False'}
	config['Schedule'] = {'active_days': ''.join([str(i)+',' for i in range(1, 7)][:-1]),
	                      'active_hours': ''.join([str(i)+',' for i in range(5, 18)][:-1])
	                      }
	config['Paths'] = {'sl_exe': 'C:/Users/mfgpc00/AppData/Local/Apps/2.0/QQC2A2CQ.YNL/K5YT3MK7.VDY/sl8...ient_002c66e0bc74a4c9_0008.0003_1fdd36ef61625f38/WinStudio.exe',# find_file('WinStudio.exe'),
					   'pip_exe': path}
	config['Login'] = {'username': '???',
					   'password': '???'}
	config['loggers'] = {'keys': list_to_string(loggers)}
	config['handlers'] = {'keys': list_to_string(handlers)}
	config['formatters'] = {'keys': list_to_string(formatters)}
	config['formatter_errorFormatter'] = {'format': "[{asctime}][{levelname}][{filename}, function:{funcName}, line:{lineno!s}]  {message}",
										  'datefmt': "%X",
										  'style': "{",
										  'class': "logging.Formatter"}
	config['formatter_infoFormatter'] = {'format': "[{asctime}]{levelname!s:<8} {message}",
										 'datefmt': "%x %X",
										 'style': "{",
										 'class': "logging.Formatter"}
	config['formatter_debugFormatter'] = {'format': "[{asctime}.{msecs:0>3.0f}] {levelname!s:<5} {module!s:>8}.{funcName}:{lineno!s:<5} {message}",
										  'datefmt': "%X",
										  'style': "{",
										  'class': "logging.Formatter"}
	config['formatter_timeFormatter'] = {'format': "[{asctime}] {message}",
										 'datefmt': "%X",
										 'style': "{",
										 'class': "logging.Formatter"}
	config['handler_errorHandler'] = {'class': "StreamHandler",
									  'level': "WARNING",
									  'formatter': "errorFormatter",
									  'args': "(sys.stdout,)"}
	config['handler_infoHandler'] = {'class': "handlers.TimedRotatingFileHandler",
									 'level': "INFO",
									 'formatter': "infoFormatter",
									 'args': f"('{info_log_dir}', 'D', 7, 3)"}
	config['handler_debugHandler'] = {'class': "FileHandler",
									  'level': "DEBUG",
									  'formatter': "debugFormatter",
									  'args': f"('{debug_log_dir}', 'w')"}
	config['handler_consoleHandler'] = {'class': "StreamHandler",
										'level': "DEBUG",
										'formatter': "debugFormatter",
										'args': "()"}
	config['handler_timeHandler'] = {'class': "handlers.TimedRotatingFileHandler",
									 'level': "INFO",
									 'formatter': "timeFormatter",
									 'args': f"('{time_log_dir}', 'D', 1, 9000)"}
	config['handler_controlHandler'] = {'class': "FileHandler",
										'level': "DEBUG",
										'formatter': "timeFormatter",
										'args': f"('{control_log_dir}', 'w')"}
	config['logger_root'] = {'level': 'NOTSET',
							 'handlers': list_to_string(handlers[:4]),
							 'qualname': 'root'}
	config['logger_logTime'] = {'level': 'INFO',
								'handlers': 'timeHandler',
								'qualname': 'logTime'}
	config['logger_logControl'] = {'level': 'DEBUG',
								   'handlers': 'controlHandler',
								   'qualname': 'logControl'}
	with open('config.ini', 'w') as configfile:
		config.write(configfile)


if 'config.ini' not in os.listdir(os.getcwd()):
	write_config()

logging.config.fileConfig("config.ini")



bit = 8*struct.calcsize("P")
major, minor, micro = version.major, version.minor, version.micro

# TODO: Any time there is a major update, do a screen calibration
# TODO: If missing control in db, get it