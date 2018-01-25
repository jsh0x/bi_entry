# coding=utf-8
import json, pathlib, os
from collections import UserDict
from typing import Any, Dict, Union
from common import *

KILOBYTE = 1024  # Bytes
MEGABYTE = 1048576  # Bytes
GIGABYTE = 1073741824  # Bytes


class Config(UserDict):
	filepath = None

	def __init__(self, content: dict):
		UserDict.__init__(self, content)

	@classmethod
	def open(cls, fp: Filepath):
		fp = normalize_filepath(fp).with_suffix('.json')
		if not fp.exists():
			raise OSError
		retval = cls(cls._read(fp))
		retval.filepath = fp
		return retval

	@classmethod
	def write(cls, obj, fp: Filepath):
		fp = normalize_filepath(fp).with_suffix('.json')
		# assert fp.is_file()

		retval = cls(obj)
		retval.save(fp)
		return retval

	@staticmethod
	def _read(fp: Filepath):
		fp = normalize_filepath(fp).with_suffix('.json')
		return json.load(fp.open())

	def read(self, fp: Filepath=None):
		if (fp is None) and (self.filepath is None):
			raise ValueError
		elif self.filepath is None:
			fp = normalize_filepath(fp).with_suffix('.json')
		else:
			fp = self.filepath
		self.data = json.load(fp.open())

	def save(self, fp: Filepath=None):
		if (fp is None) and (self.filepath is None):
			fp = pathlib.Path.cwd().with_name('config').with_suffix('.json')
		elif self.filepath is None:
			fp = normalize_filepath(fp).with_suffix('.json')
		else:
			fp = self.filepath

		json.dump(self.data, fp.open(mode='w+'), indent='\t')
		self.filepath = fp

