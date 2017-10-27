import pywinauto.timings
from pywinauto.controls import common_controls

from _common import Application, PuppetMaster, DataGrid, _check_units
from config import *
from constants import *
from utils import *
from random import shuffle, randint
from string import digits, ascii_letters, punctuation, whitespace

from time import sleep
from threading import Thread


# _assorted_lengths_of_string = ('30803410313510753080335510753245107531353410', '3660426037804620468050404740384034653780366030253080',
# '474046203600486038404260432039003960', '63004620S875486038404260S875432039003960',
# '58803900396063004620360048603840426038404620', '54005880Q750516045004500', '1121327')
# _adr_data, _adr_data_sl, _usr_data, _pwd_data, _db_data, _db_data_sl, _key = _assorted_lengths_of_string
# mssql = MS_SQL.legacy_encrypted_connection(_key, address=_adr_data, username=_usr_data, password=_pwd_data, database=_db_data)
#
# print(_check_units(mssql, 'Queued'))
# quit()
def thread_target1(app: Application, usr: str, pwd: str):
	app.quick_log_in(usr, pwd)
	sleep(1)

def open_form(app: Application, name):
	pass

def thread_target2(app: Application, value):
	while app.win32.is_process_running():
		print(app.win32.cpu_usage(value))


def thread_target3(pm: PuppetMaster, fp):
	app = pm.start(fp)
	win = app.win32.top_window()
	while True:
		win.Edit.type_keys('This is what Py do I test on you.{ENTER}')

fp = application_filepath
fp2 = r'C:\Windows\System32\notepad.exe'
n = 2
pywinauto.timings.Timings.Fast()
# 1053 [255, 128, 128]
# 1059 [0, 255, 0]
colors = {}
val_list = ['10'+str(x).rjust(2, '0') for x in range(70)] + ['11'+str(x).rjust(2, '0') for x in range(17)]
rem = ['1015', '1038', '1044', '1065', '1066', '1067']

user_list = [username, 'BISync01', 'BISync02', 'BISync03']
pwd_list = [password, 'N0Trans@cti0ns', 'N0Re@s0ns', 'N0Gue$$!ng']

def test(self, string: str):
	win = self.app.win32.top_window()
	print(self, self.app.pid, self.name, win)
	value = randint(1, 25)
	win.Edit.send_keystrokes(str(value).rjust(2, '0')+' '+string+'{ENTER}')

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
	shuffle(char)
	shuffle(num)
	shuffle(sym)
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

with PuppetMaster(4, fp2) as pm:
	p1, p2, p3, p4 = pm.children()
	val = ''
	while val != 'quit':
		val = input("Input >")
		p1.set_input(test, val)
		p2.set_input(test, val.upper())
		p3.set_input(test, val.lower())
		p4.set_input(test, parse_text(val))
quit()

with PuppetMaster(1) as pm:
	pm.optimize_screen_space()
	pm.open_forms(['Units'])
	app = pm.children()[0]

	worker = Thread(target=thread_target2, args=(app, 0.5))
	worker.setDaemon(True)
	worker.start()
	sleep(1)

	worker = Thread(target=thread_target3, args=(pm, fp2))
	worker.setDaemon(True)
	worker.start()
	sleep(1)

	sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
	sl_win.send_keystrokes('{F4}')
	print("Pressing Service Order Lines Button")
	sl_win.ServiceOrderLinesButton.click()
	sl_win.ServiceOrderOperationsButton.wait('visible', 2, 0.09)
	print("Pressing Service Order Operations Button")
	sl_win.ServiceOrderOperationsButton.click()
	sl_win.SROLinesButton.wait('visible', 2, 0.09)
	print("Opening Reasons Tab")
	common_controls.TabControlWrapper(sl_win.TabControl).select('Reasons')
	reason_grid = DataGrid.from_name(app, 'Data Grid View', ['General Reason', 'Specific Reason', 'General Resolution', 'Specific Resolution'], 6)
	gn = reason_grid['General Reason', 1]
	sn = reason_grid['Specific Reason', 1]
	go = reason_grid['General Resolution', 1]
	so = reason_grid['Specific Resolution', 1]
	print(gn, sn, go, so)
	gn = reason_grid['General Reason', 2]
	sn = reason_grid['Specific Reason', 2]
	go = reason_grid['General Resolution', 2]
	so = reason_grid['Specific Resolution', 2]
	print(gn, sn, go, so)
