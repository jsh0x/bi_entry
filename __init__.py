__author__ = 'jsh0x'
__version__ = '0.9.0'

import struct
import subprocess
import configparser
from sys import version_info as version
import os
import sys
import logging
import logging.handlers


log = logging.getLogger('devLog')

#log.setLevel(logging.DEBUG)
errFormat = logging.Formatter("[%(asctime)s][%(levelname)s][%(module)s.py, line:%(lineno)s]  %(message)s", datefmt='%H:%M:%S')
infFormat = logging.Formatter("[%(asctime)s]  [%(levelname)s][%(module)s.py, line:%(lineno)s]  %(message)s", datefmt='%Y/%m/%d %H:%M:%S')
devFormat = logging.Formatter("[%(asctime)s.%(msecs)-3d]  [%(levelname)s][%(module)s.py, line:%(lineno)s]  %(message)s", datefmt='%H:%M:%S')

errh = logging.StreamHandler(sys.stderr)
errh.setLevel(logging.WARNING)
errh.setFormatter(errFormat)

infh = logging.handlers.RotatingFileHandler(os.getcwd() + '\\info.log', maxBytes=20000000, backupCount=5)  # ~20MB
infh.setLevel(logging.INFO)
infh.setFormatter(infFormat)

dbgh = logging.handlers.RotatingFileHandler(os.getcwd() + '\\dbg.log', maxBytes=50000000, backupCount=5)  # ~50MB
dbgh.setLevel(logging.DEBUG)
dbgh.setFormatter(infFormat)

devh = logging.StreamHandler(sys.stdout)
devh.setLevel(logging.DEBUG)
#devh.setFormatter(devFormat)

log.addHandler(errh)
log.addHandler(infh)
log.addHandler(dbgh)
#
#log.addHandler(devh)
log.setLevel(logging.DEBUG)



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
