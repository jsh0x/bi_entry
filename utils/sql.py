# coding=utf-8
import datetime
import decimal
import logging
import pymssql
import sqlite3
from abc import ABC, abstractmethod
from collections import namedtuple, UserString, UserDict, UserList
from typing import NamedTuple, Tuple, Union, overload

from constants import REGEX_SQL_DATE as sql_date_regex, REGEX_SQL_TIME as sql_time_regex
from utils.crypt import legacy_decrypt
from utils.tools import prepare_string

log = logging.getLogger(__name__)

SimpleValue = Union[str, int]

def sql_standardize(value):
	if isinstance(value, (str, UserString)):
		return str(value)
	elif isinstance(value, tuple):
		return tuple(sql_standardize(x) for x in value)
	elif isinstance(value, set):
		return tuple(sql_standardize(x) for x in value)
	elif isinstance(value, (list, UserList)):
		return tuple(sql_standardize(x) for x in value)
	elif isinstance(value, (dict, UserDict)):
		return {sql_standardize(k): sql_standardize(v) for k, v in value.items()}
	else:
		return value

class SQL(ABC):
	def __init__(self, *, quiet: bool, **kwargs):
		self.quiet = quiet
		self._kwargs = kwargs

	@property
	def kwargs(self):
		return self._kwargs

	@property
	@abstractmethod
	def _conn(self): raise NotImplementedError()

	@abstractmethod
	def execute(self, command, params): raise NotImplementedError()


class MSSQL(SQL):
	_type_codes = {1: str, 2: bytes, 3: int, 4: datetime.datetime, 5: decimal.Decimal}

	@staticmethod
	def _adapt_type(x):
		if type(x) is str:
			val = sql_date_regex.match(x)
			if val is not None:
				return datetime.date(int(val.group('year')), int(val.group('month')), int(val.group('day')))
			val = sql_time_regex.match(x)
			if val is not None:
				return datetime.time(int(val.group('hour')), int(val.group('minute')), int(val.group('second')), int(val.group('microsecond')))
			return prepare_string(x)
		else:
			return x

	@classmethod
	@overload
	def connect(cls, address: str, username: str, password: str, database: str, *, key: str = None, legacy_encryption: bool = False, quiet: bool = False):
		try:
			conn = pymssql.connect(server=address, user=username, password=password, database=database, login_timeout=10)
		except Exception:
			raise ConnectionError("Connection to SQL Server failed!")
		else:
			return cls(server=address, user=username, password=password, database=database, login_timeout=10, quiet=quiet)

	@classmethod
	def connect(cls, address: str, username: str, password: str, database: str, *, key: str, legacy_encryption: bool = True, quiet: bool = False):
		try:
			conn = pymssql.connect(server=legacy_decrypt(address, key), user=legacy_decrypt(username, key), password=legacy_decrypt(password, key), database=legacy_decrypt(database, key),
			                       login_timeout=10)
		except Exception:
			raise ConnectionError("Connection to SQL Server failed!")
		else:
			return cls(server=legacy_decrypt(address, key), user=legacy_decrypt(username, key), password=legacy_decrypt(password, key), database=legacy_decrypt(database, key), login_timeout=10, quiet=quiet)

	@property
	def _conn(self) -> pymssql.Connection:
		try:
			conn = pymssql.connect(**self.kwargs)
		except Exception:
			raise ConnectionError("Connection to SQL Server failed!")
		else:
			return conn

	def execute(self, command, params=None) -> Tuple[NamedTuple, ...]:
		with self._conn as conn:
			c = conn.cursor()
			params = sql_standardize(params)
			if command.upper().startswith('SELECT'):
				if not self.quiet:
					log.debug(f"Executing SQL query: '{command}'")
				c.execute(command, params)
				SQL_Results = NamedTuple('SQL_Results', [(x[0].replace(' ', '_'), self._type_codes[x[1]]) for x in c.description])
				results = tuple([SQL_Results(*[self._adapt_type(y) for y in x]) for x in c.fetchall() if x is not None])
				if not self.quiet:
					log.debug(f"SQL query successful, value(s) returned: {results}")
				return results
			elif 'DELETE' in command.upper():
				if not self.quiet:
					log.debug(f"Executing SQL transaction: '{command}'")
					log.info(f"Executing SQL transaction: '{command}'")
				c.execute(command, params)
				conn.commit()
				if not self.quiet:
					log.debug("SQL transaction successful")
					log.info("SQL transaction successful")
			else:
				if not self.quiet:
					log.debug(f"Executing SQL transaction: '{command}'")
				c.execute(command, params)
				conn.commit()
				if not self.quiet:
					log.debug("SQL transaction successful")


class SQLite(SQL):
	@classmethod
	def connect(cls, database: str, detect_types: int = 0, quiet: bool = False):
		try:
			conn = sqlite3.connect(database=database, detect_types=detect_types)
		except Exception:
			raise ConnectionError("Connection to SQLite3 Database failed!")
		else:
			return cls(database=datetime, detect_types=detect_types, quiet=quiet)

	@property
	def _conn(self) -> sqlite3.Connection:
		try:
			conn = sqlite3.connect(**self.kwargs)
		except Exception:
			raise ConnectionError("Connection to SQLite3 Database failed!")
		else:
			return conn

	def execute(self, command, params=None) -> Tuple[NamedTuple, ...]:
		with self._conn as conn:
			c = conn.cursor()
			params = sql_standardize(params)
			if command.upper().startswith('SELECT'):
				if not self.quiet:
					log.debug(f"Executing SQL query: '{command}'")
				c.execute(command, params)
				SQL_Results = namedtuple('SQL_Results', [x[0].replace(' ', '_') for x in c.description])
				results = tuple([SQL_Results(*[y for y in x]) for x in c.fetchall() if x is not None])
				if not self.quiet:
					log.debug(f"SQL query successful, value(s) returned: {results}")
				return results
			elif 'DELETE' in command.upper():
				if not self.quiet:
					log.debug(f"Executing SQL transaction: '{command}'")
					log.info(f"Executing SQL transaction: '{command}'")
				c.execute(command, params)
				conn.commit()
				if not self.quiet:
					log.debug("SQL transaction successful")
					log.info("SQL transaction successful")
			else:
				if not self.quiet:
					log.debug(f"Executing SQL transaction: '{command}'")
				c.execute(command, params)
				conn.commit()
				if not self.quiet:
					log.debug("SQL transaction successful")


__all__ = ['MSSQL', 'SQLite']
