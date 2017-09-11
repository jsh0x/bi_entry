import datetime
import logging.config
import configparser
from random import randint
from time import sleep

from transact import transact
from scrap import scrap
from reason import reason
from common import REGEX_REPLACE_SESSION, REGEX_USER_SESSION_LIMIT, REGEX_INVALID_LOGIN, Application, Unit
from _sql import MS_SQL
from _crypt import decrypt
from exceptions import *

_assorted_lengths_of_string = ('30803410313510753080335510753245107531353410',
                              '474046203600486038404260432039003960',
                              '63004620S875486038404260S875432039003960',
                              '58803900396063004620360048603840426038404620',
                              '1121327')
_adr_data, _usr_data, _pwd_data, _db_data, _key = _assorted_lengths_of_string
mssql = MS_SQL(address=decrypt(_adr_data, _key), username=decrypt(_usr_data, _key), password=decrypt(_pwd_data, _key), database=decrypt(_db_data, _key))

replace_session_regex = REGEX_REPLACE_SESSION
user_session_regex = REGEX_USER_SESSION_LIMIT
invalid_login_regex = REGEX_INVALID_LOGIN

config = configparser.ConfigParser()
logging.config.fileConfig('config2.ini')
log = logging


def main():
	sleep(randint(10, 20) / 10)
	log.info("Attempting to read 'config.ini'")
	config.read_file(open('config2.ini'))
	log.info("Starting Application")
	app = Application(config.get('Paths', 'sl_exe'))
	usr = config.get('Login', 'username')
	pwd = config.get('Login', 'password')
	active_days = [int(x) for x in config.get('Schedule', 'active_days').split(',')]
	active_hours = [int(x) for x in config.get('Schedule', 'active_hours').split(',')]
	# Switch between Reason, Scrap, and Transaction
	while True:  # Core Loop
		dt = datetime.datetime.now()
		weekday = int(dt.__format__('%w'))
		if (weekday not in active_days) or (dt.hour not in active_hours):
			continue
		if not app.logged_in:
			log.info("SyteLine not logged in, starting login procedure")
			try:
				app.win32.SignIn.wait('ready')
				while app.win32.SignIn.exists():
					app.win32.SignIn.UserLoginEdit.set_text(usr)
					app.win32.SignIn.PasswordEdit.set_text(pwd)
					if (app.win32.SignIn.UserLoginEdit.texts()[0] != usr) or (app.win32.SignIn.PasswordEdit.texts()[0] != pwd) or (not app.win32.SignIn.OKButton.exists()):
						raise ValueError()
					app.win32.SignIn.OKButton.click()
					while app.win32.Dialog.exists():
						# Get dialog info
						title = app.win32.Dialog.texts()
						buttons = {ctrl.texts()[0].strip('!@#$%^&*()_ ').replace(' ', '_').lower() + '_button': ctrl for ctrl in app.win32.Dialog.children() if ctrl.friendly_class_name() == 'Button'}
						text = [ctrl.texts()[0].capitalize() for ctrl in app.win32.Dialog.children() if ctrl.friendly_class_name() == 'Static' and ctrl.texts()[0]]
						log.debug([title, buttons, text, replace_session_regex.search(text[0]), user_session_regex.search(text[0])])
						if replace_session_regex.search(text[0]):  # Handle better in future
							if 'yes_button' in buttons:
								buttons['yes_button'].click()
						elif user_session_regex.search(text[0]):  # Handle better in future
							if 'ok_button' in buttons:
								buttons['ok_button'].click()
						elif invalid_login_regex.search(text[0]):  # Handle better in future
							if 'ok_button' in buttons:
								buttons['ok_button'].click()
								raise SyteLineLogInError('')
						else:
							raise ValueError()
			except ValueError:
				continue  # Handle better in future
			else:
				log.info(f"Successfully logged in as '{usr}'")
				app.logged_in = True
		if app.logged_in:
			result = mssql.execute("SELECT TOP 1 * FROM PyComm WHERE [Status] = 'Queued' OR [Status] = 'Reason' OR [Status] = 'Scrap' ORDER BY [Id] ASC")
			if result is None:
				log.info("No valid results, waiting...")
				sleep(10)
				continue
			unit = Unit(mssql, result)
			log.info(f"Unit object created with serial_number={unit.serial_number}'")
			if result.Status == 'Queued':
				transact(app, unit)
			elif result.Status == 'Reason':
				transact(app, unit)
			elif result.Status == 'Scrap':
				transact(app, unit)
			else:
				raise ValueError()

if __name__ == '__main__':
	main()
