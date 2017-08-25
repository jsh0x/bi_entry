import logging, sqlite3 as sql
from typing import Union, Dict, List, NamedTuple, Set
from platform import uname
from collections import defaultdict
from time import sleep
import threading
import datetime

import pyautogui as pag, pywinauto as pwn, numpy as np
from matplotlib import pyplot as plt
from PIL import Image

from controls import Control, Button, Checkbox, Textbox, Datebox, VerticalScrollbar, HorizontalScrollbar, GridView, Tab
from commands import screenshot, Application
from math_ import get_total_reliability, colorspace_iterator
from types_ import Coordinates, ControlInfo, ControlConfig, GlobalCoordinates, Form, UniqueList, ExtendedImage


# class ControlInfo(NamedTuple):
# 	Id: int
# 	Type: str
# 	Name: str
# 	Form: str
# 	Position: Coordinates
# 	Image: np.ndarray
# 	Reliability: int
#
#
# class ControlConfig(NamedTuple):
# 	Id: int
# 	Name: str
# 	IDs: Set[int]
# 	Total_Reliability: int
#
#
# class GlobalCoordinates(Coordinates):
# 	def __init__(self, left: int=0, top: int=0, right: int=0, bottom: int=0):
# 		super().__init__(left=left, top=top, right=right, bottom=bottom)
# 		self._original_left = left
# 		self._original_top = top
# 		self._original_right = right
# 		self._original_bottom = bottom
# 		self._locals = []
#
#
# class _LocalCoordinates(Coordinates):
# 	def __init__(self, global_container: GlobalCoordinates, left: int = 0, top: int = 0, right: int = 0, bottom: int = 0):
# 		self.global_left = left
# 		self.global_top = top
# 		self.global_right = right
# 		self.global_bottom = bottom
# 		width = np.subtract(right, left)
# 		height = np.subtract(bottom, top)
# 		left = np.subtract(left, global_container.left)
# 		top = np.subtract(top, global_container.top)
# 		right = np.add(left, width)
# 		bottom = np.add(top, height)
# 		super().__init__(left=left, top=top, right=right, bottom=bottom)
# 	# def update(self, global_container: GlobalCoordinates):
# 	# 	width = np.subtract(self.right, self.left)
# 	# 	height = np.subtract(self.bottom, self.top)
# 	# 	left = np.add(self.left, global_container.left)
# 	# 	top = np.add(self.top, global_container.top)
# 	# 	right = np.add(left, width)
# 	# 	bottom = np.add(top, height)
# 	# 	self.global_left, self.global_top, self.global_right, self.global_bottom = left, top, right, bottom
#
#
# class GlobalCoordinates(Coordinates):
# 	def __init__(self, left: int=0, top: int=0, right: int=0, bottom: int=0):
# 		super().__init__(left=left, top=top, right=right, bottom=bottom)
# 		self._original_left = left
# 		self._original_top = top
# 		self._original_right = right
# 		self._original_bottom = bottom
# 		self._locals = []
#
# 	def add_local(self, name: str, left: int=0, top: int=0, right: int=0, bottom: int=0):
# 		local_coord = _LocalCoordinates(left=left, top=top, right=right, bottom=bottom, global_container=self)
# 		self.__setattr__(name, local_coord)
# 		self._locals.append(name)
#
# 	def __contains__(self, item: _LocalCoordinates):
# 		if self.left > item.left:
# 			return False
# 		elif self.right < item.right:
# 			return False
# 		elif self.top > item.top:
# 			return False
# 		elif self.bottom < item.bottom:
# 			return False
# 		else:
# 			return True
#
# 	# def adjust_coords(self):
# 	# 	for name in self._locals:
# 	# 		old_local = self.__getattribute__(name)
# 	# 		new_local = _LocalCoordinates(global_container=self, left=old_local.left+self.left, top=old_local.top+self.top, right=old_local.right, bottom=old_local.bottom)
# 	# 		self.__delattr__(name)
# 	# 		self.__setattr__(name, new_local)
# 	#
# 	# def coords_changed(self):
# 	# 	if (self._original_left, self._original_top, self._original_right, self._original_bottom) != (self.left, self.top, self.right, self.bottom):
# 	# 		return True
# 	# 	else:
# 	# 		return False
# 	#
# 	# def check_coords(self):
# 	# 	if self.coords_changed():
# 	# 		self.adjust_coords()


