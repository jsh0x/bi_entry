import datetime
import logging.config
import configparser
from random import randint
from time import sleep
import sys
from exceptions import *

def main():
	from transact import Transact
	from scrap import scrap
	from reason import reason
	from common import REGEX_REPLACE_SESSION, REGEX_USER_SESSION_LIMIT, REGEX_INVALID_LOGIN, REGEX_PASSWORD_EXPIRE, Application, Unit
	from _sql import MS_SQL
	from _crypt import decrypt

	_assorted_lengths_of_string = ('30803410313510753080335510753245107531353410',
	                               '3660426037804620468050404740384034653780366030253080',
	                               '474046203600486038404260432039003960',
	                               '63004620S875486038404260S875432039003960',
	                               '58803900396063004620360048603840426038404620',
	                               '54005880Q750516045004500',
	                               '1121327')
	_adr_data, _adr_data_sl, _usr_data, _pwd_data, _db_data, _db_data_sl, _key = _assorted_lengths_of_string
	mssql = MS_SQL(address=decrypt(_adr_data, _key), username=decrypt(_usr_data, _key), password=decrypt(_pwd_data, _key), database=decrypt(_db_data, _key))
	slsql = MS_SQL(address=decrypt(_adr_data_sl, _key), username=decrypt(_usr_data, _key), password=decrypt(_pwd_data, _key), database=decrypt(_db_data_sl, _key))

	replace_session_regex = REGEX_REPLACE_SESSION
	user_session_regex = REGEX_USER_SESSION_LIMIT
	invalid_login_regex = REGEX_INVALID_LOGIN
	password_expire_regex = REGEX_PASSWORD_EXPIRE

	config = configparser.ConfigParser()
	logging.config.fileConfig('config.ini')
	log = logging

	sleep(randint(10, 20) / 10)
	log.info("Attempting to read 'config.ini'")
	config.read_file(open('config.ini'))
	log.info("Starting Application")
	app = Application(config.get('Paths', 'sl_exe'))
	usr = config.get('Login', 'username')
	pwd = config.get('Login', 'password')
	active_days = [int(x) for x in config.get('Schedule', 'active_days').split(',')]
	active_hours = [int(x) for x in config.get('Schedule', 'active_hours').split(',')]
	active_days = list(range(7))  # TEMP
	active_hours = list(range(24))  # TEMP
	# Switch between Reason, Scrap, and Transaction
	while True:  # Core Loop
		dt = datetime.datetime.now()
		weekday = int(dt.__format__('%w'))
		if (weekday not in active_days) or (dt.hour not in active_hours):
			continue
		if not app.logged_in:
			log.info("SyteLine not logged in, starting login procedure")
			"""try:
				app.win32.SignIn.wait('ready')
				while app.win32.SignIn.exists():
					app.win32.SignIn.UserLoginEdit.set_text(usr)
					app.win32.SignIn.PasswordEdit.set_text(pwd)
					if (app.win32.SignIn.UserLoginEdit.texts()[0] != usr) or (app.win32.SignIn.PasswordEdit.texts()[0] != pwd) or (not app.win32.SignIn.OKButton.exists()):
						raise ValueError()
					app.win32.SignIn.set_focus()
					app.win32.SignIn.OKButton.click()
					Dialog2 = app.uia.top_window()
					while Dialog2.exists():
						# Get dialog info
						Dialog = Dialog2.children()[0]
						title = Dialog.texts()
						buttons = {ctrl.texts()[0].strip('!@#$%^&*()_ ').replace(' ', '_').lower() + '_button': ctrl for ctrl in Dialog.children() if ctrl.friendly_class_name() == 'Button'}
						text = [ctrl.texts()[0].capitalize() for ctrl in Dialog.children() if ctrl.friendly_class_name() == 'Static' and ctrl.texts()[0]]
						if not text:
							break
						log.debug([title, buttons, text, replace_session_regex.search(text[0]), user_session_regex.search(text[0])])
						if replace_session_regex.search(text[0]):  # Handle better in future
							if 'yes_button' in buttons:
								Dialog.set_focus()
								buttons['yes_button'].click()
						elif password_expire_regex.search(text[0]):  # Handle better in future
							if 'ok_button' in buttons:
								Dialog.set_focus()
								buttons['ok_button'].click()
						elif user_session_regex.search(text[0]):  # Handle better in future
							if 'ok_button' in buttons:
								Dialog.set_focus()
								buttons['ok_button'].click()
						elif invalid_login_regex.search(text[0]):  # Handle better in future
							if 'ok_button' in buttons:
								Dialog.set_focus()
								buttons['ok_button'].click()
								raise SyteLineLogInError('')
						else:
							raise ValueError()
			except ValueError:
				continue  # Handle better in future
			else:
				log.info(f"Successfully logged in as '{usr}'")
				app.logged_in = True"""
			sleep(4)
			app.win32.SignIn.UserLoginEdit.set_text(usr)
			app.win32.SignIn.PasswordEdit.set_text(pwd)
			app.win32.SignIn.set_focus()
			app.win32.SignIn.OKButton.click()
			sleep(10)
			log.info(f"Successfully logged in as '{usr}'")
			app.logged_in = True
		if app.logged_in:
			# result = mssql.execute("SELECT TOP 1 * FROM PyComm WHERE [Status] = 'Queued' OR [Status] = 'Reason' OR [Status] = 'Scrap' ORDER BY [Id] ASC")
			result = mssql.execute("SELECT TOP 1 * FROM PyComm WHERE [Status] = 'Queued' ORDER BY [Id] ASC")
			# result = mssql.execute("SELECT TOP 1 * FROM PyComm WHERE [Serial Number] = '1160324'")
			if result is None:
				log.info("No valid results, waiting...")
				sleep(10)
				continue
			try:
				unit = Unit(mssql, slsql, result)
			except ValueError:
				mssql.execute(f"UPDATE PyComm SET [Status] = 'Skipped({result.Status})' WHERE [Id] = {result.Id} AND [Serial Number] = '{result.Serial_Number}'")
				continue
			log.info(f"Unit object created with serial_number={unit.serial_number}'")
			script_dict = {'Queued': Transact, 'Reason': reason, 'Scrap': scrap}
			try:
				if unit.SRO_Line_status == 'Closed':
					raise UnitClosedError(f"Unit '{unit.serial_number}' closed on SRO Lines level")
				if unit.sro_num is None:
					raise UnitClosedError(f"Unit '{unit.serial_number}' has no SROs")
				script_dict.get(result.Status, lambda x,y: None)(app, unit)
			except UnitClosedError:
				unit.skip('No Open SRO')
			# except pag.FailSafeException:
			# 	mssql.execute(f"UPDATE PyComm SET [Status] = '{result.Status}' WHERE [Id] = {result.Id} AND [Serial Number] = '{result.Serial_Number}'")
			# 	sys.exit(1)
			else:
				log.info(f"Unit: {unit.serial_number_prefix+unit.serial_number} completed")
			finally:
				log.info('-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------')

if __name__ == '__main__':
	main()
