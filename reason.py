import logging.config
from time import sleep

from common import REGEX_REPLACE_SESSION, REGEX_USER_SESSION_LIMIT, REGEX_WINDOW_MENU_FORM_NAME, Application, Unit

import pywinauto as pwn
# from pywinauto import Application, application
from pywinauto.timings import Timings
from pywinauto.controls import uia_controls, win32_controls, common_controls

Timings.Fast()
logging.config.fileConfig('config2.ini')
log = logging

replace_session_regex = REGEX_REPLACE_SESSION
user_session_regex = REGEX_USER_SESSION_LIMIT
form_name_regex = REGEX_WINDOW_MENU_FORM_NAME

def reason(app):
	print(app)
	quit()