# def array_splicer_OLD(a: Union[np.ndarray,str], mode: str='split'):
# 	dtypes_dict = {'uint8': np.uint8, 'uint16': np.uint16, 'uint32': np.uint32,
# 	          'int8': np.int8, 'int16': np.int16, 'int32': np.int32,
# 	          'float16': np.float16, 'float32': np.float32, 'float64': np.float64}
# 	retval = None
# 	if mode == 'split' and type(a) is np.ndarray:
# 		if a.ndim == 3:
# 			string1 = ""
# 			for val1 in a:
# 				string2 = ""
# 				for val2 in val1:
# 					string3 = ""
# 					for val3 in val2:
# 						string3 += f"{val3},"
# 					string2 += f"{string3[:-1]},,"
# 				string1 += f"{string2[:-2]},,,"
# 			retval = string1[:-3]
# 		elif a.ndim == 2:
# 			string1 = ""
# 			for val1 in a:
# 				string2 = ""
# 				for val2 in val1:
# 					string2 += f"{val2},"
# 				string1 += f"{string2[:-1]},,"
# 			retval = string1[:-2]
# 		elif a.ndim == 1:
# 			string1 = ""
# 			for val1 in a:
# 				string1 += f"{val1},"
# 			retval = string1[:-1]
# 		retval += f";{str(a.dtype)}"
# 		return retval
# 	elif mode == 'join' and type(a) is str:
# 		a, d_str = a.split(';')
# 		dtype = dtypes_dict.get(d_str, np.int)
# 		list1 = []
# 		if ',,,' in a:
# 			for string1 in a.split(',,,'):
# 				list2 = []
# 				for string2 in string1.split(',,'):
# 					list3 = []
# 					for string3 in string2.split(','):
# 						list3.append(dtype(string3))
# 					list2.append(list3)
# 				list1.append(list2)
# 		elif ',,' in a:
# 			for string1 in a.split(',,'):
# 				list2 = []
# 				for string2 in string1.split(','):
# 					list2.append(dtype(string2))
# 				list1.append(list2)
# 		elif ',' in a:
# 			for string1 in a.split(','):
# 				list1.append(dtype(string1))
# 		retval = np.array(list1, dtype=dtype)
# 		return retval
# 	else:
# 		raise ValueError(f"Invalid mode specification: '{mode}', must be either 'split' for ndarrays or 'join' for strings"
def array_splicer(a: Union[np.ndarray,str], mode: str='split', retval=None, _original=True, dtype=None):
	dtypes_dict = {'uint8': np.uint8, 'uint16': np.uint16, 'uint32': np.uint32,
	          'int8': np.int8, 'int16': np.int16, 'int32': np.int32,
	          'float16': np.float16, 'float32': np.float32, 'float64': np.float64}
	if mode == 'split' and type(a) is np.ndarray:
		sep = ',' * a.ndim
		string1 = ""
		if a.ndim > 1:
			for val1 in a[:]:
				val2 = array_splicer(val1, mode, retval=retval, _original=False)
				string1 += f"{val2}{sep}"
		elif a.ndim == 1:
			for val1 in a:
				string1 += f"{val1}{sep}"
		retval = string1[:-a.ndim]
		if _original:
			retval += f";{str(a.dtype)}"
		return retval
	elif mode == 'join' and type(a) is str:
		if _original:
			a, d_str = a.split(';')
			dtype = dtypes_dict.get(d_str, np.int)
		sep = ','
		while sep in a:
			sep += ','
		else:
			sep = sep[:-1]
		list1 = []
		if len(sep) > 1:
			for string1 in a.split(sep):
				val1 = array_splicer(string1, mode, retval=retval, _original=False, dtype=dtype)
				list1.append(val1)
		else:
			for string1 in a.split(sep):
				list1.append(dtype(string1))
		retval = list1
		if _original:
			retval = np.array(list1, dtype=dtype)
		return retval
	else:
		raise ValueError(f"Invalid mode specification: '{mode}', must be either 'split' for ndarrays or 'join' for strings")


def convert_array(value: bytes) -> np.ndarray:
	return array_splicer(bytes.decode(value, encoding='utf-8'), mode='join')


def adapt_array(value: np.ndarray) -> bytes:
	return bytes(array_splicer(value, mode='split'), encoding='utf-8')


def convert_coordinates(value: bytes) -> Coordinates:
	return Coordinates(*array_splicer(bytes.decode(value, encoding='utf-8'), mode='join').tolist())


def adapt_coordinates(value: Coordinates) -> bytes:
	# return bytes(value)
	value = np.array(value.to_list(), dtype=np.uint32)
	return bytes(array_splicer(value, mode='split'), encoding='utf-8')


def convert_image(value: bytes) -> Image:
	return ExtendedImage(array_splicer(bytes.decode(value, encoding='utf-8'), mode='join'))


def adapt_image(value: ExtendedImage) -> bytes:
	return bytes(value)

sql.register_adapter(np.ndarray, adapt_array)
sql.register_adapter(Coordinates, adapt_coordinates)
sql.register_adapter(ExtendedImage, adapt_image)
sql.register_converter('ARRAY', convert_array)
sql.register_converter('COORDINATES', convert_coordinates)
sql.register_converter('IMAGE', convert_image)


# Initial Variables
# SkeletonClass = namedtuple('SkeletonClass', ['control', 'criteria'])
# TODO: improve shorthand dictionary for "common" terms (Serial = srl, Number = num, etc)
shorthand_dict = {'serial': 'srl', 'number': 'num', 'miscellaneous': 'misc', 'form': 'frm',
                  'quantity': 'qty', 'quality': 'qlty', 'reason': 'rsn', 'location': 'loc',
                  'generate': 'gen', 'process': 'proc', 'detail': 'dtl', 'window': 'win',
                  'button': 'btn', 'checkbox': 'chk', 'textbox': 'txt', 'datebox': 'dte',
                  'verticalscrollbar': 'vsb', 'gridview': 'grd', 'tab': 'tab', 'customer': 'cust',
                  'horizontalscrollbar': 'hsb', 'combobox': 'cmb',  'line': 'ln', 'service': 'svc',
                  'order': 'ord', 'description': 'desc', 'history': 'hist', 'operation': 'optn',
                  'operator': 'optr', 'floor': 'flr', 'recieved': 'rcvd', 'resolution': 'res',
                  'complete': 'cmplt', 'repair': 'rpr', 'statement': 'stmnt', 'transaction': 'trnctn',
                  'clear': 'clr', 'filter': 'fltr', 'include': 'incl', 'debug': 'dbg',
                  'document': 'doc'}
vowels = {'a', 'e', 'i', 'o', 'u', 'y'}
ctrl_dict = {'Button': Button, 'Checkbox': Checkbox, 'Textbox': Textbox, 'Datebox': Datebox,
			 'VerticalScrollBar': VerticalScrollbar, 'HorizontalScrollBar': HorizontalScrollbar,
			 'GridView': GridView, 'Tab': Tab}
ctrl_pfx_dict = {'Button': 'btn', 'Checkbox': 'chk', 'Textbox': 'txt', 'Datebox': 'dte',
				 'VerticalScrollBar': 'vsb', 'HorizontalScrollBar': 'hsb',
				 'GridView': 'grd', 'Tab': 'tab'}
log = logging.getLogger("root")
colors = [np.array([255, 000, 000], dtype=np.uint8), np.array([000, 255, 000], dtype=np.uint8), np.array([000, 000, 255], dtype=np.uint8), np.array([255, 128, 000], dtype=np.uint8),
			          np.array([128, 000, 255], dtype=np.uint8), np.array([000, 128, 000], dtype=np.uint8), np.array([000, 220, 128], dtype=np.uint8), np.array([255, 000, 255], dtype=np.uint8)]


conn = sql.connect(database='vision.db', detect_types=sql.PARSE_DECLTYPES)
c = conn.cursor()
# c.execute("SELECT name FROM sqlite_master WHERE type='table'")
# tables = map(lambda x: x[0], c.fetchall())

