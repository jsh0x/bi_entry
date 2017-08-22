import sys
from collections import defaultdict as _defaultdict
from time import sleep as _sleep
import datetime
import logging
import queue
import threading
from string import ascii_letters as _ascii_letters, punctuation as _punctuation, digits as _digits
from typing import Dict as _Dict, Union as _Union, Any as _Any, List as _List, Tuple as _Tuple

import psutil as _psutil
import pyautogui as pag
import pywinauto as pwn
from pywinauto import Application, keyboard, controls as ctrls, clipboard, base_wrapper, win32defines, mouse
from pywinauto.timings import always_wait_until_passes
import numpy as np

from types_ import Coordinates

log = logging.getLogger('root')
ctrl_log = logging.getLogger('logControl')

# __name__
# __annotations__
# __defaults__
# __kwdefaults__

def string2date(string: str):
	month, day, year = string.split('/', 2)
	return datetime.date(year=int(year), month=int(month), day=int(day))


def string2datetime(string: str):
	date, time = string.split(' ', 1)
	month, day, year = date.split('/', 2)
	time, mod = time.rsplit(' ', 1)
	hour, minute, second = time.split(':', 3)
	if mod == 'AM' and int(hour) == 12:
		hour = '00'
	elif mod == 'PM' and int(hour) != 12:
		hour = str(int(hour) + 12)
	return datetime.datetime(year=int(year), month=int(month), day=int(day), hour=int(hour), minute=int(minute), second=int(second))


def constant_factory(value):
	return lambda: value


class Control:
	def __init__(self, window: pwn.WindowSpecification, criteria: _Dict[str, _Any], wrapper, text: str=None):
		self.__name__ = self.control_name
		#self.window = window.__getattribute__(self.name)
		self.window = None
		self.parent_window = None
		#self.text = text
		self.ctrl = None
		self.get_ctrl(window, criteria, wrapper)

		#self.__name__ = self.ctrl.criteria['control_type']
		props = self.ctrl.get_properties()
		coord = props['rectangle']
		self.coordinates = Coordinates(left=coord.left, top=coord.top, right=coord.right, bottom=coord.bottom)
		log_string = f"'{self.control_name}' {self.control_type_name}= "

		try: log_string += f", class_name: '{props['class_name']}'"
		except Exception: pass
		try: log_string += f", parent: '{self.ctrl.parent()}'"
		except Exception: pass
		try: log_string += f", process: '{self.ctrl.process()}'"
		except Exception: pass
		try: log_string += f", title: '{self.ctrl.title()}'"
		except Exception: pass
		try: log_string += f", visible: '{props['is_visible']}'"
		except Exception: pass
		try: log_string += f", enabled: '{props['is_enabled']}'"
		except Exception: pass
		try: log_string += f", handle: '{self.ctrl.handle()}'"
		except Exception: pass
		try: log_string += f", active: '{props['is_active']}'"
		except Exception: pass
		try: log_string += f", control_id: '{self.ctrl.control_id()}'"
		except Exception: pass
		try: log_string += f", control_type: '{self.ctrl.control_type()}'"
		except Exception: pass
		try: log_string += f", auto_id: '{self.ctrl.auto_id()}'"
		except Exception: pass
		try: log_string += f", framework_id: '{self.ctrl.framework_id()}'"
		except Exception: pass
		try: log_string += f", tree: '{self.ctrl.dump_tree()}'"
		except Exception: pass

		ctrl_log.debug(log_string)

	@always_wait_until_passes(10, 1)
	def get_ctrl(self, window, criteria, wrapper):
		self.window = window.child_window(**criteria)
		self.parent_window = window
		self.ctrl = wrapper(self.window.element_info)

	def ready(self):
		self.window.wait('ready')
		self.window.wait('exists')
		self.window.wait('visible')

	def exists(self):
		return self.window.exists()

	def get_props(self):
		return self.ctrl.get_properties()

	def get_image(self):
		return self.ctrl.capture_as_image()

	"""	try:
			val = self.ctrl.get_properties()
			print(f"\n{name}\n{val}")
		except Exception as ex:
			print(ex)"""

	"""@property
	def ctrl(self):
		return self.window.wrapper_object()"""

	"""	try:
			handle = window[self.name].handle
			window = window[self.name]
		except:
			parent = window.parent()
			for child in parent.children():
				if child.texts()[0] == self.name:
					break
			window = parent
			handle = parent.handle
		super().connect(handle=handle).window_ = window

	@property
	def window(self):
		
		try:
			handle = self.window[self.name].handle
			value = self.window[self.name]
		except:
			parent = value.parent()
			for child in parent.children():
				if child.texts()[0] == self.name:
					break
			handle = parent.handle
		app = Application(self.window.backend.name).connect(handle=handle)
		return .window_()

	@window.setter
	def window(self, value):
		super().__init__(value.backend.name)
		try:
			handle = value[self.name].handle
			value = value[self.name]
		except:
			parent = value.parent()
			for child in parent.children():
				if child.texts()[0] == self.name:
					break
			handle = parent.handle
		self._window = super().connect(handle=handle).window_

	@property"""
	"""def enabled(self):
		self.window.set_focus()
		self.window.click_input()
		im = self.window.capture_as_image()
		img = np.array(im.convert('L'))
		img = np.where(img > 200, img, 0)
		bg_white = np.where(img > 250, 1, 0).flatten().sum()
		bg_gray = np.where(210 < img < 240, 1, 0).flatten().sum()
		if bg_white > bg_gray:
			return True
		elif bg_white < bg_gray:
			return False"""


