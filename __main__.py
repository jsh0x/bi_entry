#! python3 -W ignore
# coding=utf-8
import random
from string import ascii_letters, digits, punctuation, whitespace
from time import sleep

import pywinauto.timings
import os
from common import Application, Unit
from config import *
import processes
import logging
import datetime
from constants import SYTELINE_WINDOW_TITLE, TRANSACTION_STATUS, REASON_STATUS
from utils.tools import fix_isoweekday
from exceptions import *

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
my_name = os.environ['COMPUTERNAME']

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
'''_'''
# res = mssql.execute("""SELECT [Serial Number], Operation, Parts, Status, DateTime FROM PyComm where (Status like 'Queued%' or Status like '%Queued' or Status like '%Queued%') and Status <> 'Queued' and Status <> 'Started(Queued)' order by DateTime desc""")
# final = '\n'.join(f"{r.Serial_Number}\t{r.Operation}\t{','.join(' x '.join(str(x) for x in mssql.execute('''SELECT PartNum,Qty FROM Parts WHERE ID = %d''', int(part_id))[0]) if '-' not in part_id else ' x '.join(str(x) for x in mssql.execute('''SELECT PartNum,Qty FROM Parts WHERE PartNum = %s''', part_id)[0]) for part_id in r.Parts.split(',')) if r.Parts else ''}\t{r.Status}\t{r.DateTime}\t" for r in res)
#
# print(final)
#
# quit()
# def quick_fix():
# 	from time import sleep
# 	import numpy as np
#
# 	import pyautogui as pag
# 	import pywinauto.timings
# 	from pywinauto.controls import common_controls, uia_controls, win32_controls
# 	from constants import SYTELINE_WINDOW_TITLE
# 	from constants import WHITE
# 	from utils.tools import get_background_color
# 	serials = """1121932
# 	1127035
# 	1127047
# 	1137694
# 	1141151
# 	1144203
# 	1147406
# 	1155304
# 	1161067
# 	1301487
# 	1302153
# 	1302181
# 	1303537
# 	1304276
# 	1304629
# 	1307927
# 	1310577
# 	1315835
# 	1316784
# 	1319483
# 	1320947
# 	1326074
# 	1327436
# 	1327507
# 	1327626
# 	1328556
# 	1329539
# 	1331110
# 	1333530
# 	1342422
# 	1352666
# 	1353079
# 	6100151
# 	6101949
# 	6501082
# 	6501664
# 	6503127
# 	6503454
# 	6503603
# 	7750617
# 	7751912
# 	7758426
# 	7760219
# 	7760652
# 	7762971
# 	7763500
# 	7764195
# 	7765692
# 	7768866
# 	7769995
# 	7770126
# 	7771256
# 	7772329
# 	7774954
# 	7775986
# 	7777253
# 	7777831
# 	7780848
# 	9308825
# 	9421839
# 	9441661
# 	9457589
# 	9461628
# 	9467680
# 	9801623
# 	9803419
# 	9803645
# 	9803770
# 	9804654
# 	9807064
# 	9807228
# 	9807544
# 	9809409
# 	9809622
# 	9809798
# 	9811296
# 	9811835
# 	9812581""".splitlines()
# 	app = Application.start(application_filepath)
# 	app.log_in(username, password)  # If not logged in and within schedule
# 	wait_duration = 60  # slow speed
# 	wait_duration = 15  # normal speed
#
# 	wait_interval = 1  # slow speed
# 	wait_interval = 0.09  # normal & fast speeds
# 	prefix_dict = {'98': 'TD', '11': 'OT', '13': 'LC', '93': 'HGS', '94': 'HGM', '77': 'HGR', '65': 'HB', '61': 'HB'}
# 	for sn in serials:
# 		sn = sn.strip()
# 		app.ensure_form("Units")
# 		sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
# 		sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
# 		sl_win.send_keystrokes('{F4}')
# 		sl_win.UnitEdit.exists()
# 		sl_win.UnitEdit.wait('visible', wait_duration, wait_interval)
# 		if get_background_color(sl_win.UnitEdit) != WHITE:
# 			sl_win.send_keystrokes('{F4}')
# 			sl_win.send_keystrokes('{F5}')
# 		pfx = prefix_dict.get(sn[:2], '*')
# 		sl_win.UnitEdit.set_text(pfx+sn)
# 		sleep(0.2)
# 		sl_win.send_keystrokes('{F4}')
# 		sleep(1)
# 		sl_win.set_focus()
# 		sl_win.ServiceOrderLinesButton.click()
# 		sl_win.ServiceOrderOperationsButton.wait('visible', wait_duration, wait_interval)
# 		sleep(1)
# 		sl_win.set_focus()
# 		sl_win.ServiceOrderOperationsButton.click()
# 		sl_win.SROLinesButton.wait('visible', wait_duration, wait_interval)
# 		if sl_win.StatusEdit3.texts()[0].strip() == 'Closed':
# 			status = win32_controls.EditWrapper(sl_win.StatusEdit3.element_info)
# 			status.set_text('Open')
# 			status.click_input()
# 			pag.press('tab')
# 			pag.press('esc')
# 			save = sl_uia.SaveButton
# 			save.click()
# 		sl_uia.CancelCloseButton.click()
# 		sl_uia.CancelCloseButton.click()
# 		sl_win.UnitEdit.wait('visible', 2, 0.09)
# 		sleep(0.2)
# 		sl_win.send_keystrokes('{F4}')  # Clear Filter
# 		sleep(0.2)
# 		sl_win.send_keystrokes('{F5}')  # Clear Filter
# 		sleep(0.2)
# 		sl_win.UnitEdit.wait('visible', wait_duration, wait_interval)
# 		print(sn)
# quick_fix()
# quit()
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
					for process, status in zip((processes.reason, processes.transact), (REASON_STATUS, TRANSACTION_STATUS)):
						# units = process.get_units()
						try:
							units = Unit.from_serial_number(serial[0].SerialNumber, status)
						except NoSROError:
							for status2 in (REASON_STATUS, TRANSACTION_STATUS):
								mssql.execute("""UPDATE PyComm SET Status = %s WHERE [Serial Number] = %s AND Status = %s""", (f'No SRO({status2})', serial[0].SerialNumber, status2))  # or   """... AND Status like %s""", (f'No SRO({status2})', serial[0].SerialNumber, f'%{status2}%'))"""
							break
						except NoOpenSROError as ex:
							for status2 in (REASON_STATUS, TRANSACTION_STATUS):
								mssql.execute("""UPDATE PyComm SET Status = %s WHERE [Serial Number] = %s AND Status = %s""", (f'No Open SRO({status2})({ex.sro})', serial[0].SerialNumber, status2))
							break
						except NewUnitError:
							for status2 in (REASON_STATUS, TRANSACTION_STATUS):
								mssql.execute("""UPDATE PyComm SET Status = %s WHERE [Serial Number] = %s AND Status = %s""", (f'New Unit({status2})', serial[0].SerialNumber, status2))
							break
						else:
							if units:
								process.main(app, units)
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
