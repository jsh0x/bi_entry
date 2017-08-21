from collections import UserDict, UserList
from typing import NamedTuple, MutableSet

import numpy as np


class Coordinates:
	def __init__(self, left: int=0, top: int=0, right: int=0, bottom: int=0):
		self._left = None
		self._top = None
		self._right = None
		self._bottom = None
		#
		self.left = np.uint32(left)
		self.top = np.uint32(top)
		self.right = np.uint32(right)
		self.bottom = np.uint32(bottom)

	@property
	def left(self):
		return self._left

	@left.setter
	def left(self, value):
		if self._right and value >= self._right:
			raise ValueError
		else:
			self._left = value

	@property
	def top(self):
		return self._top

	@top.setter
	def top(self, value):
		if self._bottom and value >= self._bottom:
			raise ValueError
		else:
			self._top = value

	@property
	def right(self):
		return self._right

	@right.setter
	def right(self, value):
		if self._left and value <= self._left:
			raise ValueError
		else:
			self._right = value

	@property
	def bottom(self):
		return self._bottom

	@bottom.setter
	def bottom(self, value):
		if self._top and value <= self._top:
			raise ValueError
		else:
			self._bottom = value

	@property
	def width(self):
		return np.subtract(self.right, self.left)

	@property
	def height(self):
		return np.subtract(self.bottom, self.top)

	@property
	def center(self):
		x = np.add(self.left, np.floor_divide(self.width, 2))
		y = np.add(self.top, np.floor_divide(self.height, 2))
		return x, y

	def __str__(self):
		return f"({self.left}, {self.top}, {self.right}, {self.bottom})"

	def __repr__(self):
		return f"<COORD L{self.left}, T{self.top}, R{self.right}, B{self.bottom}>"

	def __bytes__(self):
		return bytes(f"{self.left},{self.top},{self.right},{self.down}", encoding="utf-8")

	def update(self, *args, **kwargs):
		if len(args) == 4:
			left, top, right, bottom = args
		else:
			left = np.uint32(kwargs.get('left', 0))
			top = np.uint32(kwargs.get('top', 0))
			right = np.uint32(kwargs.get('right', 0))
			bottom = np.uint32(kwargs.get('bottom', 0))
		self._left = left
		self._top = top
		self._right = right
		self._bottom = bottom
		# Checks for any conflicting coords
		self.left = left
		self.top = top
		self.right = right
		self.bottom = bottom

	def coords(self):
		return self.left, self.top, self.right, self.bottom


class GlobalCoordinates(Coordinates):
	def __init__(self, left: int=0, top: int=0, right: int=0, bottom: int=0):
		super().__init__(left=left, top=top, right=right, bottom=bottom)
		self._original_left = left
		self._original_top = top
		self._original_right = right
		self._original_bottom = bottom
		self._locals = []


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


class ControlInfo(NamedTuple):
	Id: int
	Type: str
	Name: str
	Form: str
	Position: Coordinates
	Image: np.ndarray
	Reliability: int


class UniqueList(UserList):
	def __init__(self, iterable: list=None):
		super().__init__(iterable)
		self._set = set(self.data)

	def __contains__(self, item):
		return item in self._set

	def __setitem__(self, key, value):
		if type(key) is not int:
			raise TypeError
		elif (key < 0) or (key >= len(self.data)):
			raise IndexError
		if value not in self._set:
			self.data[key] = value
			self._set = set(self.data)

	def __delitem__(self, key):
		if type(key) is not int:
			raise TypeError
		elif (key < 0) or (key >= len(self.data)):
			raise IndexError
		self._set.remove(self.data[key])
		self.data.remove(self.data[key])

	def __add__(self, other):
		retval = self.data
		for item in other:
			if item not in self._set:
				retval.append(item)
		return self.__class__(retval)

	def __iadd__(self, other):
		self.extend(other)

	def __mul__(self, other):
		pass

	def __rmul__(self, other):
		pass

	def __imul__(self, other):
		pass

	def append(self, item):
		if item not in self._set:
			self.data.append(item)
			self._set.add(item)

	def extend(self, other):
		for val in other:
			self.append(val)

	def insert(self, i, item):
		if type(i) is not int:
			raise TypeError
		elif (i < 0) or (i >= len(self.data)):
			raise IndexError
		if item not in self._set:
			self.data.insert(i, item)
			self._set.add(item)

	def pop(self, i=-1):
		retval = self.data.pop(i)
		self._set.remove(retval)
		return retval

	def remove(self, item):
		self._set.remove(item)
		self.data.remove(item)

	def clear(self):
		self.data.clear()
		self._set.clear()


class Listionary(UserDict):
	def __init__(self, *args):
		self._all_values = []
		super().__init__(self, *args)

	def __getitem__(self, key):
		return self.data.__getitem__(key)

	def __setitem__(self, key, val):
		self.data.__setitem__(key, val)
		if type(val) is not dict:
			self._all_values.append(val)

	def __contains__(self, item):
		return item in self._all_values

	def __len__(self):
		return len(self._all_values)

	def clear(self):
		self.data.clear()
		self._all_values.clear()

	def all_values(self):
		return self._all_values


class UniqueListionary(Listionary):
	def __init__(self, *args):
		self._all_values = UniqueList()
		super().__init__(self, *args)

	def __setitem__(self, key, val):
		self.data.__setitem__(key, val)
		if type(val) is not dict and val not in self._all_values:
			self._all_values.append(val)


class NestedListionary(Listionary):
	def __getitem__(self, key):
		try:
			self.data.__getitem__(key)
		except KeyError:
			self.data.__setitem__(key, NestedListionary())
		finally:
			return self.data.__getitem__(key)


class NestedUniqueListionary(UniqueListionary):
	def __getitem__(self, key):
		try:
			self.data.__getitem__(key)
		except KeyError:
			self.data.__setitem__(key, UniqueListionary())
		finally:
			return self.data.__getitem__(key)


class ControlConfig(NamedTuple):
	Id: int
	Name: str
	IDs: UniqueList
	Total_Reliability: float