class Control2:
	def __init__(self, window: pwn.WindowSpecification, criteria: _Dict[str, _Any], wrapper):
		self.__name__ = ''
		self.__type__ = ''
		self.window = window.child_window(**criteria)
		self.parent_window = window
		self.ctrl = wrapper(self.window.element_info)
		props = self.ctrl.get_properties()
		coord = props['rectangle']
		self.coordinates = Coordinates(left=coord.left, top=coord.top, right=coord.right, bottom=coord.bottom)
		log_string = f"'{self.control_name}' {self.control_type_name}= "

	def ready(self):
		self.window.wait('ready')
		self.window.wait('exists')
		self.window.wait('visible')

	def exists(self):
		return self.window.exists()


class Button(Control):
	def __init__(self, window: _Dict[str, pwn.WindowSpecification], criteria: _Dict[str, _Any], control_name, control_type_name=None, text: str=None):
		self.control_name = control_name
		if not control_type_name:
			self.control_type_name = 'Button'
		else:
			self.control_type_name = control_type_name
		self._kwargs = {'window': window, 'criteria': criteria, 'control_name': control_name, 'control_type_name': control_type_name}
		log.debug(f"Initializing '{self.control_name}' {self.control_type_name}")
		super().__init__(window['uia'], criteria, ctrls.uia_controls.ButtonWrapper)
		log.debug(f"'{self.control_name}' {self.control_type_name} initialized")

	# @always_wait_until_passes(5, 1)
	def click(self, quantity: int = 1):
		for q in range(quantity):
			self.ctrl.click()


class Checkbox(Button):
	def __init__(self, window: _Dict[str, pwn.WindowSpecification], criteria: _Dict[str, _Any], control_name, text: str = None):
		self._kwargs = {'window': window, 'criteria': criteria, 'control_name': control_name}
		super().__init__(window, criteria, control_name, control_type_name='Checkbox')

	@property
	def checked_state(self):
		retval = self.ctrl.get_toggle_state()
		if retval == 1:
			return True
		elif retval == 0:
			return False
	@checked_state.setter
	def checked_state(self, value):
		if self.checked_state and not value\
		or not self.checked_state and value:
			self.ctrl.toggle()

	def toggle(self):
		self.ctrl.toggle()


class Textbox(Control):
	def __init__(self, window: _Dict[str, pwn.WindowSpecification], criteria: _Dict[str, _Any], control_name, control_type_name=None, fmt=('alphabetic','punctuation','numeric','mixed'), text: str=None):
		self.control_name = control_name
		if not control_type_name:
			self.control_type_name = 'Textbox'
		else:
			self.control_type_name = control_type_name
		self._kwargs = {'window': window, 'criteria': criteria, 'control_name': control_name, 'control_type_name': control_type_name, 'fmt': fmt}
		log.debug(f"Initializing '{self.control_name}' {self.control_type_name}")
		super().__init__(window['win32'], criteria, ctrls.win32_controls.EditWrapper)
		self.fmt = fmt
		log.debug(f"'{self.control_name}' {self.control_type_name} initialized")

	def set_focus(self):
		self.ctrl.set_focus()

	def set_keyboard_focus(self):
		self.ctrl.set_keyboard_focus()

	def send_keystrokes(self, keystrokes):
		self.ctrl.send_keystrokes(keystrokes)

	def filter_text(self, text: str):
		if self.fmt == datetime.datetime:
			text = string2datetime(text)
			text = text.strftime("%m/%d/%Y %I:%M:%S %p")
		elif self.fmt == datetime.date:
			text = string2date(text)
			text = text.strftime("%m/%d/%Y")
		else:
			if 'mixed' in self.fmt:
				text = text
			elif 'upper' in self.fmt:
				text = text.upper()
			elif 'lower' in self.fmt:
				text = text.lower()
			if 'alphabetic' not in self.fmt:
				for char in text:
					if char in _ascii_letters:
						text = text.replace(char, '', 1)
			if 'punctuation' not in self.fmt:
				for char in text:
					if char in _punctuation:
						text = text.replace(char, '', 1)
			if 'numeric' not in self.fmt:
				for char in text:
					if char in _digits:
						text = text.replace(char, '', 1)
		return text

	def text(self):
		return self.ctrl.texts()[0]

	@always_wait_until_passes(4, 1)
	def texts(self):
		return self.ctrl.texts()[1:]

	@always_wait_until_passes(2, 1)
	def set_text(self, text: str):
		if self.fmt != ('alphabetic','punctuation','numeric','mixed'):
			text = self.filter_text(text)
		self.ctrl.set_focus()
		self.ctrl.set_keyboard_focus()
		self.ctrl.set_text(text)
		#self.ctrl.send_keystrokes('^{HOME}')
		#self.ctrl.send_keystrokes('^+{END}')
		#self.ctrl.send_keystrokes('{DELETE}')
		#self.ctrl.send_keystrokes(text)

	def get_line(self, index: int):
		# self.get_line(index)
		return self.ctrl.texts()[index]

	def text_block(self):
		# self.ctrl.text_block()
		return self.ctrl.texts()[0]

	def line_count(self):
		# self.ctrl.line_count()
		return len(self.ctrl.texts())-1

	def line_length(self, index: int):
		# self.line_length()
		line = self.get_line(index)
		return len(line)


class Textbox2(Control2):
	def __init__(self, window, criteria, control_name, control_type_name=None):
		self.control_name = control_name
		if not control_type_name:
			self.control_type_name = 'Textbox'
		else:
			self.control_type_name = control_type_name
		log.debug(f"Initializing '{self.control_name}' {self.control_type_name}")
		super().__init__(window['win32'], criteria, ctrls.win32_controls.EditWrapper)
		log.debug(f"'{self.control_name}' {self.control_type_name} initialized")


class Datebox(Textbox):
	def __init__(self, window: _Dict[str, pwn.WindowSpecification], criteria: _Dict[str, _Any], control_name, text: str=None):
		self._kwargs = {'window': window, 'criteria': criteria, 'control_name': control_name}
		super().__init__(window, criteria, control_name, control_type_name='Datebox')
		self.fmt = datetime.datetime


