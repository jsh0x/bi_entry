import os
import threading
import pathlib
from collections import defaultdict
import logging, logging.config
from secrets import choice
from typing import Union, Iterable, Dict, Any, Tuple, List, Optional
from time import sleep
from string import ascii_lowercase
from concurrent.futures import ThreadPoolExecutor

import psutil
import win32gui
import win32api
import win32con
import win32process
from PIL import ImageGrab
import numpy as np
import pywinauto as pwn
from pywinauto import mouse, keyboard as kbd, clipboard as clp
from pywinauto.clipboard import win32clipboard
import pyautogui as pag

from exceptions import *
from types_ import Coordinates
from computer_vision import CV_Config
from _sql import MS_SQL
from _crypt import decrypt
from bi_entry import Unit, timer

# Initial variables
screen_width = win32api.GetSystemMetrics(0)
screen_height = win32api.GetSystemMetrics(1)
logging.config.fileConfig("config.ini")
log = logging.getLogger('root')

file_list = os.listdir(os.getcwd())
if 'dev.key' in file_list:
	dev_mode = True
else:
	dev_mode = False

_assorted_lengths_of_string = ('30803410313510753080335510753245107531353410',
                              '474046203600486038404260432039003960',
                              '63004620S875486038404260S875432039003960',
                              '58803900396063004620360048603840426038404620',
                              '1121327')
_adr_data, _usr_data, _pwd_data, _db_data, _key = _assorted_lengths_of_string
mssql = MS_SQL(address=decrypt(_adr_data, _key), username=decrypt(_usr_data, _key), password=decrypt(_pwd_data, _key), database=decrypt(_db_data, _key))

def is_running(filename: str, exclude: Optional[Union[int, Iterable[int]]]=None) -> bool:
	# processes = win32process.EnumProcesses()    # get PID list
	# for pid in processes:
	# 	try:
	# 		if exclude is not None and ((type(exclude) is int and exclude == pid) or (pid in exclude)):
	# 			continue
	# 		handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid)
	# 		exe = win32process.GetModuleFileNameEx(handle, 0)
	# 		if exe.lower() == filename.lower():
	# 			return True
	# 	except:
	# 		pass
	# return False
	for proc in psutil.process_iter():
		try:
			if exclude is not None and ((isinstance(exclude, int) and proc.pid == exclude) or proc.pid in exclude):
				continue
			if proc.exe().lower() == filename.lower():
				return True
		except (psutil.NoSuchProcess, psutil.AccessDenied):
			pass
	return False


def process_pid(filename: str, exclude: Optional[Union[int, Iterable[int]]]=None) -> int:
	for proc in psutil.process_iter():
		try:
			if exclude is not None and ((isinstance(exclude, int) and proc.pid == exclude) or proc.pid in exclude):
				continue
			if proc.exe().lower() == filename.lower():
				return proc.pid
		except psutil.NoSuchProcess:
			pass
	return None


class StoppableThread(threading.Thread):
	"""Thread class with a stop() method. The thread itself has to check
	regularly for the stopped() condition."""

	def __init__(self, target: callable, args: Tuple=None):
		if not args:
			super().__init__(target=target)
		else:
			super().__init__(target=target, args=args)
		self._stop_event = threading.Event()

	def stop(self):
		self._stop_event.set()

	def stopped(self):
		return self._stop_event.is_set()


def blocker(win: pwn.WindowSpecification):
	while True:
		if win.exists():
			# After esc repeat last action?
			pag.press('esc')



def moveTo(x: int, y: int):
	mouse.move((x, y))


def moveRel(xOffset: int=None, yOffset: int=None):
	x,y = pag.position()
	if xOffset:
		x += xOffset
	if yOffset:
		y += yOffset
	mouse.move((x, y))


