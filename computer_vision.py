import logging
import tempfile
from typing import Tuple
import sqlite3 as sql

import pyautogui as pag
import pywinauto as pwn
import numpy as np
from matplotlib import pyplot as plt

from controls import Coordinates,Control
from commands import screenshot


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

	def add_local(self, name: str, left: int=0, top: int=0, right: int=0, bottom: int=0):
		local_coord = _LocalCoordinates(left=left, top=top, right=right, bottom=bottom, global_container=self)
		self.__setattr__(name=name, value=local_coord)

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
c.execute("CREATE TABLE cv_data(name text, position coordinates, image array)")


class CV_Config:
	def __init__(self, window: pwn.WindowSpecification):
		props = window.get_properties()
		coord = props['rectangle']
		self.window_gc = GlobalCoordinates(left=coord.left, top=coord.top, right=coord.right, bottom=coord.bottom)
		self.scrn = np.array(screenshot())
		self.window_image = self.scrn[self.window_gc.top:self.window_gc.bottom, self.window_gc.left:self.window_gc.right]

	def add_control(self, ctrl: Control):
		self.window_gc.add_local(ctrl.__name__, ctrl.coordinates.left, ctrl.coordinates.right)
		ctrl = self.window_gc.__getattribute__(ctrl.__name__)
		ctrl_image = self.window_image[ctrl.top:ctrl.bottom, ctrl.left:ctrl.right]

window = pwn.WindowSpecification('')
cv_config = CV_Config(window)

pag.locateAll(needleImage=, haystackImage=cv_config.window_image)