# c.execute("DROP TABLE cv_data")
# c.execute("DROP TABLE cv_configs")
# conn.commit()
# quit()

c.execute("CREATE TABLE IF NOT EXISTS cv_data("
          "Id INTEGER PRIMARY KEY, "
          "Type TEXT, "
          "Name TEXT, "
          "Form TEXT, "
          "Position COORDINATES, "
          "Image IMAGE, "
          "Reliability INTEGER DEFAULT 0, "
          "OS_Name TEXT, "
          "OS_General_Version TEXT, "
          "OS_Specific_Version TEXT, "
          "Computer_Name TEXT, "
          "Username TEXT"
          ")")
c.execute("CREATE TABLE IF NOT EXISTS cv_configs("
          "Id INTEGER PRIMARY KEY, "
          "Name TEXT, "
          "Config ARRAY, "
          "Total_Reliability REAL"
          ")")
conn.commit()
# values = [('Name1', np.arange(9, dtype=np.uint16).reshape((3,3))), ('Name2', np.arange(16, dtype=np.uint16).reshape((4,4))), ('Name3', np.arange(4, dtype=np.uint16).reshape((2,2))), ('Name4', np.arange(16384, dtype=np.uint16).reshape((128,128)))]
# c.executemany("INSERT INTO cv_configs(name,config) VALUES (?, ?)", values)
# conn.commit()


