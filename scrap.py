import logging.config
from time import sleep

from common import REGEX_REPLACE_SESSION, REGEX_USER_SESSION_LIMIT, REGEX_WINDOW_MENU_FORM_NAME, Application

import pywinauto as pwn
# from pywinauto import Application, application
from pywinauto.timings import Timings
from pywinauto.controls import uia_controls, win32_controls, common_controls

Timings.Fast()
logging.config.fileConfig('config.ini')
log = logging

replace_session_regex = REGEX_REPLACE_SESSION
user_session_regex = REGEX_USER_SESSION_LIMIT
form_name_regex = REGEX_WINDOW_MENU_FORM_NAME


def scrap(app: Application):
	sl_win = app.win32.window(title_re='Infor ERP SL (EM)*')
	sl_uia = app.uia.window(title_re='Infor ERP SL (EM)*')
	# while sl_win.exists():
	if sl_win.exists():
		log.debug([x.texts()[0] for x in sl_uia.WindowMenu.items()])
		if sl_uia.WindowMenu.control_count() > 3:  # If forms are already open
			forms = {item.texts()[0]: item for item in sl_uia.WindowMenu.items() if (item.texts()[0].lower() != 'cascade') and (item.texts()[0].lower() != 'tile') and (item.texts()[0].lower() != 'close all')}
		for i,form in enumerate(['Miscellaneous Issue', 'Units', 'Serial Numbers']):
			sl_win.send_keystrokes('^o')
			app.win32.SelectForm.AllContainingEdit.set_text(form)
			app.win32.SelectForm.FilterButton.click()
			common_controls.ListViewWrapper(app.win32.SelectForm.ListView).item(form).click()
			app.win32.SelectForm.OKButton.click()
			sleep(4)
		for item in sl_uia.WindowMenu.items():
			print(item.get_properties())
			for item2 in item.children():
				print(item2.get_properties())
		quit()
		if sl_uia.WindowMenu.control_count() > 3:  # If forms are already open
			forms = {form_name_regex.search(item.texts()[0]).group(1): item for item in sl_uia.WindowMenu.items() if (item.texts()[0].lower() != 'cascade') and (item.texts()[0].lower() != 'tile') and (item.texts()[0].lower() != 'close all')}
		sleep(4)
	quit()
if __name__ == '__main__':
	app = pwn.Application()
	try:
		main(app)
	finally:
		app.kill()
