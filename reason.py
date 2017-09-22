import logging.config
from time import sleep

from common import timer, access_grid, Application, Unit, center
from constants import REGEX_ROW_NUMBER as row_number_regex, REGEX_NEGATIVE_ITEM as negative_item_regex

import pywinauto as pwn
# from pywinauto import Application, application
from pywinauto.timings import Timings
from pywinauto.controls import uia_controls, win32_controls, common_controls

Timings.Fast()
logging.config.fileConfig('config.ini')
log = logging


def reason(app):
	print(app)
	quit()
