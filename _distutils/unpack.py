#! python3 -W ignore
# coding=utf-8
import zipfile
import shutil
import re
from win32com.client import Dispatch
import subprocess

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

def create_shortcut(name: str, exe_path, startin, icon_path):
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

def compare_versions(v1: str, v2: str):
	v1_score = sum([int(v1.split('.')[i]) * (10 ** (2 - i)) for i in range(3)])
	v2_score = sum([int(v2.split('.')[i]) * (10 ** (2 - i)) for i in range(3)])
	if v1_score == v2_score:
		if (v1.count('.') == 3) and (v2.count('.') == 2):
			return v2
		elif (v1.count('.') == 2) and (v2.count('.') == 3):
			return v1
		elif (v1.count('.') == 3) and (v2.count('.') == 3):
			v1_score += int(v1.split('.')[3])
			v2_score += int(v2.split('.')[3])
			if v1_score > v2_score:
				return v1
			else:
				return v2
		elif (v1.count('.') == 2) and (v2.count('.') == 2):
			return v2
		else:
			raise ValueError
	elif v1_score > v2_score:
		return v1
	else:
		return v2

def unpack_it():
	prog_dir = pathlib.WindowsPath(os.environ["PROGRAMDATA"]) / 'BI_Entry'
	path = 'build/exe.win-amd64-3.6/src.zip'
	vers_dir = prog_dir / 'bin' / 'lib' / '__version__.py'

	def extract_it():
		with zipfile.ZipFile(path) as myzip:
			myzip.extractall(prog_dir.as_posix())
		create_shortcut(name='BI_Entry', exe_path=prog_dir / 'bin' / 'exe.win-amd64-3.6' / 'checker.exe', startin=prog_dir / 'bin' / 'exe.win-amd64-3.6',
		                icon_path=prog_dir / 'bin' / 'exe.win-amd64-3.6' / 'bi_entry.ico')

	def get_version():
		with zipfile.ZipFile(path) as myzip:
			with myzip.open('bin/lib/__version__.py') as myfile:
				_vers = myfile.read()
			for line in _vers.splitlines():
				if b'full_version = ' in line:
					full_v = re.search(r"'(.*)'", line.decode('utf-8')).group().strip("'")
				elif b'short_version = ' in line:
					short_v = re.search(r"'(.*)'", line.decode('utf-8')).group().strip("'")
				elif b'release = ' in line:
					if b'True' in line:
						return short_v
					else:
						return full_v
				

	def update_it():
		bin_dir = prog_dir / 'bin'
		config_file = prog_dir / 'config.json'
		try:
			if bin_dir.exists():
				bin_dir.rename(prog_dir / 'bin_OLD')
			if config_file.exists():
				os.remove(config_file.as_posix())  # TODO: Handle overwriting old configs, ie maintaining data continuity where relevant
			if any([bin_dir.exists(), config_file.exists()]):
				raise FileExistsError()
			extract_it()
			if not bin_dir.exists():
				raise FileNotFoundError()
			try:
				DefaultConfig()
				shutil.rmtree(bin_dir.with_name('bin_OLD').as_posix())
			except Exception:
				pass
		except Exception as ex:
			bin_dir = prog_dir / 'bin_OLD'
			if bin_dir.exists():
				bin_dir.rename(prog_dir / 'bin')
			raise ex

	my_vers = get_version()

	if vers_dir.exists():
		match = None
		vers = vers_dir.read_text()
		for line in vers.splitlines():
			if 'full_version = ' in line:
				full_v = re.search(r"'(.*)'", line).group().strip("'")
			elif 'short_version = ' in line:
				short_v = re.search(r"'(.*)'", line).group().strip("'")
			elif 'release = ' in line:
				if 'True' in line:
					match = short_v
				else:
					match = full_v
		if compare_versions(match, my_vers) != match:
			update_it()
	elif prog_dir.exists():
		update_it()
	else:
		extract_it()
	startin = prog_dir / 'bin'
	os.chdir(startin.as_posix())
	subprocess.run((prog_dir / 'bin' / 'exe.win-amd64-3.6' / 'bi_entry.exe').relative_to(pathlib.Path.cwd()).as_posix())

if __name__ == '__main__':
	unpack_it()
