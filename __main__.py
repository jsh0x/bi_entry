#! python3 -W ignore
# coding=utf-8
import random
from string import ascii_letters, digits, punctuation, whitespace
from time import sleep

import pywinauto.timings
import os
from common import Application
from config import *
from processes import transact, reason
import logging
import datetime
from constants import SYTELINE_WINDOW_TITLE
from utils.tools import fix_isoweekday

# _assorted_lengths_of_string = ('30803410313510753080335510753245107531353410', '3660426037804620468050404740384034653780366030253080',
#                                '474046203600486038404260432039003960', '63004620S875486038404260S875432039003960',
#                                '58803900396063004620360048603840426038404620', '54005880Q750516045004500', '1121327')
# _adr_data, _adr_data_sl, _usr_data, _pwd_data, _db_data, _db_data_sl, _key = _assorted_lengths_of_string
# mssql = MSSQL.legacy_encrypted_connection(_key, address=_adr_data, username=_usr_data, password=_pwd_data, database=_db_data)


# print(_check_units(mssql, 'Queued'))
fp = application_filepath
fp2 = r'C:\Windows\System32\notepad.exe'
n = 2
# pywinauto.timings.Timings.Fast()
# 1053 [255, 128, 128]
# 1059 [0, 255, 0]
colors = {}
val_list = ['10' + str(x).rjust(2, '0') for x in range(70)] + ['11' + str(x).rjust(2, '0') for x in range(17)]
rem = ['1015', '1038', '1044', '1065', '1066', '1067']
# my_name = os.environ['COMPUTERNAME']
my_name = 'MFGW10PC-1'

user_list = ['bigberae', username, 'BISync01', 'BISync02', 'BISync03']
pwd_list = ['W!nter17', password, 'N0Trans@cti0ns', 'N0Re@s0ns', 'N0Gue$$!ng']
log = logging.getLogger('root')

def temp(char: str):
	if char in whitespace:
		return '0'
	elif char in ascii_letters:
		return '1'
	elif char in digits:
		return '2'
	else:
		return '3'


def parse_text(text: str) -> str:
	mapped_text = ''.join(temp(x) for x in text)
	char = [x for x in text if x in ascii_letters]
	num = [x for x in text if x in digits]
	sym = [x for x in text if x in punctuation]
	random.shuffle(char)
	random.shuffle(num)
	random.shuffle(sym)
	retval = ''
	for i in mapped_text:
		if i == '0':
			retval += ' '
		elif i == '1':
			retval += char.pop()
		elif i == '2':
			retval += num.pop()
		elif i == '3':
			retval += sym.pop()
	return retval


def main(process):
	# with SyteLinePupperMaster(1) as pm:
	# 	for ppt in pm.children():
	# 		forms = process.starting_forms
	# 		ppt.set_input(lambda x, y: x.app.quick_open_form(*y), forms)
	# 	pm.run_process(process, ppt)
	pass


'''res = mssql.execute("""SELECT DISTINCT [Serial Number] FROM PyComm WHERE [Status] = 'Skipped(Queued)' AND [Operation] = 'QC' AND [DateTime] >= 11/01/2017""")
for sn in res:
	number = sn.Serial_Number
	results = mssql.execute("""SELECT p.Prefix FROM Prefixes p INNER JOIN Prefixes r ON r.Product=p.Product WHERE r.Prefix = %s AND r.Type = 'N' AND p.Type = 'P'""", number[:2])
	for res in results:
		if slsql.execute("""SELECT ser_num FROM serial ( NOLOCK ) WHERE ser_num = %s""", (res.Prefix + number)):
			break
	serial_number = res.Prefix + str(number)
	statuses = slsql.execute("""SELECT TOP 1
		CASE WHEN t.stat = 'C'
			THEN 'Closed'
		ELSE 'Open' END AS [SRO Line Status],
		CASE WHEN o.stat = 'C'
			THEN 'Closed'
		ELSE 'Open' END AS [SRO Operation Status]
	FROM fs_sro s
		INNER JOIN fs_sro_line t ( NOLOCK )
			ON s.sro_num = t.sro_num
		INNER JOIN fs_unit_cons c ( NOLOCK )
			ON t.ser_num = c.ser_num
		INNER JOIN fs_sro_oper o ( NOLOCK )
			ON t.sro_num = o.sro_num AND t.sro_line = o.sro_line
		LEFT JOIN fs_unit_cons c2 ( NOLOCK )
			ON c.ser_num = c2.ser_num AND c.eff_date < c2.eff_date
	WHERE c2.eff_date IS NULL AND
	      t.ser_num = %s
	ORDER BY s.open_date DESC""", serial_number)
	if statuses:
		mssql.execute("""UPDATE PyComm SET [Status] = 'Queued' WHERE [Status] = 'Skipped(Queued)' AND [Operation] = 'QC' AND [DateTime] >= 11/01/2017 AND [Serial Number] = %s""", number)
quit()'''

# TODO: Reason/Resolution notes by-line textblock reading
# THINK: Maybe TextBlock class? If so, using win32's "set_text" function and "texts" method would be ideal
# Note: from the texts() method, index 0 returns a text block, while the indices that follow return each individual line, respectively
# Example:
#       raw_text = reason_notes.texts()[1:]
#       clean_text = [line.strip() for line in raw_text if line.strip()]
#       # or just:      clean_text = [line.strip() for line in reason_notes.texts()[1:] if line.strip()]
#       # Append new lines to list 'clean_text'
#       reason_notes.set_text('\r\n'.join(line.strip() for line in clean_text if line.strip()))


if __name__ == '__main__':
	app = Application.start(application_filepath)
	log.debug("Started")
	sleep(1)
	while True:
		sleep(1)
		current_datetime = datetime.datetime.now()
		current_hour = current_datetime.hour
		current_day = fix_isoweekday(current_datetime)
		log.info(f"Current hour: {current_hour}")
		log.info(f"Current day: {current_day}")
		if app.logged_in:
			if current_day in active_days and current_hour in active_hours:  # If logged in and within schedule
				log.debug(f"DateTime: {str(current_datetime)} within active schedule of days: {active_days} and hours: {active_hours}")

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
					app.ensure_form('Units')

				serial = mssql.execute("""SELECT SerialNumber from PuppetMaster WHERE MachineName = %s""", my_name)
				if serial:
					for process in (reason, transact):
						units = process.get_units(serial[0].SerialNumber)
						if units:
							process.run(app, units)
				mssql.execute(f"UPDATE PuppetMaster SET SerialNumber = '' WHERE MachineName = '{my_name}'")
				if not serial:
					log.info("No valid results, waiting...")
					sleep(10)
					continue
			else:
				log.debug(f"DateTime: {str(current_datetime)} NOT within active schedule of days: {active_days} and hours: {active_hours}")
				log.info("Logging out...")
				app.log_out()  # If logged in and not within schedule
		else:
			if current_day in active_days and current_hour in active_hours:
				log.debug(f"DateTime: {str(current_datetime)} within active schedule of days: {active_days} and hours: {active_hours}")
				log.info("Logging in...")
				app.log_in(username, password)  # If not logged in and within schedule
			else:
				log.debug(f"DateTime: {str(current_datetime)} NOT within active schedule of days: {active_days} and hours: {active_hours}")
				sleep(10)  # If not logged in and not within schedule