class CV_Config:
	__slots__ = ['_window', '_username', '_window_gc', '_window_image',
	             '_cropped_window_image', 'forms', 'controls', '_control_ids',
	             '_config', '__dict__']

	def __init__(self, **kwargs):
		"""Sets the global coordinates to that of the window"""
		if 'window' in kwargs.keys():
			window = kwargs['window']
			props = window.get_properties()
			coord = props['rectangle']
			self._window = window
			self._window_gc = GlobalCoordinates(left=coord.left+8, top=coord.top+7, right=coord.right-8, bottom=coord.bottom-2)
			self._window_image = self.scrn[self.window_gc.top:self.window_gc.bottom, self.window_gc.left:self.window_gc.right].view()
			self._cropped_window_image = self.window_image[7:748, 8:1015].copy()
			self.forms = set([])
			self.controls = set([])
			self._all_controls = set([])
			self._control_ids = UniqueList()
			self._config = None
			# TODO: Iterable forms/controls initlist
			# self._worker = DisplayThread(1, self.window_image)
		# elif 'coord' in kwargs.keys():
		# 	coord = kwargs['coord']
		# 	self.window_gc = GlobalCoordinates(left=coord.left, top=coord.top, right=coord.right, bottom=coord.bottom)
		# 	self._window = None
		# 	self.scrn = np.array(screenshot())
		# 	self.window_image = self.scrn[self.window_gc.top:self.window_gc.bottom, self.window_gc.left:self.window_gc.right].view()
		# 	self.controls = defaultdict(dict)
		else:
			raise ValueError("Expected at least one argument for either 'coord' or 'window', got None")
		if 'controls' in kwargs.keys():
			controls = kwargs['controls']
			self.add_control(*controls)

	@property
	def scrn(self):
		return np.array(screenshot(), dtype=np.uint8)

	@property
	def window_gc(self):
		props = self._window.get_properties()
		coord = props['rectangle']
		self._window_gc.update(left=coord.left+8, top=coord.top+7, right=coord.right-8, bottom=coord.bottom-2)
		return self._window_gc

	@property
	def window_image(self):
		return self.scrn[self.window_gc.top:self.window_gc.bottom, self.window_gc.left:self.window_gc.right].view()

	@property
	def config(self):
		return self._config

	@config.setter
	def config(self, value):
		if type(value) is ControlConfig:
			self.controls.clear()
			self._control_ids.clear()
			for name in self.window_gc._locals:
				self._window_gc.__delattr__(name)
			self.window_gc._locals.clear()
			self._add_control(*value.IDs)
			self._config = value
		else:
			raise TypeError(f"Type 'ControlConfig' expected, got '{type(value)}' instead")

	@property
	def _total_reliability(self):
		return get_total_reliability(np.array(list(map(lambda x: x.Reliability, self._all_controls)), np.uint32))

	def check_control(self, ctrl: Union[Control, ControlInfo]):
		"""Checks if the given control still exists at its previous known location"""
		if type(ctrl) is Control:
			ctrl = self.window_gc.__getattribute__(ctrl.__name__)
			ctrl_image = self.window_image[ctrl.top:ctrl.bottom, ctrl.left:ctrl.right].view()
		elif type(ctrl) is ControlInfo:
			ctrl_image = self.controls[ctrl.Form][ctrl.Type][ctrl.Name].Image
			ctrl = ctrl.Position
		coords = pag.locate(needleImage=Image.fromarray(ctrl_image), haystackImage=Image.fromarray(self.window_image), grayscale=True)
		if coords:
			val = np.subtract(np.array(ctrl.coords(), dtype=np.int16), np.array([coords[0], coords[1], coords[0] + coords[2], coords[1] + coords[3]], dtype=np.int16)).sum().sum()
			if val < 4:
				return True
			else:
				return False
		else:
			return False

	def add_form(self, name: str):
		name = name.strip()
		if name.startswith('frm_'): #and name.split('_', 1)[1].isupper():
			pass
		else:
			if ' ' in name:
				names = name.split(' ')
				name = 'frm_'
				last = None
				for n in names:
					if n.isupper():
						value = n+'_'
						current = 'upper'
					elif n.istitle():
						value = n[0]
						current = 'title'
					else:
						continue
					if last is not None and (current == 'upper' and last == 'title'):
						name += '_'+value
					else:
						name += value
					last = current
			else:
				name2 = ''
				for char in name:
					if char.isupper():
						name += char
				name = name2
		name = name.strip('_')
		if name not in self.forms:
			self.__setattr__(name, Form)
			self.forms.add(name)

	def add_control(self, form, username, *args):
		_sysinfo = uname()
		if form not in self.forms:
			self.add_form(form)
			# raise ValueError()
		for ctrl in args:
			pfx = ctrl_pfx_dict[ctrl.__class__.__name__]
			sfx = ctrl.__name__.strip()
			# sfx2 = ''
			# if ' ' in sfx:
			# 	sfxs = sfx.split(' ')
			# else:
			# 	sfxs = [sfx]
			# for sfx in sfxs:
			# 	if len(sfx) > 3:
			# 		chars = []
			# 		for char in sfx[1:-1]:
			# 			if char not in vowels:
			# 				chars.append(char)
			# 		print(chars)
			# 		if len(chars) % 2 != 0 and len(chars) > 1:
			# 			char = chars[(len(chars) // 2) + 1]
			# 		else:
			# 			char = chars[len(chars) // 2]
			# 		sfx2 += sfx[0]+char+sfx[-1]
			# 	else:
			# 		sfx2 += sfx
			# sfx = sfx2.strip('_')
			control_name = pfx+'_'+sfx.lower()

			if ctrl.__class__.__name__ == 'Tab':
				self.window_gc.add_local(name=control_name, left=ctrl.coordinates.left, top=ctrl.coordinates.top + 5, right=ctrl.coordinates.right, bottom=ctrl.coordinates.bottom + 7)
			else:
				self.window_gc.add_local(name=control_name, left=ctrl.coordinates.left, top=ctrl.coordinates.top + 6, right=ctrl.coordinates.right - 1, bottom=ctrl.coordinates.bottom + 5)
			coord = self.window_gc.__getattribute__(control_name)
			img = ExtendedImage(self.window_image[coord.top:coord.bottom, coord.left:coord.right])
			# plt.imshow(img.array)
			# plt.show()
			ctrl.coordinates = Coordinates(left=coord.left, top=coord.top, right=coord.right, bottom=coord.bottom)
			c.execute("SELECT [Id] FROM cv_data WHERE [Type] = ? AND [Name] = ? AND [Form] = ? AND [Position] = ? AND [Image] = ?",
			          (ctrl.__class__.__name__, control_name, form, ctrl.coordinates, img))
			val = c.fetchone()
			if not val:
				c.execute("INSERT INTO cv_data (Type,Name,Form,Position,Image,OS_Name,OS_General_Version,OS_Specific_Version,Computer_Name,Username) VALUES (?,?,?,?,?,?,?,?,?,?)",
				          (ctrl.__class__.__name__, control_name, form, ctrl.coordinates, img, _sysinfo.system, _sysinfo.release, _sysinfo.version, _sysinfo.node, username))
				conn.commit()
				c.execute("SELECT [Id] FROM cv_data WHERE [Type] = ? AND [Name] = ? AND [Form] = ? AND [Position] = ? AND [Image] = ?",
				          (ctrl.__class__.__name__, control_name, form, ctrl.coordinates, img))
				val = c.fetchone()
			c.execute("SELECT [Id],[Type],[Name],[Form],[Position],[Image],[Reliability] FROM cv_data WHERE [Id] = ?", (val[0],))
			val = c.fetchone()
			# print(val)
			ctrl = ControlInfo(*val)
			if ctrl not in self._all_controls:
				self.controls.add(ctrl.Name)
				self.__getattribute__(ctrl.Form).__setattr__(self, ctrl.Name, ctrl)
				self._all_controls.add(ctrl)
			# self._worker._val = choice(colors), ctrl.Position.left, ctrl.Position.top, ctrl.Position.right, ctrl.Position.bottom
				self._control_ids.append(ctrl.Id)
			# self.controls[ctrl.__class__.__name__][ctrl.__name__] = (val, ctrl._kwargs)
			# self._controls[ctrl.__class__.__name__][ctrl.__name__] = SkeletonClass(ctrl.__class__, ctrl.criteria)

	def _add_control(self, *args):
		for ctrl_id in args:
			c.execute("SELECT [Id],[Type],[Name],[Form],[Position],[Image],[Reliability] FROM cv_data WHERE [Id] = ?", (int(ctrl_id),))
			val = c.fetchone()
			ctrl = ControlInfo(*val)
			if ctrl.Form not in self.forms:
				self.__setattr__(ctrl.Form, Form(**{ctrl.Name: ctrl}))
				self.forms.add(ctrl.Form)
			self.window_gc._add_local(ctrl.Name, *ctrl.Position.coords())
			if ctrl not in self._all_controls:
				self.controls.add(ctrl.Name)
				old_kwargs = self.__getattribute__(ctrl.Form).list_attr()
				old_kwargs[ctrl.Name] = ctrl
				self.__setattr__(ctrl.Form, Form(**old_kwargs))

				self._all_controls.add(ctrl)
				self._control_ids.append(ctrl.Id)

	def load_previous_configuration(self, name: str):
		c.execute("SELECT * FROM cv_configs WHERE [Name] = ?", (name,))
		exists = c.fetchone()
		if exists:
			self.config = ControlConfig(*exists)
		else:
			raise ValueError(f"Config with name '{name}' does not exist")

	def save_current_configuration(self, name: str=None):
		if name is not None:
			c.execute("SELECT * FROM cv_configs WHERE [Name] = ?", (name,))
			exists = c.fetchone()
			if exists:
				c.execute("UPDATE cv_configs SET [Config] = ?,[Total_Reliability] = ? WHERE [Name] = ?", (np.array(list(self._control_ids), dtype=np.uint16), self._total_reliability, name))
			else:
				c.execute("INSERT INTO cv_configs ([Name],[Config],[Total_Reliability]) VALUES (?,?,?)", (name, np.array(list(self._control_ids), dtype=np.uint16), self._total_reliability))
			conn.commit()
		elif self.config is None:
			raise ValueError("Name required if not using saved/loaded config")
		else:
			c.execute("UPDATE cv_configs SET [Config] = ?,[Total_Reliability] = ? WHERE [Name] = ?", (np.array(list(self._control_ids), dtype=np.uint16), self._total_reliability, self.config.Name))
			conn.commit()

	def get_configs(self):
		c.execute("SELECT [Id],[Name],[Config] FROM cv_configs")
		return c.fetchall()

	# TODO: Maybe change to 'control_equal', and just supply db record as second argument
	def control_equal_to_db(self, ctrl: Control):
		name = ctrl.__name__
		ctrl = self.window_gc.__getattribute__(name)
		c.execute(f"SELECT position,image FROM cv_data WHERE name = '{name}'")
		coords = c.fetchone()
		if coords:
			coords,image = coords
			if (ctrl.left, ctrl.top, ctrl.right, ctrl.bottom) == (coords[0], coords[1], coords[0]+coords[2], coords[1]+coords[3]):
				ctrl_image = self.window_image[ctrl.top:ctrl.bottom, ctrl.left:ctrl.right].view()
				diff_image = np.subtract(ctrl_image, image).sum().sum()
				if not diff_image:
					return True
				else:
					return False
			else:
				return False
		else:
			raise ValueError(f"Control '{name}' does not exist in database.")

	def plot(self, img=None):
		if img is None:
			img = self.window_image
		plt.imshow(img)
		plt.show()
	# def TEST_WINDOW(self):
	# 	# Create figure and axes
	# 	window_image2 = self.window_image.copy()
	#
	# 	# Display the image
	# 	plt.imshow(self.window_image)
	# 	# Add the lines to the Axes
	# 	ymax, ymin = plt.ylim()
	# 	xmin, xmax = plt.xlim()
	# 	ymax, ymin, xmax, xmin = map(sum, [[ymax, 0.5], [ymin, 0.5], [xmax, 0.5], [xmin, 0.5]])
	# 	rng = np.arange(ymin, ymax, 100, dtype=np.intp)
	# 	hlines = np.array([np.array([y-1, y+1], dtype=np.intp) for y in rng if y-1 > ymin and y+2 < ymax], dtype=np.intp)
	# 	edge1 = np.array([np.array([y, y + 1], dtype=np.intp) for y in rng if y - 1 < ymin], dtype=np.intp)
	# 	edge2 = np.array([np.array([y-1, y], dtype=np.intp) for y in rng if y + 2 > ymax], dtype=np.intp)
	# 	rng = np.arange(ymin, ymax, 10, dtype=np.intp)
	# 	# self.window_image[hlines] += np.array([128, 128, 128], dtype=np.uint8)
	# 	# self.window_image[edge1] += np.array([128, 128, 128], dtype=np.uint8)
	# 	# self.window_image[edge2] += np.array([128, 128, 128], dtype=np.uint8)
	# 	# self.window_image[rng] += np.array([128, 128, 128], dtype=np.uint8)
	#
	# 	# self.window_image = self.window_image[7:748, 8:1015]
	#
	# 	h,w = self.window_image.shape[:2]
	# 	z = np.zeros(self.window_image.shape[-1], dtype=np.uint8)
	# 	self.window_image[:7] = z
	# 	self.window_image[748:] = z
	# 	self.window_image[:, :8] = z
	# 	self.window_image[:, 1015:] = z
	# 	self.window_image[9:36, 9:np.floor_divide(w, 2)] = z
	# 	self.window_image[36:64, np.floor_divide(w, 2):-9] = z
	# 	self.window_image[64:89, 9:np.multiply(np.floor_divide(w, 5), 3)] = z
	# 	self.window_image[89:725, 9:-9] = z
	# 	self.window_image[729:746, 9:np.multiply(np.floor_divide(w, 5), 1)] = z
	# 	self.window_image[729:746, np.multiply(np.floor_divide(w, 5), 4):-9] = z
	# 	plt.imshow(self.window_image)
	# 	plt.show()
	#
	# 	rng = np.arange(xmin, xmax, 100, dtype=np.intp)
	# 	vlines = np.array([np.array([x - 1, x + 1], dtype=np.intp) for x in rng if x - 1 > xmin and x + 2 < xmax], dtype=np.intp)
	# 	edge1 = np.array([np.array([x, x + 1], dtype=np.intp) for x in rng if x - 1 < xmin], dtype=np.intp)
	# 	edge2 = np.array([np.array([x-1, x], dtype=np.intp) for x in rng if x + 2 > xmax], dtype=np.intp)
	# 	rng = np.arange(xmin, xmax, 10, dtype=np.intp)
	# 	window_image2[:, vlines] += np.array([128, 128, 128], dtype=np.uint8)
	# 	window_image2[:, edge1] += np.array([128, 128, 128], dtype=np.uint8)
	# 	window_image2[:, edge2] += np.array([128, 128, 128], dtype=np.uint8)
	# 	window_image2[:, rng] += np.array([128, 128, 128], dtype=np.uint8)
	# 	plt.imshow(window_image2)
	# 	plt.show()
	# @property
	# def controls(self):
	# 	"""Returns a more friendly version of the controls dictionary"""
	# 	retval = self._controls.copy()
	# 	for ctrl,names in self._controls.items():
	# 		for name in names:
	# 			retval[ctrl][name] = self._controls[ctrl][name][0](**self._controls[ctrl][name][1])
	# 	return retval
	#
	# @controls.setter
	# def controls(self, value1):
	# 	pass