class Scrollbar(Control):
	def __init__(self, window: pwn.WindowSpecification, criteria: _Dict[str, _Any], control_name, control_type_name, text: str=None):
		self.control_name = control_name
		self.control_type_name = control_type_name

		super().__init__(window, criteria, ctrls.hwndwrapper.HwndWrapper)
		self._possible_amounts = ('line', 'page', 'end')


class VerticalScrollbar(Scrollbar):
	def __init__(self, window: pwn.WindowSpecification, control_name, text: str=None):
		super().__init__(window=window, criteria={'best_match': 'Vertical'}, control_name=control_name, control_type_name="Vertical Scrollbar")
		self._kwargs = {'window': window, 'criteria': {'best_match': 'Vertical'}, 'control_name': control_name}
		log.debug(f"Initializing '{self.control_name}' {self.control_type_name}")
		_column_down = self.window.child_window(title="Column down", control_type="Button", top_level_only=False, visible_only=False)
		self._column_down = ctrls.uia_controls.ButtonWrapper(_column_down.element_info)
		_column_up = self.window.child_window(title="Column up", control_type="Button", top_level_only=False, visible_only=False)
		self._column_up = ctrls.uia_controls.ButtonWrapper(_column_up.element_info)
		#_page_down = self.window.child_window(title="Page down", control_type="Button", top_level_only=False, visible_only=False)
		#self._page_down = ctrls.uia_controls.ButtonWrapper(_page_down.element_info)
		#_page_up = self.window.child_window(title="Page up", control_type="Button", top_level_only=False, visible_only=False)
		#self._page_up = ctrls.uia_controls.ButtonWrapper(_page_up.element_info)
		log.debug(f"'{self.control_name}' {self.control_type_name} initialized")

	def scroll_up(self, amount: str='line', count: int=1):
		if amount not in self._possible_amounts:
			raise ValueError
		if amount == 'line':
			for presses in range(count):
				self._column_up.click()
		#elif amount == 'page':
		#	for presses in range(count):
		#		self._page_up.click()
		#elif amount == 'end':
		#	for presses in range(count):
		#		keyboard.SendKeys('^{HOME}')

	def scroll_down(self, amount: str='line', count: int=1):
		if amount not in self._possible_amounts:
			raise ValueError
		if amount == 'line':
			for presses in range(count):
				self._column_down.click()
		#elif amount == 'page':
		#	for presses in range(count):
		#		self._page_down.click()
		#elif amount == 'end':
		#	for presses in range(count):
		#		keyboard.SendKeys('^{END}')


class HorizontalScrollbar(Scrollbar):
	def __init__(self, window: pwn.WindowSpecification, control_name, text: str = None):
		super().__init__(window=window, criteria={'best_match': 'Horizontal'}, control_name=control_name, control_type_name="Horizontal Scrollbar")
		self._kwargs = {'window': window, 'criteria': {'best_match': 'Horizontal'}, 'control_name': control_name}
		log.debug(f"Initializing '{self.control_name}' {self.control_type_name}")
		_column_right = self.window.child_window(title="Column right", control_type="Button", top_level_only=False, visible_only=False)
		self._column_right = ctrls.uia_controls.ButtonWrapper(_column_right.element_info)
		_column_left = self.window.child_window(title="Column left", control_type="Button", top_level_only=False, visible_only=False)
		self._column_left = ctrls.uia_controls.ButtonWrapper(_column_left.element_info)
		#_page_right = self.window.child_window(title="Page right", control_type="Button", top_level_only=False, visible_only=False)
		#self._page_right = ctrls.uia_controls.ButtonWrapper(_page_right.element_info)
		#_page_left = self.window.child_window(title="Page left", control_type="Button", top_level_only=False, visible_only=False)
		#self._page_left = ctrls.uia_controls.ButtonWrapper(_page_left.element_info)
		log.debug(f"'{self.control_name}' {self.control_type_name} initialized")

	def scroll_left(self, amount: str='line', count: int=1):
		if amount not in self._possible_amounts:
			raise ValueError
		if amount == 'line':
			for presses in range(count):
				self._column_left.click()
		#elif amount == 'page':
		#	for presses in range(count):
		#		self._page_left.click()
		#elif amount == 'end':
		#	for presses in range(count):
		#		keyboard.SendKeys('^{HOME}')

	def scroll_right(self, amount: str='line', count: int=1):
		if amount not in self._possible_amounts:
			raise ValueError
		if amount == 'line':
			for presses in range(count):
				self._column_right.click()
		#elif amount == 'page':
		#	for presses in range(count):
		#		self._page_right.click()
		#elif amount == 'end':
		#	for presses in range(count):
		#		keyboard.SendKeys('^{END}')


