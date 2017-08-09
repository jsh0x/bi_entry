__author__ = 'jsh0x'
__version__ = '1.0.0'

import struct
import subprocess
import configparser
from sys import version_info as version
import os
import sys
import logging
import logging.handlers
import pathlib


log = logging.getLogger('devLog')
time_log = logging.getLogger('timeLog')
ctrl_log = logging.getLogger('ctrlLog')

log_dir = pathlib.WindowsPath.cwd()/'logs'
log_dir.mkdir(exist_ok=True)
time_dir = pathlib.WindowsPath.cwd()/'time_logs'
time_dir.mkdir(exist_ok=True)
ctrl_dir = pathlib.WindowsPath.cwd()/'control_logs'
ctrl_dir.mkdir(exist_ok=True)
errFormat = logging.Formatter("[%(asctime)s][%(levelname)s][%(module)s.py, line:%(lineno)s]  %(message)s", datefmt='%H:%M:%S')
infFormat = logging.Formatter("[%(asctime)s]%(levelname)-8s %(message)s", datefmt='%d/%m/%Y %H:%M:%S')
devFormat = logging.Formatter("[%(asctime)s.%(msecs)03d] %(levelname)-5s %(module)8s:%(lineno)-5s %(message)s", datefmt='%H:%M:%S')
# devFormat = logging.Formatter("[%(asctime)s.%(msecs)-3d] [%(levelname)s] [%(process)d, %(module)s.py, line:%(lineno)s]  %(message)s", datefmt='%H:%M:%S')
consoleFormat = logging.Formatter("[%(asctime)s.%(msecs)03d] %(levelname)-5s %(module)8s:%(lineno)-5s%(message)s", datefmt='%H:%M:%S')
timeFormat = logging.Formatter("[%(asctime)s] %(message)s", datefmt='%H:%M:%S')

errh = logging.StreamHandler(sys.stderr)
errh.setLevel(logging.WARNING)
errh.setFormatter(errFormat)

infh = logging.handlers.TimedRotatingFileHandler(log_dir/'info.log', when='D', interval=7, backupCount=3)
infh.setLevel(logging.INFO)
infh.setFormatter(infFormat)

dbgh = logging.FileHandler(log_dir/'dbg.log', mode='w')
dbgh.setLevel(logging.DEBUG)
dbgh.setFormatter(devFormat)

devh = logging.StreamHandler()
devh.setLevel(logging.DEBUG)
devh.setFormatter(consoleFormat)

timeh = logging.handlers.TimedRotatingFileHandler(time_dir/'completed.log', when='D', interval=1, backupCount=9000)
timeh.setLevel(logging.INFO)
timeh.setFormatter(timeFormat)

ctrlh = logging.FileHandler(ctrl_dir/'controls.log', mode='w')
ctrlh.setLevel(logging.DEBUG)
ctrlh.setFormatter(timeFormat)

log.addHandler(errh)
log.addHandler(infh)
log.addHandler(dbgh)
log.addHandler(devh)
log.setLevel(logging.DEBUG)

time_log.addHandler(timeh)
time_log.setLevel(logging.INFO)

ctrl_log.addHandler(ctrlh)
ctrl_log.setLevel(logging.DEBUG)

bit = 8*struct.calcsize("P")
major, minor, micro = version.major, version.minor, version.micro


def find_file(name, path="C:/"):
	for root, dirs, files in os.walk(path):
		if name in files:
			return str(os.path.join(root, name)).replace('\\', '/')
	else:
		return None


def get_outdated_modules(pip_dir) -> dict:
	retval = {}
	mods = str(subprocess.Popen([pip_dir, 'list', '--format=legacy', '--outdated'], stdout=subprocess.PIPE).communicate()[0])
	mods = (mods.split("'")[1]).split('\\r\\n')
	for mod in mods:
		try:
			mod = mod.split(' ')
			name, old, new = mod[0], (mod[1].rstrip(')')).lstrip('('), mod[4]
			retval[name] = (old, new)
		except:
			continue
	return retval


def write_config():
	path = (os.path.dirname(sys.executable)).replace('\\', '/')+"/Scripts/pip3.6.exe"
	config = configparser.ConfigParser()
	module_list = ['numpy', 'setuptools', 'pywinauto', 'Pillow', 'psutil']
	for mod in get_outdated_modules(path).keys():
		if mod in module_list:
			pass  # Update it
	config['DEFAULT'] = {'printer': 'None',
	                     'min_sl_instances': '1',
	                     'max_sl_instances': '1',
	                     'multiprocess': 'False'}
	config['Paths'] = {'sl_exe': find_file('WinStudio.exe'),
	                   'pip_exe': path}
	config['Source Control'] = {'slapi_git': 'None',
	                            'psutil_git': 'None',
								'pywinauto_git': 'None'}
	with open('config.ini', 'w') as configfile:
		config.write(configfile)


#      %(sl_exe)
try:
	try:
		from exceptions import *
	except ImportError:
		raise ImportError("Missing bi_entry 'exceptions.py' module")
	try:
		from slapi import *
	except ImportError:
		pass  # TODO: Handle
	try:
		from . import sql
	except ImportError:
		pass  # TODO: Handle
except Exception:
	pass  # TODO: Handle


import forms
import controls
__all__ = []
__all__ += forms.__all__
__all__ += controls.__all__
