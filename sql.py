import logging.config
import re
import decimal
import datetime
from typing import Tuple, NamedTuple, overload
# import sqlite3

import pymssql

from constants import REGEX_SQL_TIME as sql_time_regex, REGEX_SQL_DATE as sql_date_regex


logging.config.fileConfig("config.ini")
log = logging

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
			log.debug(f"Executing SQL query: '{command}'")
			c.execute(command)
			SQL_Results = NamedTuple('SQL_Results', [(x[0].replace(' ', '_'), type_codes[x[1]]) for x in c.description])
			if fetchall:
				results = tuple([SQL_Results(*[adapt_type(y) for y in x]) for x in c.fetchall() if x is not None])
			else:
				results = c.fetchone()
				if results is not None:
					results = SQL_Results(*[adapt_type(y) for y in results])
			log.debug(f"SQL query successful, value(s) returned: {results}")
			return results
		else:
			log.debug(f"Executing SQL transaction: '{command}'")
			c.execute(command)
			self._conn.commit()
			log.debug("SQL transaction successful")
			return None


class MS_SQL(_SQL):
	def __init__(self, address: str, username: str, password: str, database: str):
		try:
			conn = pymssql.connect(server=address, user=username, password=password, database=database, login_timeout=10)
		except Exception:
			raise ConnectionError("Connection to SQL Server failed!")
		else:
			self._conn = conn


# class SQL_Lite(_SQL):
# 	def __init__(self, database: Union[bytes, str], detect_types: int=0):
# 		try:
# 			conn = sqlite3.connect(database=database, detect_types=detect_types)
# 		except Exception:
# 			raise ConnectionError("Connection to SQL Server failed!")
# 		else:
# 			self._conn = conn