def DefaultConfig(fp: Filepath=None, usr: str=None, pwd=None, sl8_fp: Filepath=None) -> Config:
	if fp is None:
		fp = pathlib.WindowsPath(os.environ["PROGRAMDATA"]) / 'BI_Entry' / 'config.json'
	log_dir = pathlib.WindowsPath(os.environ["PROGRAMDATA"]) / 'BI_Entry' / 'logs'
	log_dir.mkdir(exist_ok=True)

	# def create_config(usr: str, pwd, sl8_fp: Filepath, log_dir: Filepath, content: dict=None):
	# 	sl8_fp = find_SyteLine()
	# 	log_dir = my_directory / 'logs'
	# 	log_dir.mkdir(parents=True, exist_ok=True)
	# 	module_list = packages
	if sl8_fp is None:
		sl8_fp = find_SyteLine()

	if usr is None or pwd is None:
		my_name = os.environ['COMPUTERNAME']
		if my_name == 'BIGBERAESEW10':
			usr, pwd = 'BISync03', 'Gue$$!ngN0'
		elif my_name == 'MFGW10PC-1':
			usr, pwd = 'jredding', 'JRJan18!'
		elif my_name == 'MFGPC89':
			usr, pwd = 'BISync01', 'Trans@cti0nsN0'
		elif my_name == 'MFGW10PC-27':
			usr, pwd = 'BISync02', 'Re@s0nsN0'
		else:
			usr, pwd = 'bigberae', 'W!nter17'

	whole_hour = [x for x in range(60)]

	file_size = MEGABYTE * 100
	config_content = {'Schedule':
		                  {1: {0: whole_hour,
		                       1: whole_hour,
		                       2: whole_hour,
		                       3: whole_hour,
		                       4: whole_hour,
		                       5: whole_hour,
		                       6: whole_hour,
		                       7: whole_hour,
		                       8: whole_hour,
		                       9: whole_hour,
		                       10: whole_hour,
		                       11: whole_hour,
		                       12: whole_hour,
		                       13: whole_hour,
		                       14: whole_hour,
		                       15: whole_hour,
		                       16: [x for x in range(45)],
		                       20: [x for x in range(15, 60)],
		                       21: whole_hour,
		                       22: whole_hour,
		                       23: whole_hour},
		                   2: {0: whole_hour,
		                       1: whole_hour,
		                       2: whole_hour,
		                       3: whole_hour,
		                       4: whole_hour,
		                       5: whole_hour,
		                       6: whole_hour,
		                       7: whole_hour,
		                       8: whole_hour,
		                       9: whole_hour,
		                       10: whole_hour,
		                       11: whole_hour,
		                       12: whole_hour,
		                       13: whole_hour,
		                       14: whole_hour,
		                       15: whole_hour,
		                       16: [x for x in range(45)],
		                       20: [x for x in range(15, 60)],
		                       21: whole_hour,
		                       22: whole_hour,
		                       23: whole_hour},
		                   3: {0: whole_hour,
		                       1: whole_hour,
		                       2: whole_hour,
		                       3: whole_hour,
		                       4: whole_hour,
		                       5: whole_hour,
		                       6: whole_hour,
		                       7: whole_hour,
		                       8: whole_hour,
		                       9: whole_hour,
		                       10: whole_hour,
		                       11: whole_hour,
		                       12: whole_hour,
		                       13: whole_hour,
		                       14: whole_hour,
		                       15: [x for x in range(45)],
		                       18: [x for x in range(15, 60)],
		                       19: whole_hour,
		                       20: whole_hour,
		                       21: whole_hour,
		                       22: whole_hour,
		                       23: whole_hour},
		                   4: {0: whole_hour,
		                       1: whole_hour,
		                       2: whole_hour,
		                       3: whole_hour,
		                       4: whole_hour,
		                       5: whole_hour,
		                       6: whole_hour,
		                       7: whole_hour,
		                       8: whole_hour,
		                       9: whole_hour,
		                       10: whole_hour,
		                       11: whole_hour,
		                       12: whole_hour,
		                       13: whole_hour,
		                       14: whole_hour,
		                       15: whole_hour,
		                       16: [x for x in range(45)],
		                       20: [x for x in range(15, 60)],
		                       21: whole_hour,
		                       22: whole_hour,
		                       23: whole_hour},
		                   5: {0: whole_hour,
		                       1: whole_hour,
		                       2: whole_hour,
		                       3: whole_hour,
		                       4: whole_hour,
		                       5: whole_hour,
		                       6: whole_hour,
		                       7: whole_hour,
		                       8: whole_hour,
		                       9: whole_hour,
		                       10: whole_hour,
		                       11: whole_hour,
		                       12: whole_hour,
		                       13: whole_hour,
		                       14: whole_hour,
		                       15: whole_hour,
		                       16: [x for x in range(45)],
		                       20: [x for x in range(15, 60)],
		                       21: whole_hour,
		                       22: whole_hour,
		                       23: whole_hour},
		                   6: {0: whole_hour,
		                       1: whole_hour,
		                       2: whole_hour,
		                       3: whole_hour,
		                       4: whole_hour,
		                       5: whole_hour,
		                       6: whole_hour,
		                       7: whole_hour,
		                       8: whole_hour,
		                       9: whole_hour,
		                       10: whole_hour,
		                       11: whole_hour,
		                       12: whole_hour,
		                       13: whole_hour,
		                       14: whole_hour,
		                       15: whole_hour,
		                       16: [x for x in range(45)],
		                       20: [x for x in range(15, 60)],
		                       21: whole_hour,
		                       22: whole_hour,
		                       23: whole_hour}},
	                  'Paths':
		                  {'syteline_exe': str(sl8_fp)},
	                  'Login':
		                  {'username': usr,
		                   'password': pwd},
	                  'Logging':
		                  {'version': 1,
		                   'loggers':
		                              {'root':
			                               {'level':    'DEBUG',
			                                'handlers': ['errors', 'info', 'debug', 'console'],
			                                'qualname': 'root'},
		                               'UnitLogger':
			                               {'level':    'DEBUG',
			                                'handlers': ['errors', 'unitInfo'],
			                                'qualname': 'UnitLogger'},
		                               'SQLLogger':
			                               {'level':    'DEBUG',
			                                'handlers': ['errors', 'sqlInfo'],
			                                'qualname': 'SQLLogger'}},
		                   'formatters':
		                              {'simple':
			                               {'format':  '[{asctime}]{levelname!s:>5}| {message}',
			                                'datefmt': '%X',
			                                'style':   '{'},
		                               'error':
			                               {'format':  '[{asctime}]{levelname} | {filename}(Thread-{threadName}) | function:{funcName} | line:{lineno!s} | {message}\n',
			                                'datefmt': '%x %X',
			                                'style':   '{'},
		                               'verbose':
			                               {'format':  '{asctime}.{msecs:0>3.0f}[{levelname!s:<5}] | Thread-{threadName} | {module!s:>8}.{funcName}:{lineno!s:<5} | {message}',
			                                'datefmt': '%X',
			                                'style':   '{'},
		                               'unitSpecialized':
			                               {'format':  '{asctime}.{msecs:0>3.0f}|{message}',
			                                'datefmt': '%X',
			                                'style':   '{'},
		                               'sqlSpecialized':
			                               {'format':  '{asctime}.{msecs:0>3.0f}{levelname!s:>5}| {message}',
			                                'datefmt': '%X',
			                                'style':   '{'}},
		                   'handlers':
		                              {'errors':
			                               {'class':     'RotatingFileHandler',
			                                'level':     'ERROR',
			                                'formatter': 'error',
			                                'args':      [(log_dir / 'err.log').as_posix(), 'a', file_size, 5]},  # 'args': [log_dir.as_posix()]},
		                               'console':
			                               {'class':     'StreamHandler',
			                                'level':     'DEBUG',
			                                'formatter': 'verbose'},
		                               'info':
			                               {'class':     'RotatingFileHandler',
			                                'level':     'INFO',
			                                'formatter': 'simple',
			                                'args':      [(log_dir / 'info.log').as_posix(), 'a', file_size, 5]},  # 'args': [(log_dir / 'info').as_posix()]},
		                               'debug':
			                               {'class':     'RotatingFileHandler',
			                                'level':     'DEBUG',
			                                'formatter': 'verbose',
			                                'args':      [(log_dir / 'debug.log').as_posix(), 'a', file_size, 5]},
		                               'unitInfo':
			                               {'class':     'RotatingFileHandler',
			                                'level':     'DEBUG',
			                                'formatter': 'unitSpecialized',
			                                'args':      [(log_dir / 'unit.log').as_posix(), 'a', file_size, 5]},
		                               'sqlInfo':
			                               {'class':     'RotatingFileHandler',
			                                'level':     'DEBUG',
			                                'formatter': 'sqlSpecialized',
			                                'args':      [(log_dir / 'sql.log').as_posix(), 'a', file_size, 5]}}}}
	return Config.write(config_content, fp)


__all__ = ['Config', 'DefaultConfig']