# def convert_configs(value: bytes) -> list:
# 	value = bytes.decode(value, encoding="utf-8").split('```')
# 	retval = []
# 	for v in value:
# 		k, names = v.split('``;')
# 		for name in names.split('`;`'):
# 			name,val = name.split('`;;')
# 			kwargs = {}
# 			for arg in val.split(';``'):
# 				k2, v2 = arg.split(';`;')
# 				kwargs[k2] = v2
# 			retval.append(ctrl_dict[k](**kwargs))
# 	return retval
#
#
# def adapt_configs(value: dict) -> bytes:
# 	string1 = ""
# 	for ctrl,names in value.items():
# 		string2 = ""
# 		for name in names:
# 			string3 = ""
# 			for k,v in value[ctrl][name][1].items():
# 				if type(v) is dict:
# 					string4 = ""
# 					for k2,v2 in v.items():
# 						string4 += f"{k2};;`{v2};;;"
# 					string3 += f"{k};`;{string4[:-3]};``"
# 				else:
# 					string3 += f"{k};`;{v};``"
# 			string2 += f"{name}`;;{string1[:-3]}`;`"
# 		string1 += f"{ctrl}``;{string2[:-3]}```"
# 	print(string1[:-3])
# 	return bytes(string1[:-3], encoding='utf-8')
# sql.register_adapter(dict, adapt_configs)
# sql.register_converter('config', convert_configs)

