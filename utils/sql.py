import logging
import decimal
import datetime
from collections import namedtuple
from typing import Tuple, NamedTuple, overload
import sqlite3
import pymssql

from constants import REGEX_SQL_TIME as sql_time_regex, REGEX_SQL_DATE as sql_date_regex
from utils.crypt import legacy_decrypt, encrypt, verify

log = logging.getLogger(__name__)

type_codes = {1: str, 2: bytes, 3: int, 4: datetime.datetime, 5: decimal.Decimal}


def adapt_type(x):
	if type(x) is str:
		val = sql_date_regex.match(x)
		if val is not None:
			return datetime.date(int(val.group('year')), int(val.group('month')), int(val.group('day')))
		val = sql_time_regex.match(x)
		if val is not None:
			return datetime.time(int(val.group('hour')), int(val.group('minute')), int(val.group('second')), int(val.group('microsecond')))
		return x
	else:
		return x


class _SQL:
	@overload
	def execute(self, command: str, fetchall: bool) -> Tuple[NamedTuple, ...]:
		...

	@overload
	def execute(self, command: str, fetchall: None=None) -> NamedTuple:
		...

	def execute(self, command, fetchall: bool=None):
		c = self._conn.cursor()
		if command.upper().startswith('SELECT'):
			if not self.quiet:
				log.debug(f"Executing SQL query: '{command}'")
			c.execute(command)
			if self.method == 'MS':
				SQL_Results = NamedTuple('SQL_Results', [(x[0].replace(' ', '_'), type_codes[x[1]]) for x in c.description])
				if fetchall:
					results = tuple([SQL_Results(*[adapt_type(y) for y in x]) for x in c.fetchall() if x is not None])
				else:
					results = c.fetchone()
					if results is not None:
						results = SQL_Results(*[adapt_type(y) for y in results])
				if not self.quiet:
					log.debug(f"SQL query successful, value(s) returned: {results}")
			else:
				SQL_Results = namedtuple('SQL_Results', [x[0].replace(' ', '_') for x in c.description])
				if fetchall:
					results = tuple([SQL_Results(*[y for y in x]) for x in c.fetchall() if x is not None])
				else:
					results = c.fetchone()
					if results is not None:
						results = SQL_Results(*[y for y in results])
				if not self.quiet:
					log.debug(f"SQL query successful, value(s) returned: {results}")
			return results
		elif 'DELETE' in command.upper():
			if not self.quiet:
				log.debug(f"Executing SQL transaction: '{command}'")
				log.info(f"Executing SQL transaction: '{command}'")
			c.execute(command)
			self._conn.commit()
			if not self.quiet:
				log.debug("SQL transaction successful")
				log.info("SQL transaction successful")
			return None
		else:
			if not self.quiet:
				log.debug(f"Executing SQL transaction: '{command}'")
			c.execute(command)
			self._conn.commit()
			if not self.quiet:
				log.debug("SQL transaction successful")
			return None


class MS_SQL(_SQL):
	def __init__(self, address: str, username: str, password: str, database: str, quiet: bool=False):
		try:
			conn = pymssql.connect(server=address, user=username, password=password, database=database, login_timeout=10)
		except Exception:
			raise ConnectionError("Connection to SQL Server failed!")
		else:
			self._conn = conn
			self.method = 'MS'
			self.quiet = quiet

	@classmethod
	def legacy_encrypted_connection(cls, key: str, address: str, username: str, password: str, database: str, quiet: bool = False):
		return cls(legacy_decrypt(address, key), legacy_decrypt(username, key), legacy_decrypt(password, key), legacy_decrypt(database, key), quiet)

	@classmethod
	def encrypted_connection(cls, address: str, username: str, password: str, database: str, quiet: bool=False):
		raise NotImplementedError()
		_address = encrypt(bytes(address, encoding='utf-8'))
		_usr = encrypt(bytes(username, encoding='utf-8'))
		_pwd = encrypt(bytes(password, encoding='utf-8'))
		_db = encrypt(bytes(database, encoding='utf-8'))
		if all(verify(_dict['_address'], _address),
		       verify(_dict['_usr'], _usr),
		       verify(_dict['_pwd'], _pwd),
		       verify(_dict['_db'], _db)):
			return cls(address, username, password, database, quiet)


class SQL_Lite(_SQL):
	def __init__(self, database: str, detect_types: int=0, quiet: bool=False):
		try:
			conn = sqlite3.connect(database=database, detect_types=detect_types)
		except Exception:
			raise ConnectionError("Connection to SQL Server failed!")
		else:
			self._conn = conn
			self.method = 'LITE'
			self.quiet = quiet


__all__ = ['SQL_Lite', 'MS_SQL']
