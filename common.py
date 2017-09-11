import re
import pathlib
import datetime
import logging.config
from random import choice
from string import ascii_lowercase
from collections import defaultdict
from typing import NamedTuple, Union, Tuple, Iterator, Optional, Iterable

import psutil
import pywinauto as pwn

from _sql import MS_SQL

logging.config.fileConfig('config2.ini')
log = logging

# - - - - - - - - - - - - - - - - - - -  CLASSES  - - - - - - - - - - - - - - - - - - - -
class Part:
	def __init__(self, sql: MS_SQL, part_number: str, quantity: int=1):
		self.part_number = part_number
		_data = sql.execute(f"SELECT [Qty],[DispName],[Location],[PartName] FROM Parts WHERE [PartNum] = '{self.part_number}'")
		self.quantity = quantity * _data.Qty
		self.display_name = _data.DispName
		self.part_name = _data.PartName
		self.location = _data.Location

	def __repr__(self):
		return f"<Part object; {self.part_number}x{self.quantity}>"

	def __str__(self):
		return f"{self.display_name}({self.part_number}) x {self.quantity}"


class Unit:
	def __init__(self, sql: MS_SQL, args: NamedTuple):
		className = self.__class__.__name__
		self._mssql = sql
		self.id, self.serial_number, self.build, self.suffix, self.operation, self.operator, \
		self.parts, self.datetime, self.notes, _status = args
		self._serial_number_prefix = self._product = self._whole_build = self._operator_initials = None
		log.debug(f"Attribute id={self.id}")
		log.debug(f"Attribute serial_number='{self.serial_number}'")
		log.debug(f"Attribute build='{self.build}'")
		log.debug(f"Attribute suffix='{self.suffix}'")
		log.debug(f"Attribute operation='{self.operation}'")
		log.debug(f"Attribute operator='{self.operator}'")
		log.debug(f"Attribute notes='{self.notes}'")
		log.debug(f"Property serial_number_prefix='{self.serial_number_prefix}'")
		log.debug(f"Property parts='{self.parts}'")
		log.debug(f"Property datetime='{self.datetime}'")
		log.debug(f"Property product='{self.product}'")
		log.debug(f"Property whole_build='{self.whole_build}'")
		log.debug(f"Property operator_initials='{self.operator_initials}'")

	@property
	def serial_number_prefix(self) -> Union[str, Tuple[str, str]]:
		try:
			if self._serial_number_prefix is None:
				value = self._mssql.execute(f"SELECT p.[Prefix] FROM Prefixes p INNER JOIN Prefixes r ON r.[Product]=p.[Product] WHERE r.[Prefix] = '{self.serial_number[:2]}' AND r.[Type] = 'N' AND p.[Type] = 'P'")[0]
			else:
				value = self._serial_number_prefix
		except Exception as ex:
			print(ex, self.serial_number)
		except (ValueError, KeyError, IndexError):
			value = None
		finally:
			return value

	@serial_number_prefix.setter
	def serial_number_prefix(self, value: str):
		if type(self.serial_number_prefix) is tuple and value in self.serial_number_prefix:
			self._serial_number_prefix = value
		else:
			self._serial_number_prefix = None

	@property
	def parts(self) -> Iterator[Part]:
		return self._parts

	@parts.setter
	def parts(self, value):
		if value:
			value = value.split(',')
			if value != ['']:
				self._parts = [Part(self._mssql, x) for x in value]
		else:
			self._parts = None

	@property
	def datetime(self) -> datetime.datetime:
		return self._datetime

	@datetime.setter
	def datetime(self, value: str):
		if type(value) is str:
			self._datetime = datetime.datetime.strptime(value, "%m/%d/%Y %I:%M:%S %p")
		else:
			self._datetime = value

	@property
	def whole_build(self):
		if self._whole_build is None:
			data = self._mssql.execute(f"SELECT [ItemNumber],[Carrier],[Suffix] FROM UnitData WHERE [SerialNumber] = '{self.serial_number}'")
			if not data:
				raise ValueError
			item, carrier, sfx = data
			if carrier == 'None':
				build = item
			else:
				if sfx == 'Direct':
					if not (item.endswith('S') or item.endswith('V')):
						build = f"{item}{carrier[0].upper()}"
					else:
						build = item
				else:
					start, end = item.rsplit('-', 1)
					if not (start.endswith('S') or start.endswith('V')):
						build = f"{start}{carrier[0].upper()}-{end}"
					else:
						build = f"{start}-{end}"
			self._whole_build = build
		return self._whole_build

	@whole_build.setter
	def whole_build(self, value):
		self._whole_build = value

	@property
	def operator_initials(self):
		if self._operator_initials is None:
			first, last = self._mssql.execute(f"SELECT [FirstName],[LastName] FROM Users WHERE [Username] = '{self.operator}'")
			self._operator_initials = first.strip()[0].upper() + last.strip()[0].upper()
		return self._operator_initials

	@operator_initials.setter
	def operator_initials(self, value):
		self._operator_initials = value

	@property
	def product(self):
		if self._product is None:
			data = self._mssql.execute(f"SELECT [Product] FROM Prefixes WHERE [Prefix] = '{self.serial_number_prefix}'")
			if not data:
				raise ValueError
			self._product = data[0]
		return self._product

	@product.setter
	def product(self, value):
		self._product = value