def enumerate_screens() -> Dict[int, Coordinates]:
	screen_width = win32api.GetSystemMetrics(0)
	screen_height = win32api.GetSystemMetrics(1)
	screens = {1: Coordinates(left=0, top=0, right=screen_width-1, bottom=screen_height-1)}
	moveTo(screen_width-1, np.floor_divide(screen_height, 2))
	new_pos = 0
	cur_pos = pag.position()
	count = 0
	while new_pos != cur_pos and count < 20:
		cur_pos = pag.position()
		moveRel(xOffset=np.floor_divide(screen_width, 2))
		new_pos = pag.position()
		moveRel(yOffset=np.multiply(screen_height, 2))
		limit = pag.position()[1]
		moveTo(*new_pos)
		moveRel(xOffset=np.floor_divide(screen_width, 2)-2)
		rec_pos = pag.position()
		count += 1
		result = rec_pos[0]+1, limit+1
		i = len(screens.keys()) + 1
		if result[0] != screen_width and new_pos != cur_pos:
			if screen_height-10 < limit < screen_height+10:
				limit = screen_height-1
			screens[i] = Coordinates(left=screens[i-1].right+1, top=0, right=rec_pos[0], bottom=limit)
	return screens


def screenshot():
	kbd.SendKeys('{PRTSC}')
	sleep(0.05)
	im = ImageGrab.grabclipboard()
	clp.EmptyClipboard()
	return im


