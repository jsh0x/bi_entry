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
process = _config.get('DEFAULT', 'process')
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

__all__ = ['active_hours', 'active_days', 'application_filepath', 'username', 'password',
           'version', 'table', 'flow', 'process']
