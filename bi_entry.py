import configparser
import datetime
import logging.config
import random
from random import randint
from time import sleep
import os

from constants import SYTELINE_WINDOW_TITLE

from exceptions import *


# TODO: Get s/n and also switch between reasons and transactions for that s/n
# TODO: also update the table if there is nothing else to do with that s/n
my_name = os.environ['COMPUTERNAME']

def main():
	from transact import Transact
	from scrap import Scrap
	from reason import Reason
	from common import Application, Unit, parse_numeric_ranges
	from sql import MS_SQL
	from crypt import decrypt

	_assorted_lengths_of_string = ('30803410313510753080335510753245107531353410',
	                               '3660426037804620468050404740384034653780366030253080',
	                               '474046203600486038404260432039003960',
	                               '63004620S875486038404260S875432039003960',
	                               '58803900396063004620360048603840426038404620',
	                               '54005880Q750516045004500',
	                               '1121327')
	_adr_data, _adr_data_sl, _usr_data, _pwd_data, _db_data, _db_data_sl, _key = _assorted_lengths_of_string
	mssql = MS_SQL(address=decrypt(_adr_data, _key), username=decrypt(_usr_data, _key),
	               password=decrypt(_pwd_data, _key), database=decrypt(_db_data, _key))
	slsql = MS_SQL(address=decrypt(_adr_data_sl, _key), username=decrypt(_usr_data, _key),
	               password=decrypt(_pwd_data, _key), database=decrypt(_db_data_sl, _key))
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
	table = 'PyComm'
	config_days = parse_numeric_ranges(config.get('Schedule', 'active_days'))
	config_hours = parse_numeric_ranges(config.get('Schedule', 'active_hours'))
	total_days = set(range(7))
	total_hours = set(range(24))
	active_days = {z for y in [list(range(x[0], x[1] + 1)) for x in config_days] for z in y}
	active_hours = {z for y in [list(range(x[0], x[1] + 1)) for x in config_hours] for z in y}
	inactive_days = total_days - active_days
	inactive_hours = total_hours - active_hours
	# Switch between Reason, Scrap, and Transaction
	current_hour = datetime.datetime.now().hour
	while True:  # Core Loop
		sleep(1)
		old_current_hour = current_hour
		current_weekday = int(format(datetime.datetime.now(), '%w'))
		current_hour = datetime.datetime.now().hour
		if (current_weekday in inactive_days) or (current_hour in inactive_hours):
			if app.logged_in:
				app.log_out()
			sleep(60)
			continue
		elif (current_weekday in active_days) and (current_hour in active_hours):
			if old_current_hour != current_hour:
				version = config.get('DEFAULT', 'version')
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
				app.verify_form('Units')
			if app.logged_in:
				if 'Units' not in app.get_focused_form():
					dlg = app.win32.window(class_name="#32770")
					while dlg.exists(1, 0.09):
						dlg.send_keystrokes('{ESC}')
						dlg = app.win32.window(class_name="#32770")
					sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
					while sl_uia.CancelCloseButton.is_enabled():
						sl_uia.CancelCloseButton.click()
						dlg = app.win32.window(class_name="#32770")
						while dlg.exists(1, 0.09):
							dlg.send_keystrokes('{ESC}')
							dlg = app.win32.window(class_name="#32770")
					app.verify_form('Units')
				result = None
				proc = config.get('DEFAULT', 'process')
				if 'scrap' in proc.lower():
					process = 'Scrap'
					result = mssql.execute("SELECT TOP 100 * FROM PyComm WHERE [Status] = 'Scrap' ORDER BY [DateTime] ASC", fetchall=True)
					if result:
						process = result.Status
				else:
					reason_results = None
					queued_results = None
					serial_number = mssql.execute(f"SELECT SerialNumber FROM PuppetMaster WHERE MachineName = '{my_name}'")
					if serial_number:
						serial_number = serial_number.SerialNumber
						statuses = mssql.execute(f"SELECT DISTINCT Status FROM PyComm WHERE [Serial Number] = '{serial_number}'", fetchall=True)
						if statuses:
							statuses = [x.Status for x in statuses]
							if 'Queued' in statuses:
								queued_results = mssql.execute(f"SELECT * FROM PyComm WHERE [Status] = 'Queued' AND [Serial Number] = '{serial_number}' ORDER BY [DateTime] ASC", fetchall=True)
								process = 'Queued'
							if 'Reason' in statuses:
								reason_results = mssql.execute(f"SELECT * FROM PyComm WHERE [Status] = 'Reason' AND [Serial Number] = '{serial_number}' ORDER BY [DateTime] ASC", fetchall=True)
								process = 'Queued'
							if reason_results or queued_results:
								result = 'something'
				if not result:
					log.info("No valid results, waiting...")
					sleep(10)
					continue
				try:
					if process == 'Scrap':
						log.debug(f"Current process: {process}")
						units = [Unit(mssql, slsql, x) for x in result]
						log.debug(f"Unit group created: {units}")
						log.debug(f"Unit group created: {', '.join(f'{x.id}, {x.parts}, {x.operation}' for x in units)}")
						unit = units[0]
					else:
						if reason_results:
							result = reason_results[0]
							reason_units = [Unit(mssql, slsql, x) for x in reason_results]
						if queued_results:
							result = queued_results[0]
							queued_units = [Unit(mssql, slsql, x) for x in queued_results]
				except NoSROError as ex:
					log.exception("No SRO Error!")
					mssql.execute(f"UPDATE {table} SET [Status] = 'No SRO({result.Status})' WHERE [Serial Number] = '{result.Serial_Number}'")
					mssql.execute(f"UPDATE PuppetMaster SET SerialNumber = '' WHERE MachineName = '{my_name}'")
					continue
				except NoOpenSROError as ex:
					log.exception("No Open SRO Error!")
					mssql.execute(f"UPDATE {table} SET [Status] = 'No Open SRO({result.Status})({ex.sro})' WHERE [Serial Number] = '{result.Serial_Number}'")
					mssql.execute(f"UPDATE PuppetMaster SET SerialNumber = '' WHERE MachineName = '{my_name}'")
					continue
				except InvalidReasonCodeError as ex:
					log.exception("Invalid Reason Code Error!")
					mssql.execute(f"UPDATE {table} SET [Status] = 'Invalid Reason Code({result.Status})({ex.reason_code})' WHERE [Serial Number] = '{result.Serial_Number}' AND [Id] = {int(ex.spec_id)}")
					mssql.execute(f"UPDATE PuppetMaster SET SerialNumber = '' WHERE MachineName = '{my_name}'")
					continue
				if process == 'Scrap':
					log.info(f"Unit object created with serial_number={unit.serial_number}'")
					script_dict = {'Queued': Transact, 'Reason': Reason, 'Scrap': Scrap, 'Custom(Queued)': Transact}
					script_dict.get(process, lambda x, y: None)(app, units)
					log.info(
							'-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------')
				elif process == 'Queued':
					try:
						if reason_results:
							Reason(app, reason_units)
						if queued_results:
							Transact(app, queued_units)
					except Exception:
						pass
					finally:
						mssql.execute(f"UPDATE PuppetMaster SET SerialNumber = '' WHERE MachineName = '{my_name}'")

if __name__ == '__main__':
	main()