class DisplayThread(object):
	def __init__(self, interval=1, *args):
		self.interval = interval
		self._val = None
		thread = threading.Thread(target=self.run, args=args)
		thread.daemon = True                            # Daemonize thread
		thread.start()                                  # Start the execution

	def run(self, img):
		""" Method that runs forever """
		while True:
			if self._val is not None:
				clr, left, top, right, bottom = self._val
				img[top:bottom + 1, left] = clr
				img[top:bottom + 1, right] = clr
				img[top, left:right + 1] = clr
				img[bottom, left:right + 1] = clr
				self._val = None
			plt.imshow(img)
			plt.draw()


def print_db_simple():
	c.execute("SELECT * FROM cv_data ORDER BY [Id]")
	for val in c.fetchall():
		print(val)
	c.execute("SELECT * FROM cv_configs ORDER BY [Id]")
	for val in c.fetchall():
		print(val)


def print_db_sleek():
	ID_len = ctrl_type_len = ctrl_name_len = form_len = coord_len = img_len = rl_len = opv_len = opv2_len = usr_len = cpu_len = op_len = 0
	c.execute("SELECT * FROM cv_data ORDER BY [Form] ASC, [Type] ASC, [Reliability] DESC, [Name] ASC")
	vals = c.fetchall()
	for val in vals:
		ID, ctrl_type, ctrl_name, form, coord, img, rl, op, opv, opv2, cpu, usr = val
		ID_len = max(ID_len, len(str(ID)))
		ctrl_type_len = max(ctrl_type_len, len(str(ctrl_type)))
		ctrl_name_len = max(ctrl_name_len, len(str(ctrl_name)))
		form_len = max(form_len, len(str(form)))
		coord_len = max(coord_len, len(str(coord)))
		img_len = max(img_len, len(str(img)))
		rl_len = max(rl_len, len(str(rl)))
		op_len = max(op_len, len(str(op)))
		opv_len = max(opv_len, len(str(opv)))
		opv2_len = max(opv2_len, len(str(opv2)))
		usr_len = max(usr_len, len(str(usr)))
		cpu_len = max(cpu_len, len(str(cpu)))

	ID_old = ID = 'ID'.center(ID_len + 2)
	ctrl_old = ctrl = 'Control'.center(ctrl_name_len + ctrl_type_len + 7)
	form_old = form = 'Form'.center(form_len + 4)
	coord_old = coord = 'Coordinates'.center(coord_len + 4)
	img_old = img = 'Image Array'.center(img_len + 4)
	cpu_old = cpu = 'User'.center(usr_len + cpu_len + 6)
	op_old = op = 'Operating System'.center(op_len + opv_len + opv2_len + 8)
	rl_old = rl = 'Reliability'.center(13)

	string = f"{ID}|{ctrl}|{form}|{coord}|{img}|{cpu}|{op}|{rl}"
	print(string)
	print('-' * ((len(ID) + len(ctrl) + len(form) + len(coord) + len(img) + len(cpu) + len(op) + len(rl) + 7)))
	last = None
	for val in vals:
		ID, ctrl_type, ctrl_name, form, coord, img, rl, op, opv, opv2, cpu, usr = val
		if last is None:
			last = form
		elif last != form:
			string = f"{' ' * len(ID_old)}|{' ' * len(ctrl_old)}|{' ' * len(form_old)}|{' ' * len(coord_old)}|{' ' * len(img_old)}|{' ' * len(cpu_old)}|{' ' * len(op_old)}|{' ' * len(rl_old)}"
			print(string)
			last = form
		ID = str(ID).rjust(ID_len)
		ctrl_name = str(ctrl_name).rjust(ctrl_name_len)
		ctrl_type = (str(ctrl_type) + ')').ljust(ctrl_type_len + 1)
		form = str(form).center(form_len)
		coord = str(coord).center(coord_len)
		img = str(img).center(img_len)
		op = str(op).rjust(op_len)
		opv2 = str(opv2 + ']').ljust(opv2_len + 1)
		usr = str(usr).rjust(usr_len)
		cpu = str(cpu + ')').ljust(cpu_len + 1)
		rl = str(rl).ljust(10)
		string = f" {ID} |  {ctrl_name} ({ctrl_type}  |  {form}  |  {coord}  |  {img}  |  {usr}({cpu}  |  {op} {opv}[v{opv2}  |      {rl}"
		print(string)
	print('\n\n')

	ID_len = name_len = ctrl_len = rl_len = 0
	c.execute("SELECT * FROM cv_configs")
	vals = c.fetchall()
	for val in vals:
		ID, name, ctrl, rl = val
		ID_len = max(ID_len, len(str(ID)))
		name_len = max(name_len, len(str(name)))
		ctrl_len = max(ctrl_len, len(str(ctrl)))
		rl_len = max(rl_len, len(str(rl)))
	for val in vals:
		ID, name, ctrl, rl = val
		ID = str(ID).rjust(ID_len)
		name = str(name).rjust(name_len)
		ctrls = ""
		startx = None
		x_temp = None
		for i, x in enumerate(sorted(ctrl)):
			if x_temp is None:
				x_temp = int(x)
				startx = str(x_temp)
			elif abs(x - x_temp) != 1:
				if (int(ctrl[i - 1]) - int(startx)) > 1:
					ctrls += f"{startx}-{str(int(ctrl[i-1]))}, "
				else:
					ctrls += f"{startx}, "
			elif abs(x - x_temp) == 1:
				x_temp = int(x)
		else:
			if (int(ctrl[i - 1]) - int(startx)) >= 1:
				ctrls += f"{startx}-{str(int(ctrl[i]))}"
			elif (x_temp - int(startx)) == 1:
				ctrls += f"{startx}, {str(int(ctrl[i]))}"
			else:
				ctrls += f"{startx}"

		if ctrls.endswith(', '):
			ctrls = ('[' + ctrls[:-2] + ']' + f"({i+1})").center(15)
		else:
			ctrls = ('[' + ctrls + ']' + f"({i+1})").center(15)
		rl = str(rl).ljust(rl_len)
		string = f"{ID} -  {name} {ctrls} {rl}"
		print(string)