class GridView(Control):
	def __init__(self, window: _Dict[str, pwn.WindowSpecification], criteria: _Dict[str, _Any], control_name, text: str=None):
		self.control_name = control_name
		self.control_type_name = 'Grid'
		self._kwargs = {'window': window, 'criteria': criteria, 'control_name': control_name, 'control_type_name': self.control_type_name}
		log.debug(f"Initializing '{self.control_name}' {self.control_type_name}")
		super().__init__(window['uia'], criteria, ctrls.uia_controls.ListViewWrapper)
		self.rows = 0
		self._cell = None
		self.header_dict = {}
		self._win = window
		# try:
		# 	scrollbar_h = self.window.child_window(title_re='Horizontal*')
		# 	if scrollbar_h.exists():
		# 		self.scrollbar_h = HorizontalScrollbar(self.window)
		# 		self.hsb = True
		# 	else:
		# 		self.hsb = False
		# except Exception as ex:
		# 	# print(ex)
		# 	self.hsb = False
		# try:
		# 	scrollbar_v = self.window.child_window(title_re='Vertical*')
		# 	if scrollbar_v.exists():
		# 		self.scrollbar_v = VerticalScrollbar(self.window)
		# 		self.vsb = True
		# 	else:
		# 		self.vsb = False
		# except Exception as ex:
		# 	# print(ex)
		# 	self.vsb = False
		if True:
			# log.debug("Looking for Top Row")
			self._top_row = self.window.child_window(title='Top Row')
			# log.debug("Found Top Row")
			# log.debug("Getting column names")
			texts = self._top_row.children_texts()
			i = 0
			for col in texts:
				if col.strip(' ') == '':
					continue
				self.header_dict[col.strip(' ')] = i
				i += 1
			column_count = len(self.header_dict.keys())
			# log.debug(f"Got {column_count} column names")
			# log.debug("Counting rows")
			for ch in self.ctrl.children():
				text = ch.texts()[0]
				#print(text)
				if "Row " in text:
					try:
						self.rows = max(self.rows, int(text.replace('Row ', '')))
						# log.debug(f"Found Row {int(text.replace('Row ', ''))}")
					except Exception:
						pass
			self.rows += 1
			log.debug("Creating reference grid")
			self._grid = np.empty((self.rows, column_count, 2), dtype=np.object_)
			log.debug("Reference grid created")
			#self._grid = np.empty((self.rows, column_count, 3), dtype=np.object_)
			#self._grid[...,1] = False
			self.header_dict_rev = {}
			for k,v in self.header_dict.items():
				self.header_dict_rev[v] = k
			#self.populate()
		log.debug(f"'{self.control_name}' {self.control_type_name} initialized")

	def doit(self):
		x_range = np.arange(self._grid.shape[1], dtype=np.intp)
		y_range = np.arange(self._grid.shape[0], dtype=np.intp)
		for y in y_range:
			for x in x_range:
				cell_string = f"{self.header_dict_rev[x]} Row {y}"
				cell = self.window.child_window(title=cell_string, visible_only=False)
				cell_string = f"{self.header_dict_rev[x]} Row {y}DataItem"
				cell = cell.child_window(title=cell_string, visible_only=False)
				print(x,y,cell.get_properties())

	def populate(self, columns: _Union[str, _Tuple[str]]=None, rows: _Union[int, _Tuple[int]]=None, visible_only=False):
		log.debug("Getting x_range")
		if not columns:
			x_range = np.arange(self._grid.shape[1], dtype=np.intp)
			log.debug(f"x_range set to: {x_range}")
		else:
			x_range = []
			if type(columns) is str:
				x_range.append(self.header_dict[columns])
			else:
				for col in columns:
					x_range.append(self.header_dict[col])
			log.debug(f"x_range set to: {x_range}")
		log.debug("Getting y_range")
		if not rows:
			y_range = np.arange(self._grid.shape[0], dtype=np.intp)
			log.debug(f"y_range set to: {y_range}")
		else:
			y_range = []
			if type(rows) is int:
				y_range.append(rows-1)
			else:
				for row in rows:
					y_range.append(row-1)
			log.debug(f"y_range set to: {y_range}")
		log.debug("Populating grid reference")
		for y in y_range:
			for x in x_range:
				cell_string = f"{self.header_dict_rev[x]} Row {y}"
				log.debug(f"Looking for cell '{cell_string}'")
				cell = self.window.child_window(title=cell_string, visible_only=visible_only)
				log.debug(f"Cell '{cell_string}' found")
				value = cell.legacy_properties()['Value'].strip(' ')
				if (value == "True") or (value == "False"):
					if value == "True":
						value = True
					elif value == "False":
						value = False
					log.debug(f"({x}, {y}) -  {value}  as type: <class 'Checkbox'>")
					self._grid[y, x] = value, Checkbox
					continue
				elif len(value) == 10:
					try:
						value = string2date(value)
					except ValueError:
						err = str(sys.exc_info()[1])
						if "not enough values to unpack" in err:
							pass
						else:
							log.error(err)
					else:
						log.debug(f"({x}, {y}) -  {value}  as type: <class 'datetime.date'>")
						self._grid[y, x] = value, datetime.date
						continue
				elif len(value) == 22:
					try:
						value = string2datetime(value)
					except ValueError:
						err = str(sys.exc_info()[1])
						if "not enough values to unpack" in err:
							pass
						else:
							log.error(err)
					else:
						log.debug(f"({x}, {y}) -  {value}  as type: <class 'datetime.datetime'>")
						self._grid[y, x] = value, datetime.datetime
						continue
				if value and (value != '(null)'):
					try:
						value = int(value)
					except ValueError:
						err = str(sys.exc_info()[1])
						if "invalid literal for int() with base 10" in err:
							pass
						else:
							log.error(err)
					else:
						log.debug(f"({x}, {y}) -  {value}  as type: <class 'int'>")
						self._grid[y, x] = value, int
						continue
					log.debug(f"({x}, {y}) -  '{value}'  as type: <class 'str'>")
					self._grid[y, x] = value, str
		c = 0
		log.debug(f"Stage 2 populating started")
		for i in np.arange(self._grid.shape[1], dtype=np.intp):
			log.debug(f"Checking column {i}")
			column = self._grid[:,i,1]
			score_keep = _defaultdict(int)
			for col in column:
				score_keep[col] += 1
			score_keep_rev = {}
			for k,v in score_keep.items():
				if not k:
					continue
				score_keep_rev[v] = k
			try:
				k = sorted(score_keep_rev.keys(), reverse=True)[0]
				log.debug(f"{k} {score_keep_rev[k]}")
				self._grid[:,i,1] = score_keep_rev[k]
			except IndexError:
				err = str(sys.exc_info()[1])
				if "list index out of range" in err:
					pass
				else:
					log.error(err)
			c += 1
		log.debug("Grid population complete")

	def select_cell(self, column: str, row: int):
		# TODO: Select multiple, return ndarray
		x = self.header_dict[column]
		y = row - 1
		log.debug(f"Attempting to select cell at ({x}, {y})")
		self._cell = (x, y)
		log.debug(f"Cell at ({x}, {y}) selected")

	@property
	def cell(self):
		if not self._cell:
			raise ValueError("Cell not selected")
		x,y = self._cell
		retval = self._grid[y,x,0]
		if retval is not None:
			if self._grid[y,x,1] == datetime.date:
				return retval.strftime("%m/%d/%Y")
			elif self._grid[y,x,1] == datetime.datetime:
				return retval.strftime("%m/%d/%Y %I:%M:%S %p")
		return retval

	@cell.setter
	def cell(self, value):
		x,y = self._cell
		header = self.header_dict_rev[x]
		cell_string = f"{header} Row {y}"
		log.debug(f"Attempting to modify cell '{cell_string}'")
		if self._grid.shape[0] == y:
			temp = np.empty((1, self._grid.shape[1], self._grid.shape[2]), dtype=np.object_)
			self._grid = np.vstack((self._grid, temp))
		if (value is not None) and (self._grid[y,x,0] != value):
			log.debug(f"Looking for cell '{cell_string}'")
			cell = self.window.child_window(title=cell_string, visible_only=True)
			props = cell.get_properties()
			coord = props['rectangle']
			cell_coords = Coordinates(left=coord.left, top=coord.top, right=coord.right, bottom=coord.bottom)
			xy = cell_coords.center
			log.debug(f"Cell '{cell_string}' found")
			# cell.set_focus()
			# log.debug(f"Cell '{cell_string}' focused")
			mouse.click(coords=xy)
			log.debug(f"Cell '{cell_string}' clicked")
			if self._grid[y,x,1] == str:
				value = str(value)
				log.debug(f"Setting cell@({x}, {y}) to string: {value}")
				keyboard.SendKeys("{DELETE}")
				pag.typewrite(value)
			elif self._grid[y,x,1] == int:
				value = int(value)
				log.debug(f"Setting cell@({x}, {y}) to integer: {value}")
				keyboard.SendKeys("{DELETE}")
				keyboard.SendKeys(str(value))
			elif self._grid[y,x,1] == datetime.date:
				month, day, year = value.split('/', 2)
				value = datetime.date(year=int(year), month=int(month), day=int(day))
				log.debug(f"Setting cell@({x}, {y}) to date: {value.strftime('%m/%d/%Y')}")
				keyboard.SendKeys("{DELETE}")
				keyboard.SendKeys(value.strftime("%m/%d/%Y"))
			elif self._grid[y,x,1] == datetime.datetime:
				date, time = value.split(' ', 1)
				month, day, year = date.split('/', 2)
				time, mod = time.rsplit(' ', 1)
				hour, minute, second = time.split(':', 3)
				if mod == 'AM' and int(hour) == 12:
					hour = '00'
				elif mod == 'PM' and int(hour) != 12:
					hour = str(int(hour) + 12)
				value = datetime.datetime(year=int(year), month=int(month), day=int(day), hour=int(hour), minute=int(minute), second=int(second))
				log.debug(f"Setting cell@({x}, {y}) to datetime: {value.strftime('%m/%d/%Y %I:%M:%S %p')}")
				keyboard.SendKeys("{DELETE}")
				keyboard.SendKeys(value.strftime("%m/%d/%Y %I:%M:%S %p"))
			elif self._grid[y,x,1] == Checkbox:
				pass
			else:
				value = str(value)
				log.debug(f"No specific type detected, setting cell@({x}, {y}) to string: {value}")
				keyboard.SendKeys("{HOME}")
				keyboard.SendKeys("+{END}")
				keyboard.SendKeys("{DELETE}")
				pag.typewrite(value)
		self._grid[y,x,0] = value
		log.debug(f"Reference grid updated")

	def sort_with_header(self, column: str, order: str='desc'):
		header = self.window.child_window(parent=self._top_row, title=column)
		if not header.exists():
			raise ValueError(f"Header '{column}' does not exist")
		if order == 'desc':
			header.double_click_input()
			_sleep(0.5)
			header.double_click_input()
		elif order == 'asc':
			header.double_click_input()
		else:
			raise ValueError

	def select_row(self, row: int):
		row -= 1
		for header in self.header_dict.keys():
			try:
				row_string = f"{header} Row {row}"
				_row = self.window.child_window(title=row_string)
			except pwn.WindowAmbiguousError:
				continue
			else:
				_row.set_focus()
				_row.click_input()
				break
		else:
			raise pwn.WindowAmbiguousError

	def click_cell(self):
		x, y = self._cell
		header = self.header_dict_rev[x]
		cell_string = f"{header} Row {y}"
		log.debug(f"Looking for cell '{cell_string}'(AGAIN???)")
		if self._grid.shape[0] == y:
			temp = np.empty((1,self._grid.shape[1],self._grid.shape[2]), dtype=np.object_)
			self._grid = np.vstack((self._grid, temp))
		cell = self.window.child_window(title=cell_string, visible_only=True)
		log.debug(f"Cell '{cell_string}' found(AGAIN???)")
		cell.set_focus()
		log.debug(f"Cell '{cell_string}' focused(AGAIN???)")
		cell.click_input()


