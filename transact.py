import re
import logging, logging.config
from time import sleep

from common import REGEX_REPLACE_SESSION, REGEX_USER_SESSION_LIMIT, REGEX_WINDOW_MENU_FORM_NAME

import pywinauto as pwn
from pywinauto import Application, application
from pywinauto.timings import Timings
from pywinauto.controls import uia_controls, win32_controls, common_controls

Timings.Fast()
logging.config.fileConfig(r'C:\Users\mfgpc00\Documents\GitHub\bi_entry\config.ini')
log = logging.getLogger('root')

replace_session_regex = REGEX_REPLACE_SESSION
user_session_regex = REGEX_USER_SESSION_LIMIT
form_name_regex = REGEX_WINDOW_MENU_FORM_NAME
usr = 'jredding'
pwd = 'JRJul17!'


def main(app: Application):
	if app.process is None:
		app.start(r"C:\Users\mfgpc00\AppData\Local\Apps\2.0\QQC2A2CQ.YNL\K5YT3MK7.VDY\sl8...ient_002c66e0bc74a4c9_0008.0003_1fdd36ef61625f38\WinStudio.exe")
	if not app.logged_in or True:
		app.SignIn.wait('ready')
		while app.SignIn.exists():
			app.SignIn.UserLoginEdit.set_text(usr)
			app.SignIn.PasswordEdit.set_text(pwd)
			if (app.SignIn.UserLoginEdit.texts()[0] != usr) or (app.SignIn.PasswordEdit.texts()[0] != pwd) or (not app.SignIn.OKButton.exists()):
				raise ValueError()
			app.SignIn.OKButton.click()
			while app.Dialog.exists():
				# Get dialog info
				title = app.Dialog.texts()
				buttons = {ctrl.texts()[0].strip('!@#$%^&*()_ ').replace(' ', '_').lower()+'_button': ctrl for ctrl in app.Dialog.children() if ctrl.friendly_class_name() == 'Button'}
				text = [ctrl.texts()[0].capitalize() for ctrl in app.Dialog.children() if ctrl.friendly_class_name() == 'Static' and ctrl.texts()[0]]
				log.debug([title, buttons, text, replace_session_regex.search(text[0]), user_session_regex.search(text[0])])
				if replace_session_regex.search(text[0]):  # Handle better in future
					if 'yes_button' in buttons:
						buttons['yes_button'].click()
				elif user_session_regex.search(text[0]):  # Handle better in future
					if 'ok_button' in buttons:
						buttons['ok_button'].click()
				else:
					raise ValueError()
	log.debug([app.InforSL.exists(), app.InforSL.is_active(), app.InforSL.is_enabled(), app.InforSL.is_visible()])

	app2 = Application(backend='uia').connect(process=app.process)
	sl_win = app.window(title_re='Infor ERP SL (EM)*')
	sl_uia = app2.window(title_re='Infor ERP SL (EM)*')
	# while sl_win.exists():
	if sl_win.exists():
		log.debug([x.texts()[0] for x in sl_uia.WindowMenu.items()])
		if sl_uia.WindowMenu.control_count() > 3:  # If forms are already open
			forms = {item.texts()[0]: item for item in sl_uia.WindowMenu.items() if (item.texts()[0].lower() != 'cascade') and (item.texts()[0].lower() != 'tile') and (item.texts()[0].lower() != 'close all')}
		for i,form in enumerate(['Miscellaneous Issue', 'Units', 'Serial Numbers']):
			sl_win.send_keystrokes('^o')
			app.SelectForm.AllContainingEdit.set_text(form)
			app.SelectForm.FilterButton.click()
			common_controls.ListViewWrapper(app.SelectForm.ListView).item(form).click()
			app.SelectForm.OKButton.click()
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