print_it = True

if print_it:
	print_db_sleek()
else:
	print_db_simple()

def main():
	filepath = 'C:/Users/mfgpc00/AppData/Local/Apps/2.0/QQC2A2CQ.YNL/K5YT3MK7.VDY/sl8...ient_002c66e0bc74a4c9_0008.0003_1fdd36ef61625f38/WinStudio.exe'
	with Application(filepath) as app:
			usr = "jredding"
			pwd = "JRJul17!"
			app.log_in(usr, pwd)
			cv = CV_Config(window=app._win)
			# app.open_form('Miscellaneous Issue')
			# cv.add_control('frm_MiscIssue', usr,
			#                Button(window=app._all_win, criteria={'best_match': "ProcessButton", 'control_type': "Button", 'top_level_only': False}, control_name='proc'),
			#                Textbox(window=app._all_win, criteria={'best_match': "Item:Edit0", 'visible_only': True}, fmt=('alphabetic', 'numeric', 'punctuation', 'upper'), control_name='item'),
			#                Textbox(window=app._all_win, criteria={'best_match': "Location:Edit", 'top_level_only': False}, control_name='loc'),
			#                Textbox(window=app._all_win, criteria={'best_match': "Quantity:Edit", 'top_level_only': False}, control_name='qty'),
			#                Textbox(window=app._all_win, criteria={'best_match': "Reason:Edit", 'top_level_only': False}, control_name='rsn'),
			#                Textbox(window=app._all_win, criteria={'best_match': "Document Number:Edit", 'top_level_only': False}, control_name='doc_num'),
			#                Textbox(window=app._all_win, criteria={'best_match': "Generate Qty:Edit", 'visible_only': True}, control_name='gen_qty'),
			# 			   Tab(window=app._all_win, criteria={'best_match': "DetailTabControl"}, name='Detail', controls={}, control_name='dtl'),
			# 			   Tab(window=app._all_win, criteria={'best_match': "Serial NumbersTabControl"}, name='Serial Numbers', controls={}, control_name='srl_num'))
			# cv.save_current_configuration('frm_MiscIssue')
			# quit()

			# app.open_form('Units')
			# cv.add_control('frm_Units', usr,
			#                Textbox(window=app._all_win, criteria={'best_match': "Unit:Edit"}, fmt=('alphabetic', 'numeric', 'upper'), control_name='unit'),
			#                Textbox(window=app._all_win, criteria={'best_match': "Description:Edit"}, control_name='desc'),
			#                Textbox(window=app._all_win, criteria={'best_match': "Item:Edit", 'enabled_only': True}, fmt=('alphabetic', 'numeric', 'punctuation', 'upper'), control_name='item'),
			#                Textbox(window=app._all_win, criteria={'best_match': 'Customer:Edit1'}, control_name='cust'),
			#                Textbox(window=app._all_win, criteria={'best_match': 'Unit Status Code:Edit'}, fmt=('alphabetic', 'numeric', 'punctuation', 'upper'), control_name='unit_status_code'),
			#                Textbox(window=app._all_win, criteria={'best_match': 'Ship To:Edit1'}, control_name='ship_to'),
			#                Textbox(window=app._all_win, criteria={'best_match': 'ESN:Edit'}, fmt=('alphabetic', 'numeric', 'upper'), control_name='esn'),
			#                Button(window=app._all_win, criteria={'auto_id': "SROLinesButton", 'control_type': "Button", 'top_level_only': False}, control_name='svc_order_lines'),
			#                Button(window=app._all_win, criteria={'auto_id': "uf_OverrideStatusBtn", 'control_type': "Button", 'top_level_only': False}, control_name='change_status'),
			#                Tab(window=app._all_win, criteria={'best_match': "Owner HistoryTabControl"}, name='Owner History', controls={}, control_name='owner_history'),
			# 	           Tab(window=app._all_win, criteria={'best_match': "Service HistoryTabControl"}, name='Service History', controls={}, control_name='svc_history'),
			# 	           Tab(window=app._all_win, criteria={'best_match': "UNIT DATATabControl"}, name='UNIT DATA', controls={}, control_name='unit_data'))
			# print('Open Owner History Tab')
			# sleep(5)
			# cv.add_control('frm_Units', usr,
			#                GridView(window=app._all_win, criteria={'parent': app._win2.child_window(best_match='Alt. 6/7 Digit SN:GroupBox'), 'auto_id': "ConsumerHistoryGrid", 'control_type': "Table",
			#                                         'top_level_only': False}, control_name='owner_history'))
			# print('Open Service History Tab')
			# sleep(5)
			# cv.add_control('frm_Units', usr,
			#                Button(window=app._all_win, criteria={'auto_id': "BtnSROLineView", 'control_type': "Button", 'top_level_only': False}, control_name='view'),
			#                GridView(window=app._all_win, criteria={'parent': app._win2.child_window(best_match='Resource:GroupBox'), 'auto_id': "fsTmpSROLineViewsGrid", 'control_type': "Table",
			#                                                        'top_level_only': False}, control_name='svc_history'))
			# cv.save_current_configuration('frm_Units')
			# quit()

			# app.open_form('Service Order Lines')
			# cv.add_control('frm_SRO_Lines', usr,
			#                Textbox(window=app._all_win, criteria={'best_match': "Status:Edit2"}, control_name='status'),
			#                Button(window=app._all_win, criteria={'auto_id': "SROOpersButton", 'control_type': "Button", 'top_level_only': False}, control_name='sro_oprtns'))
			# cv.save_current_configuration('frm_SRO_Lines')
			# quit()

			# app.open_form('Service Order Operations')
			# cv.add_control('frm_SRO_Operations', usr,
			#                Textbox(window=app._all_win, criteria={'best_match': "Status:Edit3"}, control_name='status'),
			#                Datebox(window=app._all_win, criteria={'best_match': "Received:Edit"}, control_name='rec'),
			#                Datebox(window=app._all_win, criteria={'best_match': "Floor:Edit"}, control_name='flr'),
			#                Datebox(window=app._all_win, criteria={'best_match': "F/A:Edit"}, control_name='fa'),
			#                Datebox(window=app._all_win, criteria={'best_match': "Complete:Edit"}, control_name='cp'),
			#                Button(window=app._all_win, criteria={'auto_id': "TransactionsButton", 'control_type': "Button", 'top_level_only': False}, control_name='sro_transactions'),
			#                Tab(window=app._all_win, criteria={'parent': app._win2.child_window(best_match='GeneralTabControl'), 'best_match': "GeneralTabItemControl", }, name='General', controls={}, control_name='gen'),
			#                Tab(window=app._all_win, criteria={'parent': app._win2.child_window(best_match='ReasonsTabControl'), 'best_match': "ReasonsTabItemControl"}, name='Reasons', controls={}, control_name='rsn'))
			# print('Open Reasons Tab')
			# sleep(5)
			# cv.add_control('frm_SRO_Operations', usr,
			#                Textbox(window=app._all_win, criteria={'best_match': "Reason Notes:Edit"}, control_name='rsn_notes'),
			#                Textbox(window=app._all_win, criteria={'best_match': "Resolution Notes:Edit"}, control_name='rso_notes'),
			#                Button(window=app._all_win, criteria={'auto_id': "uf_PrintRepairStatement", 'control_type': "Button", 'top_level_only': False}, control_name='prnt_rpr_sttmnt'),
			#                GridView(window=app._all_win, criteria={'parent': app._win2.child_window(best_match='Tax Code:GroupBox'), 'auto_id': "ReasonsSubGrid", 'control_type': "Table",
			#                                                        'top_level_only': False}, control_name='rsn'))
			# cv.save_current_configuration('frm_SRO_Operations')
			# quit()

			# app.open_form('SRO Transactions')
			# cv.add_control('frm_SRO_Transaction', usr,
			#                Textbox(window=app._all_win, criteria={'best_match': "Date Range:Edit1"}, fmt=datetime.date, control_name='date_range_start'),
			#                Textbox(window=app._all_win, criteria={'best_match': "Date Range:Edit2"}, fmt=datetime.date, control_name='date_range_end'),
			#                Button(window=app._all_win, criteria={'auto_id': "AddlFiltersButton", 'control_type': "Button", 'top_level_only': False}, control_name='add_fltr'),
			#                Button(window=app._all_win, criteria={'auto_id': "BtnFilterRefresh", 'control_type': "Button", 'top_level_only': False}, control_name='apply_fltr'),
			#                Button(window=app._all_win, criteria={'auto_id': "BtnClearFilter", 'control_type': "Button", 'top_level_only': False}, control_name='clr_fltr'),
			#                Button(window=app._all_win, criteria={'auto_id': "PostBatchButton", 'control_type': "Button", 'top_level_only': False}, control_name='post_batch'),
			#                Checkbox(window=app._all_win, criteria={'auto_id': "FilterPosted", 'top_level_only': False}, control_name='include_posted'),
			#                GridView(window=app._all_win, criteria={'auto_id': "MatlGrid", 'control_type': "Table", 'top_level_only': False}, control_name='transaction'))
			# cv.save_current_configuration('frm_SRO_Transaction')
			# quit()

			# app.open_form('Serial Numbers')
			# cv.add_control('frm_SerNums', usr,
			#                Textbox(window=app._all_win, criteria={'best_match': "S/N:Edit"}, fmt=('alphabetic', 'numeric', 'upper'), control_name='sn'),
			#                Textbox(window=app._all_win, criteria={'best_match': "Status:Edit"}, control_name='status'),
			#                Textbox(window=app._all_win, criteria={'best_match': 'Location:Edit'}, control_name='loc'))
			# cv.save_current_configuration('frm_SerNums')
			# quit()
			app.open_form('Units')
			cv.load_previous_configuration('frm_Units')
			clrs = colorspace_iterator(6)
			img = cv.window_image.copy()
			layer = np.zeros_like(img)
			ones = np.ones(img.shape[-1])
			for i,color in enumerate(clrs):
				img = cv.window_image.copy()
				if i == 0:
					cx,cy = cv.frm_Units.txt_unit.Position.center
					h = cv.frm_Units.txt_unit.Position.height//4
					di = np.diag_indices(h*2)
					di_rev = (di[0][::-1], di[1])
					print(di, di_rev)
					sub_img = layer[cy-h:cy+h+1, cx-h:cx+h+1].view()
					sub_img[di] = ones
					img = np.where(layer == ones, color, img)
			cv.plot(img)


			# for ctrl,names in cv.controls.items():
			# 	for name in names:
			# 		print(name, ctrl, cv.controls[ctrl][name][0](**cv.controls[ctrl][name][1]))

			# c_i = sample(colors, k=len(cv._controls))
			# for i in range(4):
			# 	img = cv.window_image.copy()
			# 	for clr,ctrl in zip(c_i, cv._controls):
			# 		left, top, right, bottom = ctrl.Position.coords()
			# 		if i == 0:
			# 			img[top:bottom, left] = clr
			# 		elif i == 1:
			# 			img[top:bottom, right] = clr
			# 		elif i == 2:
			# 			img[top, left:right] = clr
			# 		elif i == 3:
			# 			img[bottom, left:right] = clr
			# 	plt.imshow(img)
			# 	plt.show()
			# img = cv.window_image.copy()
			# for clr, ctrl in zip(c_i, cv._controls):
			# 	left, top, right, bottom = ctrl.Position.coords()
			# 	img[top:bottom+1, left] = clr
			# 	img[top:bottom+1, right] = clr
			# 	img[top, left:right+1] = clr
			# 	img[bottom, left:right+1] = clr
			# plt.imshow(img)
			# plt.show()
			# cv.save_current_configuration('TEST')

			# cfg.load_previous_configuration('TEST')
			# for ctrl, names in cfg.controls.items():
			# 	for name in names:
			# 		print(name, ctrl, cfg.controls[ctrl][name][0](**cfg.controls[ctrl][name][1]))

			# def get(**kwargs):
			# 	return win.child_window(**kwargs)
			# cmd = code.InteractiveConsole({'app': app, 'win': win, 'get': get})
			# cmd.interact(banner="")

if __name__ == '__main__':
	main()