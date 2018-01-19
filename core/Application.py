#! python3 -W ignore
# coding=utf-8

import logging
import pathlib
import win32gui
from string import punctuation
from time import sleep
from typing import Dict, Iterable, NamedTuple, Union

import psutil
import pyautogui as pag
import pywinauto as pwn
from _globals import *
from pywinauto.controls import common_controls, hwndwrapper, uia_controls, win32_controls
from utils.tools import center, process_pid

from constants import REGEX_WINDOW_MENU_FORM_NAME, SYTELINE_WINDOW_TITLE

Dialog = NamedTuple('Dialog', [('self', pwn.WindowSpecification), ('Title', str), ('Text', str),
                               ('Buttons', Dict[str, win32_controls.ButtonWrapper])])
log = logging.getLogger('root')


class Application(psutil.Process):
	# TODO: Make Simpleton?
	# TODO: Handle login pop-ups, including occasional required password change
	def __init__(self, pid):
		psutil.Process.__init__(self, pid=pid)
		self.nice(psutil.HIGH_PRIORITY_CLASS)
		self.win32 = pwn.Application(backend='win32').connect(process=self.pid)
		self.uia = pwn.Application(backend='uia').connect(process=self.pid)
		self._logged_in = False
		self._user = None

	@classmethod
	def start(cls, fp: Union[str, pathlib.Path]):
		return cls(psutil.Popen(str(fp)).pid)

	@classmethod
	def connect(cls, fp: Union[str, pathlib.Path], exclude: Union[int, Iterable[int]] = None):
		return cls(process_pid(fp, exclude))

	def log_in(self, usr: str = username, pwd: str = password) -> bool:
		if not self.logged_in and self.win32.SignIn.exists(10, 0.09):
			log.info("SyteLine not logged in, starting login procedure")
			self.win32.SignIn.UserLoginEdit.set_text(usr)
			self.win32.SignIn.PasswordEdit.set_text(pwd)
			self.win32.SignIn.set_focus()
			self.win32.SignIn.OKButton.click()
			for i in range(8):
				top_window = self.win32.top_window()
				try:
					top_window.send_keystrokes('{ENTER}')
				except hwndwrapper.InvalidWindowHandle:
					pass
			sleep(0.5)
			log.debug(self.win32.top_window().texts()[0])
			if (not self.win32.SignIn.exists(10, 0.09)) or ('(EM)' in self.win32.top_window().texts()[0]):
				self.win32.window(title_re=SYTELINE_WINDOW_TITLE).wait('ready', 2, 0.09)
				self._logged_in = True
				self._user = usr
				log.info(f"Successfully logged in as '{self._user}'")
				sleep(4)
				return True
			else:
				log.warning(f"Login attempt as '{usr}' unsuccessful")
		return False

	def log_out(self) -> bool:
		if self.logged_in and not self.win32.SignIn.exists(10, 0.09):
			log.info("SyteLine logged in, starting logout procedure")
			sl_uia = self.uia.window(title_re=SYTELINE_WINDOW_TITLE)
			so = [item for item in sl_uia.MenuBar.items() if item.texts()[0].lower().strip() == 'sign out'][0]
			sl_uia.set_focus()
			r_i = so.rectangle()
			c_coords = center(x1=r_i.left, y1=r_i.top, x2=r_i.right, y2=r_i.bottom)
			pag.click(*c_coords)
			if self.win32.SignIn.exists(10, 0.09):
				self.win32.SignIn.wait('ready', 2, 0.09)
				self._logged_in = False
				self._user = None
				log.info(f"Successfully logged out")
				sleep(4)
				return True
			else:
				log.warning(f"Logout attempt unsuccessful")
		return False

	def quick_log_in(self, usr: str = username, pwd: str = password) -> bool:
		if not self.logged_in and self.win32.SignIn.exists(1, 0.09):
			log.info("SyteLine not logged in, starting login procedure")
			self.win32.SignIn.UserLoginEdit.set_text(usr)
			self.win32.SignIn.PasswordEdit.set_text(pwd)
			self.win32.SignIn.set_focus()
			self.win32.SignIn.OKButton.click()
			for i in range(8):
				top_window = self.win32.top_window()
				try:
					top_window.send_keystrokes('{ENTER}')
				except hwndwrapper.InvalidWindowHandle:
					pass
			sleep(0.5)
			log.debug(self.win32.top_window().texts()[0])
			if (not self.win32.SignIn.exists(1, 0.09)) or ('(EM)' in self.win32.top_window().texts()[0]):
				self._logged_in = True
				self._user = usr
				log.info(f"Successfully logged in as '{self._user}'")
				return True
			else:
				log.warning(f"Login attempt as '{usr}' unsuccessful")
		return False

	def quick_log_out(self) -> bool:
		if not self.win32.SignIn.exists(1, 0.09):
			log.info("SyteLine logged in, starting logout procedure")
			sl_uia = self.uia.window(title_re=SYTELINE_WINDOW_TITLE)
			so = [item for item in sl_uia.MenuBar.items() if item.texts()[0].lower().strip() == 'sign out'][0]
			sl_uia.set_focus()
			r_i = so.rectangle()
			c_coords = center(x1=r_i.left, y1=r_i.top, x2=r_i.right, y2=r_i.bottom)
			pag.click(*c_coords)
			sleep(0.5)
			log.debug(self.win32.top_window().texts()[0])
			if 'Sign In' in self.win32.top_window().texts()[0]:
				self._logged_in = False
				log.info(f"Successfully logged out")
				return True
			else:
				log.warning(f"Logout attempt unsuccessful")
		return False

	def move_and_resize(self, left: int, top: int, right: int, bottom: int):
		coord = {'left': left, 'top': top, 'right': right, 'bottom': bottom}
		win32gui.MoveWindow(self.hwnd, int(coord['left']) - 7, coord['top'], coord['right'] - coord['left'],
		                    coord['bottom'] - coord['top'], True)

	def open_form(self, *names):
		# TODO: wait until passes
		open_forms = self.forms.keys()
		log.debug(f"Opening form(s): {', '.join(names)}")
		for name in names:
			if name in open_forms:
				continue
			sl_win = self.win32.window(title_re=SYTELINE_WINDOW_TITLE)
			sl_win.click_input()
			sl_win.send_keystrokes('^o')
			self.win32.SelectForm.AllContainingEdit.set_text(name)
			self.win32.SelectForm.set_focus()
			self.win32.SelectForm.FilterButton.click()
			common_controls.ListViewWrapper(self.win32.SelectForm.ListView).item(name).click()
			self.win32.SelectForm.set_focus()
			self.win32.SelectForm.OKButton.click()
			log.debug(f"Form '{name}' opened")
			sleep(4)

	def quick_open_form(self, *names):
		for name in names:
			sl_win = self.win32.window(title_re=SYTELINE_WINDOW_TITLE)
			sl_win.set_focus()
			sl_win.click_input()
			sl_win.send_keystrokes('^o')
			self.win32.SelectFormWindow.set_focus()
			self.win32.SelectFormWindow.AllContainingEdit.set_text(name)
			self.win32.SelectFormWindow.set_focus()
			self.win32.SelectFormWindow.FilterButton.click()
			common_controls.ListViewWrapper(self.win32.SelectFormWindow.ListView).item(name).click()
			self.win32.SelectFormWindow.set_focus()
			self.win32.SelectFormWindow.OKButton.click()
			sleep(2)

	def find_value_in_collection(self, collection: str, property_: str, value, case_sensitive=False) -> bool:
		try:
			sl_win = self.win32.window(title_re=SYTELINE_WINDOW_TITLE)
			sl_win.click_input()
			sl_win.send_keystrokes('%e')
			sleep(0.02)
			sl_win.send_keystrokes('v')
			find_window = self.win32['Find']
			if find_window.exists():
				find_window.set_focus()
				find_window.InCollectionComboBox.select(collection)
				find_window.InPropertyComboBox.select(property_)
				find_window.FindEdit.set_text(value)
				if case_sensitive:
					find_window.CaseSensitiveButton.check()
				find_window.set_focus()
				find_window.OKButton.click()
			else:
				self.win32.top_window().send_keystrokes('{ESC}')
				return False
		except Exception:
			self.win32.top_window().send_keystrokes('{ESC}')
			return False
		else:
			return True

	def change_form(self, name: str):
		forms = self.forms
		if name in forms:
			if name == self.get_focused_form():
				pass
			else:
				forms[name].select()
		else:
			raise ValueError(f"Form '{name}' not open")

	@property
	def forms(self) -> Dict[str, uia_controls.MenuItemWrapper]:
		# TODO: Possible form object including 'is_checked' property
		sl_uia = self.uia.window(title_re=SYTELINE_WINDOW_TITLE)
		retval = {REGEX_WINDOW_MENU_FORM_NAME.search(item.texts()[0]).group(1): item for item in
		          sl_uia.WindowMenu.items() if
		          (item.texts()[0].lower() != 'cascade') and (item.texts()[0].lower() != 'tile') and (
			          item.texts()[0].lower() != 'close all')}
		if retval:
			log.debug(f"Forms open: {', '.join(retval.keys())}")
		else:
			log.debug("No forms open")
		return retval

	@property
	def logged_in(self):
		if self.win32.SignIn.exists(10, 0.09):
			self._logged_in = False
		else:
			self._logged_in = True
		return self._logged_in

	@property
	def hwnd(self):
		return self.win32.top_window().handle

	@property
	def window_rect(self):
		rect = win32gui.GetWindowRect(self.hwnd)
		return int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3])

	@property
	def size(self):
		x, y = self.window_rect[:2]
		w = abs(self.window_rect[2] - x)
		h = abs(self.window_rect[3] - y)
		return w, h

	@size.setter
	def size(self, value):
		w, h = value
		x, y = self.location
		win32gui.MoveWindow(self.hwnd, x, y, w, h, True)

	@property
	def location(self):
		return self.window_rect[:2]

	@location.setter
	def location(self, value):
		x, y = value
		w, h = self.size
		win32gui.MoveWindow(self.hwnd, x, y, w, h, True)

	def get_focused_form(self) -> str:
		"""0x100000  1048576  0b100000000000000000000  focusable
		   0x100004  1048580  0b100000000000000000100  focusable, focused
		   0x100084  1048708  0b100000000000010000100  focusable, focused, hot-tracked
		   0x100094  1048724  0b100000000000010010100  focusable, focused, hot-tracked, checked
		   0x100010  1048592  0b100000000000000010000  focusable, checked
		   0x000004  0000004  0b000000000000000000100  focused
		   0x000010  0000016  0b000000000000000010000  checked
		   0x000040  0000064  0b000000000000001000000  read-only
		   0x000080  0000128  0b000000000000010000000  hot-tracked
		   0x100000  1048576  0b100000000000000000000  focusable"""
		for item in self.forms.items():
			name, form = item
			state = form.legacy_properties()['State']
			bin_state = bin(state)
			log.debug(f"Form State: {state}")
			if int(bin_state[-5], base=2):  # If the fifth bit == 1
				return name
		else:
			return ''

	def verify_form(self, name: str) -> bool:
		return name == self.get_focused_form()

	def ensure_form(self, name: str):
		self.win32.top_window().click_input()
		if name not in self.forms.keys():
			self.open_form(name)
		if not self.verify_form(name):
			self.change_form(name)

	def get_popup(self, timeout=1) -> Dialog:
		dlg = self.win32.window(class_name="#32770")
		if dlg.exists(timeout, 0.09):
			title = ''.join(text.strip() for text in dlg.texts())
			text = ''.join(text.replace('\r\n\r\n', '\r\n').strip() for cls in dlg.children() if
			               cls.friendly_class_name() == 'Static' for text in cls.texts())
			buttons = {text.strip(punctuation + ' '): cls for cls in dlg.children() if
			           cls.friendly_class_name() == 'Button' for text in cls.texts()}
			return Dialog(dlg, title, text, buttons)
		else:
			return None

	def get_user(self):
		sl_win = self.win32.window(title_re=SYTELINE_WINDOW_TITLE)
		sl_uia = self.uia.window(title_re=SYTELINE_WINDOW_TITLE)
		self.quick_open_form("User Information")
		self._user = sl_win.UserIDEdit.texts()[0]
		sl_uia.CancelCloseButton.click()

	def __enter__(self):
		return self

	def __exit__(self, etype, value, traceback):
		try:
			self.quick_log_out()
		except Exception:
			pass
		self.terminate()
		gone, still_alive = psutil.wait_procs([self], timeout=3)
		for p in still_alive:
			p.kill()

__all__ = ['Application']
