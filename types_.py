from collections import UserDict, UserList
from typing import NamedTuple, Iterable, Union

import numpy as np
import PIL.Image


class ColorValue:
	__slots__ = ['_int_value', '_float_value']

	def __init__(self, x: Union[int, float]):
		assert ((isinstance(x, float) and 0. <= x <= 1.) or (isinstance(x, int) and 0 <= x <= 255) or isinstance(x, ColorValue))
		if isinstance(x, float):
			self._int_value = np.uint8(np.multiply(np.float64(x), 255))
			self._float_value = np.float64(x)
		elif isinstance(x, int):
			self._int_value = np.uint8(x)
			self._float_value = np.true_divide(np.float64(x), 255)
		elif isinstance(x, ColorValue):
			self._int_value = int(x)
			self._float_value = float(x)

	def __int__(self):
		return self._int_value

	def __float__(self):
		return float(self._float_value)

	def __invert__(self):
		return ColorValue(np.add(self._int_value, 255, dtype=np.uint8))

	def __repr__(self):
		return f"<ColorValue object int={self._int_value}, float={self._float_value}>"


class RGB(UserList):
	__slots__ = ['red', 'green', 'blue', '_data']

	def __init__(self, *args, **kwargs):
		if len(kwargs.keys()) == 3:
			self.red = ColorValue(kwargs['red'])
			self.green = ColorValue(kwargs['green'])
			self.blue = ColorValue(kwargs['blue'])
		elif len(args) == 3:
			self.red, self.green, self.blue = map(ColorValue, args)
		else:
			raise ValueError()
		super().__init__([self.red, self.green, self.blue])

	def __int__(self):
		return tuple(map(int, self.data))

	def __float__(self):
		return tuple(map(float, self.data))

	def __invert__(self):
		return tuple(map(lambda x: ~x, self.data))


def array_splicer(a: Union[np.ndarray, str], mode: str='split', retval=None, _original=True, dtype=None):
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


class ExtendedImage(object):
	def __init__(self, img: Union[PIL.Image.Image, np.ndarray]):
		if type(img) is np.ndarray:
			if img.ndim > 2:
				if img.shape[2] == 1:
					img = PIL.Image.fromarray(img, mode='L')
				elif img.shape[2] == 3:
					img = PIL.Image.fromarray(img, mode='RGB')
				elif img.shape[2] == 4:
					img = PIL.Image.fromarray(img, mode='RGBA')
			elif img.ndim == 2:
				img = PIL.Image.fromarray(img.reshape((img.shape[0], img.shape[1], 1)), mode='L')
		self._img = img

	@property
	def array(self):
		return np.array(self._img, dtype=np.uint8)

	def __bytes__(self):
		return bytes(array_splicer(self.array, mode='split'), encoding='utf-8')

	def __getattr__(self, item):
		return self.__getattribute__('_img').__getattr__(item)

	def __repr__(self):
		return f'<ExtendedImage object; resolution={self._img.size[0]}x{self._img.size[1]}, mode={self._img.mode}>'


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
			raise ValueError(f"Value left {value} >= value right {self._right}")
		else:
			self._left = value

	@property
	def top(self):
		return self._top

	@top.setter
	def top(self, value):
		if self._bottom and value >= self._bottom:
			raise ValueError(f"Value top {value} >= value bottom {self._bottom}")
		else:
			self._top = value

	@property
	def right(self):
		return self._right

	@right.setter
	def right(self, value):
		if self._left and value <= self._left:
			raise ValueError(f"Value right {value} <= value left {self._left}")
		else:
			self._right = value

	@property
	def bottom(self):
		return self._bottom

	@bottom.setter
	def bottom(self, value):
		if self._top and value <= self._top:
			raise ValueError(f"Value bottom {value} <= value top {self._top}")
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
		return f"<Coordinate object; L{self.left}, T{self.top}, R{self.right}, B{self.bottom}>"

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

	def to_list(self):
		return [self.left, self.top, self.right, self.bottom]


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


class _LocalCoordinates2(Coordinates):
	def __init__(self, global_container: GlobalCoordinates, left: int = 0, top: int = 0, right: int = 0, bottom: int = 0):
		width = np.subtract(right, left)
		height = np.subtract(bottom, top)
		self.global_left = global_container.left+left
		self.global_top = global_container.top+top
		self.global_right = self.global_left+width
		self.global_bottom = self.global_top+height
		self.global_center = np.add(self.global_left, np.floor_divide(width, 2)), np.add(self.global_top, np.floor_divide(height, 2))
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
		self.__setattr__(name, local_coord)
		self._locals.append(name)

	def _add_local(self, name: str, left: int=0, top: int=0, right: int=0, bottom: int=0):
		local_coord = _LocalCoordinates2(left=left, top=top, right=right, bottom=bottom, global_container=self)
		self.__setattr__(name, local_coord)
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


class ControlInfo(NamedTuple):
	Id: int
	Type: str
	Name: str
	Form: str
	Position: Coordinates
	Image: ExtendedImage
	Reliability: int


class UniqueList(UserList):
	def __init__(self, iterable: list=None):
		super().__init__()
		self._current = 0
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

	def __len__(self):
		return len(self._set)

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

	@property
	def _high(self):
		return len(self.data)


class Listionary(UserDict):
	def __init__(self, *args):
		self._all_values = []
		super().__init__(self)

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
		super().__init__(self)

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


class NestedUniqueListionary(UserDict):
	def __init__(self, preset=None):
		if preset is None:
			self._all_values = UniqueList()
		else:
			self._all_values = preset
		super().__init__()

	def __setitem__(self, key, val):
		self.data.__setitem__(key, val)
		if type(val) is not dict and val not in self._all_values:
			self._all_values.append(val)

	def __getitem__(self, key):
		try:
			self.data.__getitem__(key)
		except KeyError:
			self.data.__setitem__(key, NestedUniqueListionary(self._all_values))
		finally:
			return self.data.__getitem__(key)

	def __contains__(self, item):
		return item in self._all_values

	def __len__(self):
		return len(self._all_values)

	def clear(self):
		self.data.clear()
		self._all_values.clear()

	def all_values(self):
		return self._all_values


class ControlConfig(NamedTuple):
	Id: int
	Name: str
	IDs: UniqueList
	Total_Reliability: float


class Form:
	attr_dict = {}
	def __init__(self, *args, **kwargs):
		self.attr_dict = {}
		for k,v in kwargs.items():
			self.__setattr__(k, v)
			self.attr_dict[k] = v

	def list_attr(self):
		return self.attr_dict