class Application(psutil.Process):
	def __init__(self, fp: Union[str, pathlib.Path], exclude: Optional[Union[int, Iterable[int]]] = None):
		if type(fp) is pathlib.Path:
			fp = str(fp)
		if is_running(fp, exclude):
			super().__init__(process_pid(fp, exclude))
		else:
			super().__init__(psutil.Popen(fp).pid)
		self.fp = fp
		self.nice(psutil.HIGH_PRIORITY_CLASS)
		self.win32 = pwn.Application(backend='win32').connect(process=self.pid)
		self.uia = pwn.Application(backend='uia').connect(process=self.pid)
		self._user = None
		self.logged_in = False

	# def log_in(self, usr: str = None, pwd: str = None):
	# 	if pwd is None:
	# 		raise ValueError()
	# 	if usr is None:
	# 		if self._user is not None:
	# 			usr = self._user
	# 		else:
	# 			raise ValueError()
	# 	else:
	# 		self._user = usr
	# 	login_win = self.app_win32['Sign In']
	# 	login_win.set_focus()
	# 	login_win.Edit3.SetEditText(usr)
	# 	login_win.Edit2.SetEditText(pwd)
	# 	login_win.OKButton.Click()
	# 	if self._error.exists():
	# 		message = self._error.Static2.texts()[0]
	# 		if ('count limit' in message) and ('exceeded' in message):
	# 			self._error.OKButton.Click()
	# 	while self._notification.exists():
	# 		try:
	# 			message2 = self._notification.Static2.texts()[0]
	# 			if (f"session for user '{usr}'" in message2) and ('already exists' in message2):
	# 				self._notification['&YesButton'].Click()
	# 			elif ('Exception initializing form' in message2) and ('executable file vbc.exe cannot be found' in message2):
	# 				self._notification.OKButton.Click()
	# 				raise SyteLineFormContainerError("SyteLine window's form container is corrupt/non-existent")
	# 			sleep(1)
	# 		except Exception:
	# 			break
	# 	CV_Config.__init__(self, self._win)
	# 	self.logged_in = True
	#
	# def log_out(self, force_quit=True):
	# 	if force_quit:
	# 		self._win2.child_window(best_match='Sign OutMenuItem').select()
	# 	else:
	# 		# Close out each individual open form properly
	# 		pass
	# 	self.logged_in = False

	def move_and_resize(self, left: int, top: int, right: int, bottom: int):
		self._hwnd = self._win.handle
		# hwnd = win32gui.GetForegroundWindow()
		coord = Coordinates(left=left, top=top, right=right, bottom=bottom)
		win32gui.MoveWindow(self._hwnd, int(coord.left) - 7, coord.top, coord.width, coord.height, True)

	def open_form(self, name: str, alias: Optional[str] = None):
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

	def change_forms(self):
		pass

	@property
	def forms(self):
		sl_uia = self.uia.window(title_re='Infor ERP SL (EM)*')
		return {REGEX_WINDOW_MENU_FORM_NAME.search(item.texts()[0]).group(1): item for item in sl_uia.WindowMenu.items() if (item.texts()[0].lower() != 'cascade') and (item.texts()[0].lower() != 'tile') and (item.texts()[0].lower() != 'close all')}


class PuppetMaster:
	_children = set()
	pids = defaultdict(list)

	def __init__(self, fp: Optional[Union[str, pathlib.Path]] = None):
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


class TestTimer:
	def __init__(self):
		self._start_time = None

	def start(self):
		self._start_time = datetime.datetime.now()

	def lap(self):
		if self._start_time:
			retval = datetime.datetime.now() - self._start_time
			return retval
		else:
			print(None)
			return None

	def reset(self):
		self._start_time = None

	def stop(self):
		retval = self.lap()
		self.reset()
		return retval


# - - - - - - - - - - - - - - - - - - - FUNCTIONS - - - - - - - - - - - - - - - - - - - -
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


# - - - - - - - - - - - - - - - - - - - - REGEX - - - - - - - - - - - - - - - - - - - - -
REGEX_USER_SESSION_LIMIT = re.compile(r"session count limit")
REGEX_INVALID_LOGIN = re.compile(r"user ?name.*password.*invalid")
REGEX_REPLACE_SESSION = re.compile(r"(?im)session .* user '(?P<user>\w+)' .* already exists(?s:.*)[\n\r](?P<question>.+\?)")
REGEX_WINDOW_MENU_FORM_NAME = re.compile(r"^\d+ (?P<name>[\w* ?]+\w*) .*")


# - - - - - - - - - - - - - - - - - - - - COMMON  - - - - - - - - - - - - - - - - - - - -
CELLULAR_UNIT_BUILDS = ('EX-600-M', 'EX-625S-M', 'EX-600-T', 'EX-600', 'EX-625-M', 'EX-600-DEMO', 'EX-600S', 'EX-600S-DEMO', 'EX-600V-M',
						'EX-600V', 'EX-680V-M', 'EX-600V-DEMO', 'EX-680V', 'EX-680S', 'EX-680V-DEMO', 'EX-600V-R', 'EX-680S-M', 'HG-2200-M',
						'CL-4206-DEMO', 'CL-3206-T', 'CL-3206', 'CL-4206', 'CL-4206', 'CL-3206-DEMO', 'CL-4206-M', 'CL-3206-M', 'HB-110',
						'HB-110-DEMO', 'HB-110-M', 'HB-110S-DEMO', 'HB-110S-M', 'HB-110S', 'LC-800V-M', 'LC-800S-M', 'LC-825S-M', 'LC-800V-DEMO',
						'LC-825V-M', 'LC-825V-DEMO', 'LC-825V', 'LC-825S', 'LC-825S-DEMO', 'LC-800S-DEMO')
timer = TestTimer()

