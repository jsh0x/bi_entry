import logging, sqlite3 as sql
from typing import Union, Dict, List, NamedTuple, Set
from platform import uname
from collections import defaultdict
from time import sleep

import pyautogui as pag, pywinauto as pwn, numpy as np
from matplotlib import pyplot as plt
from PIL import Image

from controls import Control, Button, Checkbox, Textbox, Datebox, VerticalScrollbar, HorizontalScrollbar, GridView, Tab
from commands import screenshot, Application
from .math import get_total_reliability
from .types import Coordinates, ControlInfo, ControlConfig, GlobalCoordinates, NestedUniqueListionary as NUL, UniqueList


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
			for val1 in a:
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
	return Coordinates(*map(int, bytes.decode(value, encoding="utf-8").split(',')))


def adapt_coordinates(value: Coordinates) -> bytes:
	return bytes(value)


# Initial Variables
# SkeletonClass = namedtuple('SkeletonClass', ['control', 'criteria'])
ctrl_dict = {'Button': Button, 'Checkbox': Checkbox, 'Textbox': Textbox, 'Datebox': Datebox,
			 'VerticalScrollBar': VerticalScrollbar, 'HorizontalScrollBar': HorizontalScrollbar,
			 'GridView': GridView, 'Tab': Tab}
log = logging.getLogger("root")

sql.register_adapter(np.ndarray, adapt_array)
sql.register_adapter(Coordinates, adapt_coordinates)
sql.register_converter('ARRAY', convert_array)
sql.register_converter('COORDINATES', convert_coordinates)

conn = sql.connect(database='vision.db', detect_types=sql.PARSE_DECLTYPES)
c = conn.cursor()
# c.execute("SELECT name FROM sqlite_master WHERE type='table'")
# tables = map(lambda x: x[0], c.fetchall())

c.execute("DROP TABLE cv_data")
c.execute("DROP TABLE cv_configs")
conn.commit()
quit()