class Tab(Control):
	def __init__(self, window: _Dict[str, pwn.WindowSpecification], criteria: _Dict[str, _Any], name, controls, control_name, text: str=None):
		self.control_name = control_name
		self.control_type_name = 'Tab'
		self._kwargs = {'window': window, 'criteria': criteria, 'name': name, 'controls': controls, 'control_name': control_name}
		log.debug(f"Initializing '{self.control_name}' {self.control_type_name}")
		super().__init__(window['uia'], criteria, ctrls.uiawrapper.UIAWrapper)
		self._controls = controls
		self._name = name
		log.debug(f"'{self.control_name}' {self.control_type_name} initialized")

	# def _initiate_controls(self, name: str, info: _Dict[str, _Any], q: queue.Queue):
	# 	_class = info['class']
	# 	args = info.get('args', [])
	# 	kwargs = info.get('kwargs', {})
	# 	log.debug(f"Attempting to create '{_class}' with '{args}' and '{kwargs}'")
	# 	retval = _class.__new__(_class, *args, **kwargs)
	# 	log.debug(f"'{_class}' created")
	# 	q.put((name, retval))
	# 	log.debug(f"'{_class}' put in queue")
	# def initiate_controls(self):
	# 	q = queue.Queue(maxsize=0)
	# 	for name,info in self._controls.items():
	# 		worker = threading.Thread(target=self._initiate_controls, args=(name, info, q))
	# 		worker.setDaemon(True)
	# 		worker.start()
	# 	worker.join()
	# 	log.debug(f"Workers joined")
	# 	while not q.empty():
	# 		log.debug("Iterating queue")
	# 		name, _class = q.get()
	# 		log.debug(f"Got {name} {_class} from queue")
	# 		self.__setattr__(name, _class)
	# 		log.debug(f"{_class} attribute created with name {name}")
	def initiate_controls(self):
		for name,info in self._controls.items():
			_class = info['class']
			args = info.get('args', [])
			kwargs = info.get('kwargs', {})
			self.__setattr__(name, _class(*args, **kwargs))

	def select(self):
		self.ctrl.set_focus()
		try:
			self.ctrl.select()
		except Exception:
			try:
				self.ctrl.select(self._name)
			except Exception:
				cxy = self.coordinates.center
				mouse.click(coords=cxy)
		# self.window.wait('ready')
		self.initiate_controls()

