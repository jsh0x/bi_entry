#!/usr/bin/env python
import configparser
import pathlib
from typing import Iterable

from constants import REGEX_NUMERIC_RANGES


_config = configparser.ConfigParser()
_config.read_file(open(r'C:\Users\mfgpc00\Documents\GitHub\bi_entry\config.ini'))

application_filepath = pathlib.Path(_config.get('Paths', 'sl_exe'))
version = _config.get('DEFAULT', 'version')
table = _config.get('DEFAULT', 'table')
flow = _config.get('DEFAULT', 'flow')
process_default = _config.get('DEFAULT', 'process')
username = _config.get('Login', 'username')
password = _config.get('Login', 'password')

def _numeric_ranges(x1, x2, x3) -> Iterable:
	if x3 is None:
		return range(int(x1), int(x2) + 1)
	else:
		return [int(x3)]

_config_days = REGEX_NUMERIC_RANGES.finditer(_config.get('Schedule', 'active_days'))
_config_hours = REGEX_NUMERIC_RANGES.finditer(_config.get('Schedule', 'active_hours'))
active_days = {y for x in _config_days for y in _numeric_ranges(*x.groups())}
active_hours = {y for x in _config_hours for y in _numeric_ranges(*x.groups())}

from utils import MS_SQL

_assorted_lengths_of_string = ('30803410313510753080335510753245107531353410', '3660426037804620468050404740384034653780366030253080',
'474046203600486038404260432039003960', '63004620S875486038404260S875432039003960',
'58803900396063004620360048603840426038404620', '54005880Q750516045004500', '1121327')
_adr_data, _adr_data_sl, _usr_data, _pwd_data, _db_data, _db_data_sl, _key = _assorted_lengths_of_string
mssql = MS_SQL.legacy_encrypted_connection(_key, address=_adr_data, username=_usr_data, password=_pwd_data, database=_db_data)
sl_sql = MS_SQL.legacy_encrypted_connection(_key, address=_adr_data_sl, username=_usr_data, password=_pwd_data, database=_db_data_sl)
__all__ = ['active_hours', 'active_days', 'application_filepath', 'username', 'password',
           'version', 'table', 'flow', 'process_default', 'mssql', 'sl_sql']
