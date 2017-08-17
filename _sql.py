import logging
from typing import Union, Dict, Tuple, Any
import sqlite3
# Try importing 3rd-party modules
log = logging.getLogger('root')
try:
	missing_imports = []
	try:
		import pymssql as pysql
	except ImportError:
		missing_imports.append(('pymssql', '2.1.3'))
finally:
	if missing_imports:
		error_string = "The following modules are missing, and are required for base functionality:\n"
		for m,v in missing_imports:
			error_string += f"    {m} - {v}\n"
		raise ImportError(error_string)


def _label_columns(columns: Tuple[str], row: Tuple[Any]) -> Dict[str, Any]:
	row_dict = {}
	for col, data in zip(columns, row):
		row_dict[col] = data
	return row_dict


def get_columns_from_command(cmd: str) -> Tuple[str]:
	column_slice = (cmd.split('FROM', 1)[0]).split('[')[1:]
	columns = []
	for col in column_slice:
		columns.append(col.rsplit(']', 1)[0])
	return tuple(columns)


class SQL:
	def __init__(self, conn: Union[pysql.Connection, sqlite3.Connection]):
		self._conn = conn

	def query(self, cmd: str, fetchall=False) -> Union[Any, Dict[str, Any], Tuple[Dict[str, Any]]]:
		c = self._conn.cursor()
		try:
			log.debug(f"Attempting to execute SQL command: {cmd}")
			c.execute(cmd)
			log.debug("Command successful")
		except Exception:
			raise ConnectionError(f"Command execution failed for command:\n'{cmd}'")
		else:
			if cmd.startswith('SELECT') and ('FROM' in cmd) and ('COUNT' in cmd.split('FROM', 1)[0]):
				retval = int(c.fetchone()[0])
				log.debug(f"Results: {retval}")
				return retval
			elif fetchall:
				rows = c.fetchall()
				if cmd.startswith('SELECT') and ('*' in cmd.split('FROM', 1)[0]):
					table = cmd.split('FROM ', 1)[1]
					if ' WHERE' in table:
						table = table.rsplit(' WHERE', 1)[0]
					columns = self.columns(table=table)
				else:
					columns = get_columns_from_command(cmd)
				if len(columns) > 1:
					retval = []
					for row in rows:
						retval.append(_label_columns(columns, row))
					log.debug(f"Results: {tuple(retval)}")
					return tuple(retval)
				else:
					log.debug(f"Results: {tuple(rows)}")
					return tuple(rows)
			else:
				row = c.fetchone()
				if cmd.startswith('SELECT') and ('*' in cmd.split('FROM', 1)[0]):
					table = cmd.split('FROM ', 1)[1]
					if ' WHERE' in table:
						table = table.rsplit(' WHERE', 1)[0]
					columns = self.columns(table=table)
				else:
					columns = get_columns_from_command(cmd)
				if len(columns) > 1 and row:
					retval = _label_columns(columns, row)
					log.debug(f"Results: {retval}")
					return retval
				else:
					log.debug(f"Results: {row}")
					return row

	def modify(self, cmd: str):
		c = self._conn.cursor()
		try:
			c.execute(cmd)
		except Exception:
			raise ConnectionError(f"Command execution failed for command:\n'{cmd}'")
		else:
			self._conn.commit()

	def columns(self, table: str) -> Tuple[str]:
		c = self._conn.cursor()
		cmd = f"SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='{table}'"
		try:
			c.execute(cmd)
		except Exception:
			raise ConnectionError(f"Command execution failed for command:\n'{cmd}'")
		else:
			retval = []
			for col in c.fetchall():
				retval.append(col[3])
			return tuple(retval)

# TODO: Function to parse commands, for getting table name, if count, if distinct, if top #, if *, requested columns, etc.


class MS_SQL(SQL):
	def __init__(self, address: str, username: str, password: str, database: str):
		try:
			conn = pysql.connect(server=address, user=username, password=password, database=database, login_timeout=10)
		except Exception:
			raise ConnectionError("Connection to SQL Server failed!")
		else:
			super().__init__(conn=conn)


class SQL_Lite(SQL):
	def __init__(self, database: Union[bytes, str], detect_types: int=0):
		try:
			conn = sqlite3.connect(database=database, detect_types=detect_types)
		except Exception:
			raise ConnectionError("Connection to SQL Server failed!")
		else:
			super().__init__(conn=conn)

# c.execute("SELECT name FROM sqlite_master WHERE type='table'")
# print(c.fetchall())