'''class Button(Control):
	def __init__(self, name: str, text: str, window: _Tuple[pwn.WindowSpecification, pwn.WindowSpecification]):
		super().__init__(name, text, window[1], 'Button')
		log.debug(f"'{self.text}' {self.__name__} initialized")

	def click(self, quantity: int=1, wait_string: str='ready'):
		for q in range(quantity):
			self.ctrl.click_input()#####
			if wait_string:
				self.window.wait(wait_string)

	def props(self):
		print(self.ctrl.get_properties())
		parent = self.ctrl
		for child in parent.children():
			print('\n\n')
			print(child.texts()[0])
			child2 = child.children()
			count = 0
			for i in range(6):
				if i >= len(child2):
					continue
				if child2[i].texts()[0] == "Column right":
					right = child2[i]
				elif child2[i].texts()[0] == "Column left":
					left = child2[i]
				if child2[i].friendly_class_name() == "Custom":
					ei = child2[i].element_info
					a = ctrls.uia_controls.ListItemWrapper(ei)
					a.set_focus()
					a.click_input()
					b2 = a.descendants()
					b3 = a.texts()
					clipboard.EmptyClipboard()
					keyboard.SendKeys("^c")
					b4 = clipboard.GetData()
					right.click()
					count += 1
					print(f'\n{b2}, {b3}, {b4}')
				else:
					print(f'\n{child2[i].get_properties()}')
			for m in range(count):
				left.click()
		"""ei = self.ctrl.element_info
		children = self.ctrl.children()
		row_count = 0
		for ch in children:
			text = ch.texts()[0]
			if "Row " in text:
				try:
					row_count = max(row_count, int(text.replace('Row ', '')))
				except Exception:
					pass
		print(row_count)
		grid = ctrls.uia_controls.ListViewWrapper(ei)
		print(grid.columns())
		for i in range(1, row_count+1):
			try:
				sro = grid.cell(i, 0)
				print(sro.get_properties())
				print()
			except:
				pass"""


class Checkbox(Control):
	def __init__(self, name: str, text, window: _Tuple[pwn.WindowSpecification, pwn.WindowSpecification]):
		super().__init__(name, text, window[0], 'Checkbox')
		log.debug(f"'{self.text}' {self.__name__} initialized")


class Textbox(Control):
	def __init__(self, name: str, text: str, window: _Tuple[pwn.WindowSpecification, pwn.WindowSpecification], control_name: str='Textbox', fmt=('alphabetic','punctuation','numeric')):
		super().__init__(name, text, window[0], control_name)
		log.debug(f"'{self.text}' {self.__name__} initialized")
		self.fmt = fmt

	"""def focus(self, goto_end=False):
		self.window.set_focus()
		self.window.set_keyboard_focus()
		if goto_end:
			keyboard.SendKeys('{END}')

	def select_row(self, goto_home=True):
		#self.focus()
		self.window.set_focus()
		self.window.set_keyboard_focus()
		if goto_home:
			keyboard.SendKeys('{HOME}')
		keyboard.SendKeys('^+{RIGHT}')

	def select_all(self):
		# self.focus()
		self.window.set_focus()
		self.window.set_keyboard_focus()
		keyboard.SendKeys('^a')

	def typewrite(self, string: str, key_pause: float=0.05):
		keys = keyboard.parse_keys(string)
		for k in keys:
			self.focus(goto_end=True)
			k.run()
			_sleep(key_pause)"""

	@property
	def edit_text(self):
		text = self.ctrl.texts()[0]
		try:
			if datetime.datetime in self.fmt:
				retval = datetime.datetime.strptime(text, "%m/%d/%Y %I:%M:%S %p")
			else:
				retval = text
		except Exception as ex:
			retval = None
		finally:
			return retval


	@edit_text.setter
	def edit_text(self, string: str):
		if datetime.datetime in self.fmt:
			string = string2datetime(string)
		if 'upper' in self.fmt:
			string = string.upper()
		elif 'lower' in self.fmt:
			string = string.lower()
		if 'alphabetic' not in self.fmt:
			for char in string:
				if char in _ascii_letters:
					string.replace(char, '', 1)
		if 'punctuation' not in self.fmt:
			for char in string:
				if char in _punctuation:
					string.replace(char, '', 1)
		if 'numeric' not in self.fmt:
			for char in string:
				if char in _digits:
					string.replace(char, '', 1)
		self.ctrl.set_focus()
		self.ctrl.set_keyboard_focus()
		keyboard.SendKeys('^a')
		keyboard.SendKeys('{DELETE}')
		self.ctrl.set_edit_text(string)


class GridView(Control):
	def __init__(self, name: str, text: str, window: _Tuple[pwn.WindowSpecification, pwn.WindowSpecification]):
		super().__init__(name, text, window[1], 'GridView')
		#TODO: Work on mapping column/row system
		self.header_dict = {}
		self.rows = 0
		try:
			scrollbar_h = self.window.__getattribute__('Horizontal Scroll Bar')
			self._right = scrollbar_h.__getattribute__('Column right')
			self._left = scrollbar_h.__getattribute__('Column left')
			self.hsb = True
		except Exception as ex:
			print(ex)
			self.hsb = False
		try:
			scrollbar_v = self.window.__getattribute__('Vertical Scroll Bar')
			self._up = scrollbar_v.__getattribute__('Line up')
			self._down = scrollbar_v.__getattribute__('Line down')
			self.vsb = True
		except Exception as ex:
			print(ex)
			self.vsb = False

		#print(self.ctrl.get_properties())
		top_row = self.window.__getattribute__('Top Row')
		texts = top_row.children_texts()
		i = 0
		for col in texts:
			if col.strip(' ') == '':
				continue
			self.header_dict[col.strip(' ')] = i
			i += 1
		column_count = len(self.header_dict.keys())

		for ch in self.ctrl.children():
			text = ch.texts()[0]
			#print(text)
			if "Row " in text:
				try:
					self.rows = max(self.rows, int(text.replace('Row ', '')))
				except Exception:
					pass
		self._grid = np.empty((self.rows, column_count, 3), dtype=np.object_)
		self._grid[...,1] = False
		self.header_dict_rev = {}
		for k,v in self.header_dict.items():
			self.header_dict_rev[v] = k
		log.debug(f"'{self.text}' {self.__name__} initialized")

	def format_cell(self, column: str, row: int, fmt=None):
		x = self.header_dict[column]-1
		y = row-1
		if not fmt:
			fmt = self._grid[y,x,2]
		data = self._grid[y,x,0]
		retval = data
		if data and fmt and type(data) is not fmt:
			if fmt == datetime.datetime:
				if len(data) > 10:
					_fmt = "%m/%d/%Y %I:%M:%S %p"
				else:
					_fmt = "%m/%d/%Y"
				retval = datetime.datetime.strptime(data, _fmt)
			elif fmt == Checkbox:
				pass
			# TODO Checkbox fmt
			elif fmt == Combobox:
				pass
			# TODO Combobox fmt
			elif fmt == int:
				retval = int(data)
			elif fmt == float:
				retval = float(data)
			elif fmt == str:
				retval = str(data)
			else:
				raise ValueError(f"fmt='{fmt}' is invalid")
		return retval

	def format_cell(self, data, fmt):
		retval = data
		if data and fmt and type(data) is not fmt:
			if fmt == datetime.datetime:
				if len(data) > 10:
					_fmt = "%m/%d/%Y %I:%M:%S %p"
				else:
					_fmt = "%m/%d/%Y"
				retval = datetime.datetime.strptime(data, _fmt)
			elif fmt == Checkbox:
				pass
			# TODO Checkbox fmt
			elif fmt == Combobox:
				pass
			# TODO Combobox fmt
			elif fmt == int:
				retval = int(data)
			elif fmt == float:
				retval = float(data)
			elif fmt == str:
				retval = str(data)
			else:
					raise ValueError(f"fmt='{fmt}' is invalid")
		return retval

	def set_column_format(self,column: str, fmt):
		x = self.header_dict[column]-1
		grid_copy = self._grid[:,x,0].copy()
		try:
			for y,data in enumerate(grid_copy):
				grid_copy[y] = self.format_cell(data=data,fmt=fmt)
		except Exception as ex:
			print(ex)
		else:
			self._grid[:,x,:4:2] = (grid_copy, fmt)

	# Change to property and setter
	def cell(self, column: str, row: int):
		if 'Date' in column:
			self.set_column_format(column, datetime.datetime)
		x = self.header_dict[column]-1
		y = row-1
		if not self._grid[y, x, 1]:
			row_string = f"Row {y}"
			cell_string = f"{column} {row_string}"
			if self.hsb:
				# Get Column
				try:
					new_column = self.header_dict_rev[self.header_dict[column] + 1]
					_column = [ch2 for ch in self.ctrl.children() if "Top Row" in ch.texts()[0] for ch2 in ch.children() if new_column in ch2.texts()[0]][0]
				except IndexError:
					_column = [ch2 for ch in self.ctrl.children() if "Top Row" in ch.texts()[0] for ch2 in ch.children() if column in ch2.texts()[0]][0]
				finally:
					while not _column.is_visible():
						self._right.click()
			if self.vsb:
				# Get Row
				_row = [ch for ch in self.ctrl.children() if row_string in ch.texts()[0]][0]
				while not _row.is_visible():
					self._down.click()
			_cell = [ch2 for ch in self.ctrl.children() if ch.texts()[0] == row_string for ch2 in ch.children() if ch2.texts()[0] == cell_string][0]
			"""try:
				_next = [ch.children()[i+1] for ch in self.ctrl.children() if ch.texts()[0] == row_string for i,ch2 in enumerate(ch.children()) if ch2.texts()[0] == cell_string][0]
				while not _next.is_visible():
					self._right.click()
			except IndexError:
				pass
			finally:
				_cell = [ch2 for ch in self.ctrl.children() if ch.texts()[0] == row_string for ch2 in ch.children() if ch2.texts()[0] == cell_string][0]
			if not _cell.is_visible():
				for press in range(len(self.header_dict.keys())):
					self._right.click()"""
			_cell.set_focus()
			_cell.click_input()
			clipboard.EmptyClipboard()
			keyboard.SendKeys("^c")
			try:
				value = self.format_cell(data=clipboard.GetData(), fmt=self._grid[y,x,2])
			except RuntimeError:
				value = None
			except Exception as ex:
				print(ex)
			finally:
				self._grid[y,x,:2] = (value, True)
		return self._grid[y,x,0]

	def sort_with_header(self, column: str, order: str='desc'):
		header = [ch2 for ch in self.ctrl.children() if "Top Row" in ch.texts()[0] for ch2 in ch.children() if column in ch2.texts()[0]][0]
		if order == 'desc':
			header.double_click_input()
			_sleep(1)
			header.double_click_input()
		elif order == 'asc':
			header.double_click_input()
		else:
			raise ValueError

	def select_row(self, row: int):
		row -= 1
		row_string = f"Row {row}"
		_row = [ch.children()[0] for ch in self.ctrl.children() if ch.texts()[0] == row_string][0]
		_row.set_focus()
		_row.click_input()
	"""	if False:
			print('\n\n')
			#print(child.texts()[0])
			child2 = text.children()
			count = 0
			for i in range(6):
				if i >= len(child2):
					continue
				if child2[i].texts()[0] == "Column right":
					right = child2[i]
				elif child2[i].texts()[0] == "Column left":
					left = child2[i]
				if child2[i].friendly_class_name() == "Custom":
					ei = child2[i].element_info
					a = ctrls.uia_controls.ListItemWrapper(ei)
					a.set_focus()
					a.click_input()
					b3 = a.texts()
					clipboard.EmptyClipboard()
					keyboard.SendKeys("^c")
					b4 = clipboard.GetData()
					right.click()
					count += 1
					print(f'\n{b3}, {b4}')
				else:
					print(f'\n{child2[i].get_properties()}')
			for m in range(count):
				left.click()"""


class Combobox(Textbox):
	def __init__(self, name: str, text, window: _Tuple[pwn.WindowSpecification, pwn.WindowSpecification], edit_text: str="", items: _List[str]=None):
		super().__init__(name, text, window, 'Combobox')
		self.edit_text = edit_text
		self.read_only = False
		self.items = items
		if not items:
			self.items = []
		log.debug(f"'{self.text}' {self.__name__} initialized")

CONTROL_DICT = {'button': Button, 'checkbox': Checkbox, 'textbox': Textbox, 'combobox': Combobox}'''