class Application(psutil.Process):
	def __init__(self, fp: Union[str, pathlib.Path], exclude: Optional[Union[int, Iterable[int]]]=None):
		if type(fp) is pathlib.Path:
			fp = str(fp)
		if is_running(fp, exclude):
			super().__init__(process_pid(fp, exclude))
		else:
			super().__init__(psutil.Popen(fp).pid)
		self.nice(psutil.HIGH_PRIORITY_CLASS)
		self.app_win32 = pwn.Application(backend='win32').connect(process=self.pid)
		self.app_uia = pwn.Application(backend='uia').connect(process=self.pid)
		self._notification = self.app_win32['Infor ERP SL']
		self._error = self.app_win32['Error']
		self._user = None
		self.logged_in = False
		self._blocker = None
		self.popup_blocker_activated = False
		self._win = self.app_win32.window(title_re='Infor ERP SL (EM)*')
		self._win2 = self.app_uia.window(title_re='Infor ERP SL (EM)*', auto_id="WinStudioMainWindow", control_type="Window")
		self._all_win = {'win32': self._win, 'uia': self._win2}  # Get rid of eventually

	def log_in(self, usr: str=None, pwd: str=None):
		if pwd is None:
			raise ValueError()
		if usr is None:
			if self._user is not None:
				usr = self._user
			else:
				raise ValueError()
		else:
			self._user = usr
		login_win = self.app_win32['Sign In']
		login_win.set_focus()
		login_win.Edit3.SetEditText(usr)
		login_win.Edit2.SetEditText(pwd)
		login_win.OKButton.Click()
		if self._error.exists():
			message = self._error.Static2.texts()[0]
			if ('count limit' in message) and ('exceeded' in message):
				self._error.OKButton.Click()
		while self._notification.exists():
			try:
				message2 = self._notification.Static2.texts()[0]
				if (f"session for user '{usr}'" in message2) and ('already exists' in message2):
					self._notification['&YesButton'].Click()
				elif ('Exception initializing form' in message2) and ('executable file vbc.exe cannot be found' in message2):
					self._notification.OKButton.Click()
					raise SyteLineFormContainerError("SyteLine window's form container is corrupt/non-existent")
				sleep(1)
			except Exception:
				break
		CV_Config.__init__(self, self._win)
		self.logged_in = True

	def log_out(self, force_quit=True):
		if force_quit:
			self._win2.child_window(best_match='Sign OutMenuItem').select()
		else:
			# Close out each individual open form properly
			pass
		self.logged_in = False

	def move_and_resize(self, left: int, top: int, right: int, bottom: int):
		self._hwnd = self._win.handle
		# hwnd = win32gui.GetForegroundWindow()
		coord = Coordinates(left=left, top=top, right=right, bottom=bottom)
		win32gui.MoveWindow(self._hwnd, int(coord.left)-7, coord.top, coord.width, coord.height, True)

	def open_form(self, name: str, alias: Optional[str]=None):
		self._win.send_keystrokes('^o')
		# pag.hotkey('ctrl', 'o')
		# win = self._win.child_window(title='Select Form')
		self._win.send_keystrokes('%c')
		# pag.hotkey('alt', 'c')
		# pag.typewrite(name)
		self._win.send_keystrokes(name)
		self._win.send_keystrokes('%f')
		# pag.hotkey('alt', 'f')
		self._win.send_keystrokes('{TAB}')
		self._win.send_keystrokes('{TAB}')
		self._win.send_keystrokes('{TAB}')
		self._win.send_keystrokes('{TAB}')
		self._win.send_keystrokes('{TAB}')
		self._win.send_keystrokes('{TAB}')
		self._win.send_keystrokes('{SPACE}')
		# pag.press('tab', 6)###
		# pag.press('space')###
		lb = self._win.child_window(auto_id='formsListView')
		# lb.click_input()
		# pag.press([name[0], 'up'])
		# selection = lb.get_selection()[0]
		# if selection.name != name:
		# 	start = selection.name
		# 	current = None
		# 	limit = 10
		# 	count = 0
		# 	while current != start and count < limit:
		# 		count += 1
		# 		pag.press('down')
		# 		selection = lb.get_selection()[0]
		# 		if selection.name == name:
		# 			break
		# 		current = selection.name
		# 	else:
		# 		raise ValueError(f"Could not find form '{name}'")
		self._win.send_keystrokes('{DOWN}')
		self._win.send_keystrokes('{ENTER}')
		# pag.press('down')###
		# pag.press('enter')
		if alias:
			name = alias
		self._visible_form = name
		# CV_Config.load_config(self, name)

	def find_value_in_collection(self, collection: str, property: str, value, case_sensitive=False):
		pag.hotkey('alt', 'e')
		pag.press('v')
		find_window = self.app_win32['Find']
		find = find_window['Find:Edit']
		clct = find_window['In Collection:Edit']
		ppty = find_window['In Property:Edit']
		ok_button = find_window['&OKButton']
		clct.click()
		pag.hotkey('alt', 'down')
		lb = find_window['In CollectionListBox']
		lb.select(collection)
		ppty.click()
		pag.hotkey('alt', 'down')
		lb = find_window['In PropertyListBox']
		lb.select(property)
		find.set_text(str(value))
		if case_sensitive:
			kbd.SendKeys('%a')
		ok_button.click()

	def popup_blocker(self, state: bool):
		if self.popup_blocker_activated == state:
			raise ValueError()
		self.popup_blocker_activated = state
		if state:
			popup = self.app_win32['Dialog']
			self._blocker = StoppableThread(target=blocker, args=(popup,))
			self._blocker.start()
		else:
			self._blocker.stop()


class PuppetMaster:
	_children = set()
	pids = defaultdict(list)

	def __init__(self, fp: Optional[Union[str, pathlib.Path]]=None):
		if fp is not None:
			self.start(fp)

	def start(self, fp: Union[str, pathlib.Path]) -> Application:
		name = ''.join(choice(ascii_lowercase) for i in range(4))
		while name in self._children:
			name = ''.join(choice(ascii_lowercase) for i in range(4))
		self.__setattr__(name, Application(fp, exclude=list(self.pids.values())))
		self.pids[fp].append(self.__getattribute__(name).pid)
		self._children.add(name)
		return self.__getattribute__(name)

	def children(self):
		return [self.__getattribute__(ch) for ch in self._children]

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		procs = self.children()
		for p in procs:
			# print(p)
			p.terminate()
		gone, still_alive = psutil.wait_procs(procs, timeout=3)
		for p in still_alive:
			# print(p)
			p.kill()

