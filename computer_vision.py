import logging
import tempfile
from typing import Tuple
import sqlite3 as sql
from collections import defaultdict
import weakref
import code

import pyautogui as pag
import pywinauto as pwn
import numpy as np
from matplotlib import pyplot as plt

from controls import Coordinates,Control
from commands import screenshot, Application


class GlobalCoordinates(Coordinates):
	pass


class _LocalCoordinates(Coordinates):
	def __init__(self, global_container: GlobalCoordinates, left: int = 0, top: int = 0, right: int = 0, bottom: int = 0):
		self.global_left = left
		self.global_top = top
		self.global_right = right
		self.global_bottom = bottom
		width = np.subtract(right, left)
		height = np.subtract(bottom, top)
		left = np.subtract(left, global_container.left)
		top = np.subtract(top, global_container.top)
		right = np.add(left, width)
		bottom = np.add(top, height)
		super().__init__(left=left, top=top, right=right, bottom=bottom)


class GlobalCoordinates(Coordinates):
	def __init__(self, left: int=0, top: int=0, right: int=0, bottom: int=0):
		super().__init__(left=left, top=top, right=right, bottom=bottom)
		self._original_left = left
		self._original_top = top
		self._original_right = right
		self._original_bottom = bottom
		self._locals = []

	def add_local(self, name: str, left: int=0, top: int=0, right: int=0, bottom: int=0):
		local_coord = _LocalCoordinates(left=left, top=top, right=right, bottom=bottom, global_container=self)
		self.__setattr__(name=name, value=local_coord)
		self._locals.append(name)

	def __contains__(self, item: _LocalCoordinates):
		if self.left > item.left:
			return False
		elif self.right < item.right:
			return False
		elif self.top > item.top:
			return False
		elif self.bottom < item.bottom:
			return False
		else:
			return True

	def coords_changed(self):
		for name in self._locals:
			old_local = self.__getattr__(name)
			new_local = _LocalCoordinates(global_container=self, left=old_local.left, top=old_local.top, right=old_local.right, bottom=old_local.bottom)
			self.__delattr__(name)
			self.__setattr__(name, new_local)

	def __call__(self, *args, **kwargs):
		if (self._original_left, self._original_top, self._original_right, self._original_bottom) != (self.left, self.top, self.right, self.bottom):
			self.coords_changed()


def convert_array(value: bytes) -> np.ndarray:
	with tempfile.TemporaryFile(mode='w+b') as f:
		f.write(value)
		retval = np.fromfile(f)
	return retval


def adapt_array(value: np.ndarray) -> bytes:
	return value.tobytes()


def convert_coordinates(value: bytes) -> Coordinates:
	return Coordinates(*map(int, bytes.decode(value, encoding="utf-8").split(',')))


def adapt_coordinates(value: Coordinates) -> bytes:
	return bytes(value)


# Initial Variables
log = logging.getLogger("devLog")

sql.register_adapter(np.ndarray, adapt_array)
sql.register_adapter(Coordinates, adapt_coordinates)
sql.register_converter('array', convert_array)
sql.register_converter('coordinates', convert_coordinates)

conn = sql.connect(database=':memory:')
c = conn.cursor()
# c.execute("CREATE TABLE cv_data(name text, form text, position coordinates, image array)")


class CV_Config:
	def __init__(self, window: pwn.WindowSpecification):
		props = window.get_properties()
		coord = props['rectangle']
		self.window_gc = GlobalCoordinates(left=coord.left, top=coord.top, right=coord.right, bottom=coord.bottom)
		self.scrn = np.array(screenshot())
		self.window_image = self.scrn[self.window_gc.top:self.window_gc.bottom, self.window_gc.left:self.window_gc.right]
		self.controls = defaultdict(list)

	def check_control(self, ctrl: Control):
		ctrl = self.window_gc.__getattribute__(ctrl.__name__)
		ctrl_image = self.window_image[ctrl.top:ctrl.bottom, ctrl.left:ctrl.right]
		coords = pag.locate(needleImage=ctrl_image, haystackImage=self.window_image, grayscale=True)
		if coords:
			if (ctrl.left, ctrl.top, ctrl.right, ctrl.bottom) == (coords[0], coords[1], coords[0]+coords[2], coords[1]+coords[3]):
				return True
			else:
				return False
		else:
			return False

	def add_control(self, ctrl: Control):
		self.window_gc.add_local(ctrl.__name__, ctrl.coordinates.left, ctrl.coordinates.top, ctrl.coordinates.right, ctrl.coordinates.bottom)
		self.controls[ctrl.__class__.__name__].append(weakref.ref(ctrl))

def main():
	filepath = 'C:/Users/mfgpc00/AppData/Local/Apps/2.0/QQC2A2CQ.YNL/K5YT3MK7.VDY/sl8...ient_002c66e0bc74a4c9_0008.0003_1fdd36ef61625f38/WinStudio.exe'
	with Application(filepath) as app:
			usr = "jredding"
			pwd = "JRJul17!"
			app.log_in(usr, pwd)
			app.open_form("Units")
			win = app._win
			def get(**kwargs):
				return win.child_window(**kwargs)
			cmd = code.InteractiveConsole({'app': app, 'win': win, 'get': get})
			cmd.interact(banner="")

if __name__ == '__main__':
	main()