'''
class Tab(Control):
	def __init__(self, name: str, text: str, window: _Tuple[pwn.WindowSpecification, pwn.WindowSpecification], controls):
		super().__init__(name, text, window[1], 'Tab')
		self._controls = controls
		log.debug(f"'{self.text}' {self.__name__} initialized")

	def select(self):
		self.ctrl.select()
		self.window.wait('ready')
		for name,info in self._controls.items():
			_class = info['class']
			kwargs = info['kwargs']
			self.__setattr__(name, _class(**kwargs))


"""class Tab(Control):
	def __init__(self, name: str, text: str, controls: _Dict[str, _List[_Dict[str, _Any]]], window: _Tuple[pwn.WindowSpecification, pwn.WindowSpecification]):
		super().__init__(name, text, window[1])
		self.controls = _defaultdict(list)
		for ctrl_type,ctrl_list in controls.items():
			for ctrl in ctrl_list:
				ctrl = CONTROL_DICT[ctrl_type](**ctrl, window=window)
				self.controls[ctrl_type].append(ctrl)

	def visible(self, x: bool):
		self.visible = x
		for ctrl_list in self.controls.values():
			for ctrl in ctrl_list:
				ctrl.visible = x"""


class TabStrip(Control):
	def __init__(self, name: str, tabs: _List[Tab], window: _Tuple[pwn.WindowSpecification, pwn.WindowSpecification]):
		super().__init__(name, None, window[1])
		self.tabs = {}
		for tab in tabs:
			tab.window = window
			self.tabs[tab.name] = tab

	def change_tab(self, name: str):
		for tab in self.tabs.value():
			tab.visible = False
		self.tabs[name].visible = True

	def visible(self, x: bool):
		self.visible = x
		for ctrl_list in self.controls.values():
			for ctrl in ctrl_list:
				ctrl.visible = x

	def enabled(self, x: bool):
		self.enabled = x
		for ctrl_list in self.controls.values():
			for ctrl in ctrl_list:
				ctrl.enabled = x


CONTROL_DICT['tabstrip'] = TabStrip

"""class Form:
	def __init__(self, name: str, controls: _Dict[str, _List[_Dict[str, _Any]]], win32=True):
		self.name = name
		self.visible = True
		self.controls = _defaultdict(list)
		if win32:
			self._window = app_win32[f'Infor ERP SL (EM) - {self.name}']
		else:
			self._window = app_uia[f'Infor ERP SL (EM) - {self.name}']
		for ctrl_type,ctrl_list in controls.items():
			for ctrl in ctrl_list:
					ctrl = CONTROL_DICT[ctrl_type](**ctrl, window=self._window)
					self.controls[ctrl_type].append(ctrl)

	def visible(self, x: bool):
		self.visible = x
		for ctrl_list in self.controls.values():
			for ctrl in ctrl_list:
				ctrl.visible = x"""
'''

__all__ = ['Textbox', 'Button', 'Checkbox', 'Datebox', 'VerticalScrollbar',
		   'HorizontalScrollbar', 'GridView', 'Tab']