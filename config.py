#! python3 -W ignore
# coding=utf-8
from __init__ import read_config, my_directory

import importlib
import os
import logging
from logging import FileHandler, Handler, StreamHandler

config = read_config(my_directory)

version = config['Default'].get('version', '?.?.?')

application_filepath = config['Paths'].get('syteline_exe', None)

username = config['Login'].get('username', 'usr')
password = config['Login'].get('password', 'pwd')

# username = 'bigberae'  ###
# password = 'W!nter17'  ###

active_days = config['Schedule'].get('active_days', list(range(7)))
active_hours = config['Schedule'].get('active_hours', list(range(24)))

# active_days = list(range(7))
# active_hours = list(range(24))

from utils import MSSQL

_assorted_lengths_of_string = ('30803410313510753080335510753245107531353410', '3660426037804620468050404740384034653780366030253080',
                               '474046203600486038404260432039003960', '63004620S875486038404260S875432039003960',
                               '58803900396063004620360048603840426038404620', '54005880Q750516045004500', '1121327')
_adr_data, _adr_data_sl, _usr_data, _pwd_data, _db_data, _db_data_sl, _key = _assorted_lengths_of_string
mssql = MSSQL.connect(key=_key, address=_adr_data, username=_usr_data, password=_pwd_data, database=_db_data, legacy_encryption=True)
slsql = MSSQL.connect(key=_key, address=_adr_data_sl, username=_usr_data, password=_pwd_data, database=_db_data_sl, legacy_encryption=True)
__all__ = ['active_hours', 'active_days', 'application_filepath', 'username', 'password',
           'version', 'mssql', 'slsql']