c.execute("CREATE TABLE IF NOT EXISTS cv_data("
          "Id INTEGER PRIMARY KEY, "
          "Type TEXT, "
          "Name TEXT, "
          "Form TEXT, "
          "Position COORDINATES, "
          "Image ARRAY, "
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
c.execute("SELECT * FROM cv_configs")
for val in c.fetchall():
	print(val)
quit()

class CV_Config:
	def __init__(self, **kwargs):
		"""Sets the global coordinates to that of the window"""
		if 'window' in kwargs.keys():
			window = kwargs['window']
			props = window.get_properties()
			coord = props['rectangle']
			self._window = window
			self._window_gc = GlobalCoordinates(left=coord.left, top=coord.top, right=coord.right, bottom=coord.bottom)
			self.scrn = np.array(screenshot())
			self.window_image = self.scrn[self.window_gc.top:self.window_gc.bottom, self.window_gc.left:self.window_gc.right].view()
			self.controls = NUL()
			self._control_ids = UniqueList()
			self._config = None
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
	def window_gc(self):
		props = self._window.get_properties()
		coord = props['rectangle']
		self._window_gc.update(left=coord.left, top=coord.top, right=coord.right, bottom=coord.bottom)
		return self._window_gc

	@window_gc.setter
	def window_gc(self, value):
		self._window_gc = value

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
		return get_total_reliability(np.array(list(map(lambda x: x.Reliability, self.controls.all_values())), np.uint32))

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

	def add_control(self, form, username, *args):
		_sysinfo = uname()
		for ctrl in args:
			self.window_gc.add_local(ctrl.__name__, *ctrl.coordinates.coords())
			img = self.window_image[ctrl.coordinates.top:ctrl.coordinates.bottom, ctrl.coordinates.left:ctrl.coordinates.right].view()
			c.execute(f"SELECT [Id] FROM cv_data WHERE "
			          f"[Type] = '{ctrl.__class__.__name__}' AND "
			          f"[Name] = '{ctrl.__name__}' AND "
			          f"[Form] = '{form}' AND "
			          f"[Position] = {ctrl.coordinates} AND "
			          f"[Image] = {img}")
			val = c.fetchone()
			if not val:
				c.execute(f"INSERT INTO cv_data (Type,Name,Form,Position,Image,OS_Name,OS_General_Version,OS_Specific_Version,Computer_Name,Username) "
				          f"VALUES ('{ctrl.__class__.__name__}','{ctrl.__name__}','{form}',{ctrl.coordinates},{img},'{_sysinfo['system']}','{_sysinfo['release']}','{_sysinfo['version']}','{_sysinfo['node']}','{username}')")
				conn.commit()
				c.execute(f"SELECT [Id] FROM cv_data WHERE [Type] = '{ctrl.__class__.__name__}' AND "
				          f"[Name] = '{ctrl.__name__}' AND "
				          f"[Form] = '{form}' AND "
				          f"[Position] = {ctrl.coordinates} AND "
				          f"[Image] = {img}")
				val = c.fetchone()
			c.execute(f"SELECT [Id],[Type],[Name],[Form],[Position],[Image],[Reliability] FROM cv_data WHERE [Id] = {ctrl_id}")
			ctrl = ControlInfo(*val[0])
			self.controls[ctrl.Form][ctrl.Type][ctrl.Name] = ctrl
			self._control_ids.add(ctrl.Id)
			# self.controls[ctrl.__class__.__name__][ctrl.__name__] = (val, ctrl._kwargs)
			# self._controls[ctrl.__class__.__name__][ctrl.__name__] = SkeletonClass(ctrl.__class__, ctrl.criteria)

	def _add_control(self, *args):
		for ctrl_id in args:
			c.execute(f"SELECT [Id],[Type],[Name],[Form],[Position],[Image],[Reliability] FROM cv_data WHERE [Id] = {ctrl_id}")
			try:
				ctrl = ControlInfo(*c.fetchone()[0])
			except IndexError:
				raise ValueError(f"Invalid ID: {ctrl_id}")
			self.window_gc.add_local(ctrl.Name, *ctrl.Position.coords())
			self.controls[ctrl.Form][ctrl.Type][ctrl.Name] = ctrl
			self._control_ids.add(ctrl_id)

	def load_previous_configuration(self, name: str):
		c.execute(f"SELECT * FROM cv_configs WHERE [Name] = '{name}'")
		exists = c.fetchone()
		if exists:
			self.config = ControlConfig(*exists[0].to_list())
		else:
			raise ValueError(f"Config with name '{name}' does not exist")

	def save_current_configuration(self, name: str=None):
		if name is not None:
			c.execute(f"SELECT * FROM cv_configs WHERE [Name] = '{name}'")
			exists = c.fetchone()
			if exists:
				c.execute(f"UPDATE cv_configs SET [Config] = {np.array(list(self._control_ids), dtype=np.uint16)},[Total_Reliability] = {self._total_reliability} WHERE [Name] = '{name}'")
			else:
				c.execute(f"INSERT INTO cv_configs ([Name],[Config],[Total_Reliability]) VALUES ('{name}',{np.array(list(self._control_ids), dtype=np.uint16)},{self._total_reliability})")
			conn.commit()
		elif self.config is None:
			raise ValueError("Name required if not using saved/loaded config")
		else:
			c.execute(f"UPDATE cv_configs SET [Config] = {np.array(list(self._control_ids), dtype=np.uint16)},[Total_Reliability] = {self._total_reliability} WHERE [Name] = '{self.config.Name}'")
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

def main():
	filepath = 'C:/Users/mfgpc00/AppData/Local/Apps/2.0/QQC2A2CQ.YNL/K5YT3MK7.VDY/sl8...ient_002c66e0bc74a4c9_0008.0003_1fdd36ef61625f38/WinStudio.exe'
	with Application(filepath) as app:
			usr = "jredding"
			pwd = "JRJul17!"
			app.log_in(usr, pwd)
			app.open_form("Units")
			cfg = CV_Config(window=app._win)
			unit_txt = Textbox(window=app._all_win, criteria={'best_match': "Unit:Edit"}, control_name='Unit')
			item_txt = Textbox(window=app._all_win, criteria={'best_match': "Item:Edit"}, control_name='Item')
			srol_btn = Button(window=app._all_win, criteria={'auto_id': "SROLinesButton", 'control_type': "Button", 'top_level_only': False}, control_name='Service Order Lines')
			ownhist_tab = Tab(window=app._all_win, criteria={'best_match': "Owner HistoryTabControl"}, name='Owner History', control_name='Owner History', controls={})
			cfg.add_control(unit_txt, item_txt, srol_btn, ownhist_tab)
			for ctrl,names in cfg.controls.items():
				for name in names:
					print(name, ctrl, cfg.controls[ctrl][name][0](**cfg.controls[ctrl][name][1]))
			cfg.save_current_configuration('TEST')

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