import logging
from collections import namedtuple
import re
from typing import Union, Dict, Tuple, Any, NamedTuple, Optional
import sqlite3

import pymssql

log = logging.getLogger('root')


class _SQL:
	def execute(self, command: str, fetchall: Optional[bool]=None) -> Union[NamedTuple, Tuple[NamedTuple, ...]]:
		c = self._conn.cursor()
		if command.startswith('SELECT'):
			SQL_Results = namedtuple('SQL_Results', field_names=self._parse_sql_command(command))
			log.debug(f"Attempting to execute SQL command: {command}")
			c.execute(command)
			log.debug("Command successful")
			if fetchall:
				results = tuple([SQL_Results(*x) for x in c.fetchall()])
			else:
				results = SQL_Results(*c.fetchone())
			log.debug(f"Results returned: {results}")
			return results
		else:
			log.debug(f"Attempting to execute SQL command: {command}")
			c.execute(command)
			self._conn.commit()
			log.debug("Command successful")
			return None

	def _parse_sql_command(self, string: str) -> Tuple[str, ...]:
		# language=RegExp
		regex = r"^SELECT (?:TOP \d+ )?((?:\*)|(?:(?:, |,)?\[[\w ]+\],?)+) FROM (\w+)"
		# regex = r"(?:" \
		#         r"^(?:(SELECT) ((?:\*)|(?:(?: ?,)?(?:\w+.)?\[[\w ]+\](?: ?,)?)+) (FROM \w+(?: \w+)?)(?: (INNER JOIN \w+ \w+ ON \w+.\[[\w ]+\] ?(?:=|<>|>|<|>=|<=|LIKE|NOT LIKE) ?\w+.\[[\w ]+\]))*)|" \
		#         r"^(?:(INSERT) INTO (\w+)(?: (\[[\w ]+\],?))* VALUES \((?:([\w\? ]),?)+\))|" \
		#         r"^(?:(UPDATE) (\w+) SET (,?(?:\w+.)?\[[\w ]+\] ?= ?[\w\?]+,?)+)|" \
		#         r"^(?:(DELETE) FROM (\w+))" \
		#         r")" \
		#         r"(?: (WHERE (?:(?: ?,)?(?:\w+.)?\[[\w ]+\] ?(?:=|<>|>|<|>=|<=|LIKE|NOT LIKE) ?[\w\?]+(?: ?,)?)+))?" \
		#         r"(?: (ORDER BY (?:(?: ?,)?(?:\w+.)?\[[\w ]+\](?: ASC| DESC)?(?: ?,)?)+))?"
		p = re.compile(regex)
		m = p.match(string)
		columns, table_name = m.groups()
		if columns == '*':
			c = self._conn.cursor()
			c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = '%s' ORDER BY ordinal_position" % table_name)
			columns = tuple([str(x[0]).strip().replace(' ', '_') for x in c.fetchall()])
		else:
			columns = tuple([str(x).strip('[ ]').replace(' ', '_') for x in columns.split(',')])
		return columns
# TODO: Function to parse commands, for getting table name, if count, if distinct, if top #, if *, requested columns, etc.


class MS_SQL(_SQL):
	def __init__(self, address: str, username: str, password: str, database: str):
		try:
			conn = pymssql.connect(server=address, user=username, password=password, database=database, login_timeout=10)
		except Exception:
			raise ConnectionError("Connection to SQL Server failed!")
		else:
			self._conn = conn


class SQL_Lite(_SQL):
	def __init__(self, database: Union[bytes, str], detect_types: int=0):
		try:
			conn = sqlite3.connect(database=database, detect_types=detect_types)
		except Exception:
			raise ConnectionError("Connection to SQL Server failed!")
		else:
			self._conn = conn
