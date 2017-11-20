import logging
from logging import FileHandler
import sys
import datetime
import pathlib
from typing import Dict, Any
import importlib

class MyFileHandler(FileHandler):
	def __init__(self, filename, mode='a', encoding=None, delay=False):
		self.logDirectory = pathlib.WindowsPath(filename)
		self._baseFilename = None
		super().__init__(filename, mode, encoding, delay)

	@property
	def baseFilename(self):
		dt_now = datetime.datetime.now()
		filename, month_name, year = dt_now.strftime('[%m-%d-%y]info.log,%b,%Y').split(',')
		filepath = self.logDirectory / year / month_name
		filename = filepath / filename
		if self._baseFilename != filename:
			filepath.mkdir(exist_ok=True)
			self._baseFilename = filename
		return self._baseFilename.as_posix()

	@baseFilename.setter
	def baseFilename(self, value):
		self._baseFilename = value


class MyExceptionFileHandler(FileHandler):
	def __init__(self, filename, mode='w', encoding=None, delay=False):
		self.logDirectory = pathlib.WindowsPath(filename)
		self._baseFilename = None
		super().__init__(filename, mode, encoding, delay)

	@property
	def baseFilename(self):
		filename = sys.last_type.__name__ + '_err'
		while ' ' in filename:
			filename = filename.replace(' ', '_')
		filepath = self.logDirectory / filename
		count = 0
		while filepath.with_suffix(f'{count}.log').exists():
			count += 1
		self._baseFilename = filepath.with_suffix(f'{count}.log')
		return self._baseFilename.as_posix()

	@baseFilename.setter
	def baseFilename(self, value):
		self._baseFilename = value


def initialize_logger(config: Dict[str, Any]):
	for logger_name, logger_dict in config['loggers'].items():
		logger = logging.getLogger(logger_name)
		logger.setLevel(logger_dict['level'])

		for handler_name in logger_dict['handlers']:
			handler_dict = config['handlers'][handler_name]
			formatter_name = handler_dict['formatter']
			args = handler_dict.get('args', [])
			try:
				handler_class = importlib.import_module(f"logging.handler.{handler_dict['class']}")
			except ImportError:
				handler_class = eval(handler_dict['class'])

			handler = handler_class(*args)
			handler.setLevel(handler_dict['level'])
			if hasattr(handler, 'namer'):
				handler.namer = eval(handler_dict.get('namer', 'None'))
			if hasattr(handler, 'rotator'):
				handler.rotator = eval(handler_dict.get('rotator', 'None'))

			formatter_dict = config['formatters'][formatter_name]
			fmt = formatter_dict.get('format', None)
			datefmt = formatter_dict.get('datefmt', None)
			style = formatter_dict.get('style', '%')
			formatter = logging.Formatter(fmt, datefmt, style)

			handler.setFormatter(formatter)
			logger.addHandler(handler)