def transaction(app):
	app.open_form('Units', 'frm_Units')
	unit_data = mssql.execute(f"SELECT TOP 1 * FROM PyComm WHERE [Status] = 'Queued' ORDER BY [DateTime] DESC")
	while unit_data is None:
		sleep(1)
		unit_data = mssql.execute(f"SELECT TOP 1 * FROM PyComm WHERE [Status] = 'Queued' ORDER BY [DateTime] DESC")
	timer.start()
	unit = Unit(unit_data)
	sleep(3)
	# app.frm_Units.txt_unit.input(unit.serial_number_prefix + unit.serial_number)
	app._win['Unit:Edit'].send_keystrokes(unit.serial_number_prefix + unit.serial_number)
	sleep(1)
	app._win.send_keystrokes('{F4}')
	# pag.press('f4')
	sleep(1)
	# app.frm_Units.btn_svc_order_lines.click()
	app._win['Service Order Lines'].click()
	sleep(4)
	if app.frm_SRO_Lines.txt_status.text() == 'Closed':
		raise ValueError()
	app._win['Service Order Operations'].click()
	# app.frm_SRO_Lines.btn_sro_oprtns.click()
	sleep(4)
	if app.frm_SRO_Operations.txt_status.text() == 'Closed':
		raise ValueError()
	# app.frm_SRO_Operations.btn_sro_transactions.click()
	app._win['SRO Transactions'].click()
	print(timer.stop())

def scrap(app):
	app.open_form('Units', 'frm_Units')
	unit_data = mssql.execute(f"SELECT TOP 1 * FROM PyComm WHERE [Status] = 'Queued' ORDER BY [DateTime] ASC")
	while unit_data is None:
		sleep(1)
		unit_data = mssql.execute(f"SELECT TOP 1 * FROM PyComm WHERE [Status] = 'Queued' ORDER BY [DateTime] ASC")
	timer.start()
	unit = Unit(unit_data)
	sleep(3)
	# app.frm_Units.txt_unit.input(unit.serial_number_prefix + unit.serial_number)
	app._win['Unit:Edit'].send_keystrokes(unit.serial_number_prefix + unit.serial_number)
	sleep(1)
	app._win.send_keystrokes('{F4}')
	# pag.press('f4')
	sleep(1)
	# app.frm_Units.btn_svc_order_lines.click()
	app._win['Service Order Lines'].click()
	sleep(4)
	if app.frm_SRO_Lines.txt_status.text() == 'Closed':
		raise ValueError()
	app._win['Service Order Operations'].click()
	# app.frm_SRO_Lines.btn_sro_oprtns.click()
	sleep(4)
	if app.frm_SRO_Operations.txt_status.text() == 'Closed':
		raise ValueError()
	# app.frm_SRO_Operations.btn_sro_transactions.click()
	app._win['SRO Transactions'].click()
	print(timer.stop())

with PuppetMaster() as ppt:
	fp = 'C:/Users/mfgpc00/AppData/Local/Apps/2.0/QQC2A2CQ.YNL/K5YT3MK7.VDY/sl8...ient_002c66e0bc74a4c9_0008.0003_1fdd36ef61625f38/WinStudio.exe'
	areas = ((0, 0, 960, 1047), (950, 0, 1920, 1047))
	targets = (transaction, scrap)
	app1 = ppt.start(fp)
	app1.log_in('jredding', 'JRJul17!')
	app1.move_and_resize(*areas[0])
	app1.load_config('Transaction')
	app2 = ppt.start(fp)
	app2.log_in('BISync03', 'N0Gue$$!ng')
	app2.move_and_resize(*areas[1])
	app2.load_config('Transaction')
	with ThreadPoolExecutor(max_workers=2) as e:
		e.submit(transaction, app1)
		e.submit(scrap, app2)
