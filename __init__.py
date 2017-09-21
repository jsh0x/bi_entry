__author__ = 'jsh0x'
__version__ = '1.1.11'

import struct
import configparser
from sys import version_info as version
import os
import sys
from typing import Sequence
from tempfile import mkstemp
from shutil import move
from os import fdopen, remove
import logging.config
import logging.handlers
import pathlib
packages = ['matplotlib', 'numpy', 'PIL', 'psutil', 'win32api',
			'pyautogui', 'pymssql', 'pywinauto', 'win32gui']


# class OneLineExceptionFormatter(logging.Formatter):
#     def formatException(self, exc_info):
#         """
#         Format an exception so that it prints on a single line.
#         """
#         result = super(OneLineExceptionFormatter, self).formatException(exc_info)
#         return repr(result)  # or format into one line however you want to
#
#     def format(self, record):
#         s = super(OneLineExceptionFormatter, self).format(record)
#         if record.exc_text:
#             s = s.replace('\n', '') + '|'
#         return s
#
# def configure_logging():
#     fh = logging.FileHandler('output.txt', 'w')
#     f = OneLineExceptionFormatter('%(asctime)s|%(levelname)s|%(message)s|',
#                                   '%d/%m/%Y %H:%M:%S')
#     fh.setFormatter(f)
#     root = logging.getLogger()
#     root.setLevel(logging.DEBUG)
#     root.addHandler(fh)
#
# def main():
#     configure_logging()
#     logging.info('Sample message')
#     try:
#         x = 1 / 0
#     except ZeroDivisionError as e:
#         logging.exception('ZeroDivisionError: %s', e)

FILE_NAME = sys.executable
DIR_NAME = os.path.dirname(sys.executable)
os.environ["TCL_LIBRARY"] = os.path.join(DIR_NAME, r"tcl\tcl8.6")
os.environ["TK_LIBRARY"] = os.path.join(DIR_NAME, r"tcl\tk8.6")

loggers = ['root']
handlers = ['errorHandler', 'infoHandler', 'debugHandler', 'consoleHandler']
formatters = ['errorFormatter', 'infoFormatter', 'debugFormatter']
cwd = pathlib.WindowsPath.cwd().parent.parent
log_dir = cwd / 'logs'

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

# def get_outdated_modules(pip_dir) -> dict:
# 	retval = {}
# 	mods = str(subprocess.Popen([pip_dir, 'list', '--format=legacy', '--outdated'], stdout=subprocess.PIPE).communicate()[0])
# 	mods = (mods.split("'")[1]).split('\\r\\n')
# 	for mod in mods:
# 		try:
# 			mod = mod.split(' ')
# 			name, old, new = mod[0], (mod[1].rstrip(')')).lstrip('('), mod[4]
# 			retval[name] = (old, new)
# 		except:
# 			continue
# 	return retval


def write_config(usr: str='???', pwd: str='???', fp: str=find_file('WinStudio.exe')):
	path = (os.path.dirname(sys.executable)).replace('\\', '/')+"/Scripts/pip3.6.exe"
	log_dir.mkdir(exist_ok=True)
	info_log_dir = str(log_dir / 'info.log').replace('\\', '/')
	debug_log_dir = str(log_dir / 'dbg.log').replace('\\', '/')
	config = configparser.ConfigParser(interpolation=None)
	module_list = packages
	# for mod in get_outdated_modules(path).keys():
	# 	if mod in module_list:
	# 		pass  # Update it
	config['DEFAULT'] = {'version': __version__,
	                     'printer': 'None',
						 'min_sl_instances': '1',
						 'max_sl_instances': '1',
						 'multiprocess': 'False'}
	config['Schedule'] = {'active_days': ','.join(str(i) for i in range(1, 6)),
	                      'active_hours': ','.join(str(i) for i in range(5, 18))
	                      }
	config['Paths'] = {'sl_exe': fp,
					   'pip_exe': path,
	                   'cwd': str(cwd).replace('\\', '/')}
	config['Login'] = {'username': usr,
					   'password': pwd}
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
	config['logger_root'] = {'level': 'DEBUG',
							 'handlers': list_to_string(handlers[:4]),
							 'qualname': 'root'}
	with open(str(cwd).replace('\\', '/') + '/config.ini', 'w') as configfile:
		config.write(configfile)


if 'config.ini' not in os.listdir(str(cwd).replace('\\', '/')):
	write_config()

config = configparser.ConfigParser()
config.read_file(open(str(cwd).replace('\\', '/')+'/config.ini'))
os.chdir(config.get('Paths', 'cwd'))
update_config()

bit = 8*struct.calcsize("P")
major, minor, micro = version.major, version.minor, version.micro

# TODO: Any time there is a major update, do a screen calibration
# TODO: If missing control in db, get it