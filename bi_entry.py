#!/usr/bin/env python
# TODO: Docstrings
# language=rst
"""

"""
import datetime
import logging
import random
from random import randint
from time import sleep

from _common import *
from config import *
from exceptions import *
from processes import *
from utils import *


__author__ = "Josh Reddington"
__credits__ = ["Josh Reddington", "Dominik Walker", "Benedict Igberaese"]
__version__ = "1.3.4"
__maintainer__ = "Josh Reddington"
__status__ = "Production"

log = logging.getLogger(__name__)

def main():
	_assorted_lengths_of_string = ('30803410313510753080335510753245107531353410',
	                               '3660426037804620468050404740384034653780366030253080',
	                               '474046203600486038404260432039003960',
	                               '63004620S875486038404260S875432039003960',
	                               '58803900396063004620360048603840426038404620',
	                               '54005880Q750516045004500',
	                               '1121327')
	_adr_data, _adr_data_sl, _usr_data, _pwd_data, _db_data, _db_data_sl, _key = _assorted_lengths_of_string
	mssql = MS_SQL.legacy_encrypted_connection(_key, address=_adr_data, username=_usr_data, password=_pwd_data, database=_db_data)
	slsql = MS_SQL.legacy_encrypted_connection(_key, address=_adr_data_sl, username=_usr_data, password=_pwd_data, database=_db_data_sl)
	sleep(randint(10, 20) / 10)
	log.info("Starting Application")
	while True:  # Core Loop
		old_current_hour = current_hour
		current_weekday = int(format(datetime.datetime.now(), '%w'))
		current_hour = datetime.datetime.now().hour
		if (current_weekday not in active_days) or (current_hour not in active_hours):
			if app.logged_in:
				app.log_out()
			sleep(60)
			continue
		elif (current_weekday in active_days) and (current_hour in active_hours):
			if old_current_hour != current_hour:
				offset = mssql.execute(f"SELECT TOP 1 [Total Time] FROM [Statistics] WHERE [Version] = '{version}' ORDER BY [Total Time] DESC")
				if offset is None:
					offset = 5
				else:
					offset = (offset.Total_Time // 60) + 2
				while datetime.datetime.now().minute < offset:
					pass
				else:
					choice = random.choice(range(2, 10, 2))
					random.seed(usr)
					for i in range(choice):
						random.randint(1, 20)
					else:
						sleep(random.randint(1, 20) / (choice * 2))
					mssql.execute("UPDATE PyComm SET [Status] = 'Queued' WHERE [Status] = 'Started(Queued)'")
					mssql.execute("UPDATE PyComm SET [Status] = 'Scrap' WHERE [Status] = 'Started(Scrap)'")
					mssql.execute("UPDATE PyComm SET [Status] = 'Reason' WHERE [Status] = 'Started(Reason)'")
					sleep(5)
			if not app.logged_in:
				app.log_in(usr, pwd)
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
			if app.logged_in:
				flow = config.get('DEFAULT', 'flow')
				tbl_mod = config.get('DEFAULT', 'table')
				proc = config.get('DEFAULT', 'process')
				table = 'PyComm' if int(tbl_mod) else 'PyComm2'  # if table == 1: PyComm, else: PyComm2
				# result = mssql.execute("SELECT TOP 1 * FROM PyComm WHERE [Status] = 'Queued' OR [Status] = 'Reason' OR [Status] = 'Scrap' ORDER BY [DateTime] ASC")
				# result = mssql.execute("SELECT TOP 1 * FROM PyComm WHERE [Status] = 'Queued' ORDER BY [DateTime] ASC")
				if 'scrap' in proc.lower():
					process = 'Scrap'
					result = mssql.execute("SELECT TOP 100 * FROM PyComm WHERE [Status] = 'Scrap' ORDER BY [DateTime] ASC", fetchall=True)
				elif 'reason' in proc.lower():
					process = 'Reason'
					result = mssql.execute("SELECT TOP 1 * FROM PyComm WHERE [Status] = 'Reason' ORDER BY [DateTime] ASC")

				else:
					result = mssql.execute(f"SELECT TOP 1 * From PyComm "
					                       f"WHERE [Status] = 'Queued' "
					                       f"AND [DateTime] <= DATEADD(MINUTE, -5, GETDATE()) "
					                       f"ORDER BY [DateTime] {flow}")
					if result:
						process = result.Status
				if not result:
					log.info("No valid results, waiting...")
					sleep(10)
					continue
				try:
					log.debug(f"Current process: {process}")
					if 'queued' in process.lower() or 'reason' in process.lower():
						if 'queued' in process.lower():
							all_results = mssql.execute(f"SELECT * FROM {table} WHERE [Serial Number] = '{result.Serial_Number}' AND "
							                            f"([Status] = 'Queued' OR [Status] = 'No Open SRO(Queued)' OR [Status] = 'Skipped(Queued)')", fetchall=True)
						elif 'reason' in process.lower():
							all_results = mssql.execute(f"SELECT * FROM {table} WHERE [Serial Number] = '{result.Serial_Number}' AND "
							                            f"([Status] = 'Reason' OR [Status] = 'No Open SRO(Reason)' OR [Status] = 'Skipped(Reason)')", fetchall=True)
						counter = {'SRO': 0, 'OSRO': 0, 'Skip': 0, 'C_SRO': 0, 'C_OSRO': 0, 'C_Skip': 0}
						for res in all_results:
							if 'Custom' in res.Status:
								if 'No Open SRO' in res.Status:
									counter['C_OSRO'] += 1
								elif 'No SRO' in res.Status:
									counter['C_SRO'] += 1
								elif 'Skipped' in res.Status:
									counter['C_Skip'] += 1
							else:
								if 'No Open SRO' in res.Status:
									counter['OSRO'] += 1
								elif 'No SRO' in res.Status:
									counter['SRO'] += 1
								elif 'Skipped' in res.Status:
									counter['Skip'] += 1
						if sum(counter.values()):
							counter_key = None
							max_count = max(counter.values())
							for k, v in counter.items():
								if v == max_count:
									counter_key = k
									break
							if counter_key:
								if 'SRO' in counter_key:
									log.exception(f"No SRO's exist for serial number: {result.Serial_Number}")
									mssql.execute(f"UPDATE {table} SET [Status] = 'No Open SRO({result.Status})' WHERE [Serial Number] = '{result.Serial_Number}'")
								if 'OSRO' in counter_key:
									log.exception(f"No SRO's exist for serial number: {result.Serial_Number}")
									mssql.execute(f"UPDATE {table} SET [Status] = 'No Open SRO({result.Status})' WHERE [Serial Number] = '{result.Serial_Number}'")
								elif 'Skip' in counter_key:
									log.exception(f"Other entries with skipped status exist for serial number: {result.Serial_Number}")
									mssql.execute(f"UPDATE {table} SET [Status] = 'Skipped({result.Status})' WHERE [Serial Number] = '{result.Serial_Number}'")
								continue
						if 'queued' in process.lower():
							units = list({unit.operation: unit for unit in [Unit(mssql, slsql, x) for x in all_results]}.values())  # Removes and duplicate operations
						elif 'reason' in process.lower():
							units = [Unit(mssql, slsql, x) for x in all_results]
					else:
						units = [Unit(mssql, slsql, x) for x in result]
					log.debug(f"Unit group created: {units}")
					log.debug(f"Unit group created: {', '.join(f'{x.id}, {x.parts}, {x.operation}' for x in units)}")
					unit = units[0]
				except NoSROError as ex:
					log.exception("No SRO Error!")
					mssql.execute(f"UPDATE {table} SET [Status] = 'No SRO({result.Status})' WHERE [Serial Number] = '{result.Serial_Number}'")
					continue
				except NoOpenSROError as ex:
					log.exception("No Open SRO Error!")
					mssql.execute(f"UPDATE {table} SET [Status] = 'No Open SRO({result.Status})({ex.sro})' WHERE [Serial Number] = '{result.Serial_Number}'")
					continue
				except InvalidReasonCodeError as ex:
					log.exception("Invalid Reason Code Error!")
					mssql.execute(
							f"UPDATE {table} SET [Status] = 'Invalid Reason Code({result.Status})({ex.reason_code})' WHERE [Serial Number] = '{result.Serial_Number}' AND [Id] = {int(ex.spec_id)}")
					continue
				log.info(f"Unit object created with serial_number={unit.serial_number}'")
				script_dict = {'Queued': transact, 'Reason': reason, 'Scrap': scrap, 'Custom(Queued)': transact}
				script_dict.get(process, lambda x, y: None)(app, units)
				log.info(
						'-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------')

if __name__ == '__main__':
	main()
