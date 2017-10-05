import re
from itertools import tee
import pathlib
from os import PathLike
from collections import UserList
from typing import Union, List
from random import getrandbits
import binhex
from string import (ascii_lowercase as char_lower, ascii_uppercase as char_upper,
                    ascii_letters as char, digits as num, punctuation as sym,
                    whitespace as w_space)
space, tab = w_space[:2]


def in_out_check(func):
	def new_func(*original_args, **original_kwargs):
		original_args = list(sub_arg for arg in original_args for sub_arg in arg)
		print(func.__name__)
		print("IN: ", [x for x in original_args])
		retval = func((x for x in original_args), **original_kwargs)
		print("OUT: ", retval)
		return retval
	return new_func


class DSL_Reader(UserList):
	"""
	Domain Specific Language Reader
	"""
	def __init__(self, *args, **kwargs):
		super().__init__(args)
		self.filepath = kwargs.get('fp', None)
		if self.filepath and all([type(i) is bytes for i in self.data]):
			self.data = [self.decode(val) for val in self.data]

	@classmethod
	def open(cls, fp: Union[str, bytes, PathLike]):
		path = pathlib.Path(fp)
		if not path.suffix:
			path = pathlib.Path(fp).with_suffix('.dsl')
		if not path.exists():
			raise FileNotFoundError(f"Filepath {path} does not exist")
		with path.open(mode='rb') as f:
			retlist = [line[:-2] for line in f]
		return DSL_Reader(*retlist, fp=path)

	def __enter__(self):
		...

	def __exit__(self, exc_type, exc_val, exc_tb):
		...

	def __iter__(self):
		self.i = 0
		return self

	def __next__(self):
		if self.i >= len(self.data):
			raise StopIteration
		retval = self.data[self.i]
		self.i += 1
		return retval

	def next(self):
		return self.__next__()

	@staticmethod
	def is_dsl_valid(dsl) -> bool:
		...

	@staticmethod
	def parse_dsl(dsl):
		...

	def encode(self, string: str) -> bytes:
		# byte_string = [bin(x)[:2].rjust(8, '0') for x in string.encode(encoding='utf-8')]
		# func = self._encoding_tuple[int(rand_encoding, base=2)]
		# byte_string = func(byte_string)
		# byte_string = start_pad + rand_encoding[0] + ''.join(y for x in byte_string for y in x) + rand_encoding[1] + end_pad
		start_pad, end_pad = self.randbits(3), self.randbits(3)
		rand_encoding = self.randbits(2)
		byte_string = start_pad + rand_encoding[0] + ''.join(z for y in self._encoding_tuple[int(rand_encoding, base=2)](self.normalize_bit_length(x, 8) for x in string.encode(encoding='utf-8')) for z in y) + rand_encoding[1] + end_pad
		return bytes([int(byte_string[i:i+8], base=2) for i in range(0, len(byte_string), 8)])

	def decode(self, bytes_: bytes) -> str:
		byte_string = ''.join(self.normalize_bit_length(x, 8) for x in bytes_)
		rand_encoding = byte_string[3] + byte_string[-4]
		byte_string = byte_string[4:-4]
		# print(self._encoding_tuple[int(rand_encoding, base=2)].__name__)
		string = ''.join(y for x in self._encoding_tuple[int(rand_encoding, base=2)](byte_string[i:i+8] for i in range(0, len(byte_string), 8)) for y in x)
		return ''.join(int(string[i:i + 8], base=2).to_bytes(1, 'little').decode() for i in range(0, len(string), 8))

	def compile(self):
		return [self.encode(x) + b'\r\n' for x in self.data]

	def save(self, fp: Union[str, bytes, PathLike]=None):
		if self.filepath and not fp:
			fp = pathlib.Path(str(self.filepath))
		elif fp:
			fp = pathlib.Path(str(fp))
			if not fp.suffix:
				fp = fp.with_suffix('.dsl')
			if not fp.exists():
				raise FileNotFoundError(f"Filepath {fp} does not exist")
		else:
			raise ValueError("No value provided for value 'fp'")
		with fp.open(mode='wb') as f:
			for line in self.compile():
				f.write(line)

	@staticmethod
	def randbits(x: int) -> str:
		return bin(getrandbits(x))[2:].rjust(x, '0')

	@staticmethod
	def normalize_bit_length(value: Union[str, int], x: int) -> str:
		value = bin(value) if type(value) is int else value
		return (value[2:] if value.startswith('0b') else value).rjust(x, '0')

	def whole_logic_switch_alt(*args) -> List[str]:
		"""Switches every-other bit
			1 -> 0 / 0 -> 1
			"""
		retval = []
		for x in args:
			for y in x:
				string = ''
				for i,z in enumerate(y):
					if i % 2:
						string += str(abs(int(z) - 1))
					else:
						string += z
				retval.append(string)
			return retval

	def whole_logic_switch_alt_offset(*args) -> List[str]:
		"""Switches every-other bit, offset by 1 position
			1 -> 0 / 0 -> 1
			"""
		retval = []
		for x in args:
			for y in x:
				string = ''
				for i,z in enumerate(y):
					if i % 2:
						string += z
					else:
						string += str(abs(int(z) - 1))
				retval.append(string)
			return retval

	def chunk_logic_switch_alt(*args) -> List[str]:
		"""Switches every-other bit by byte
			1 -> 0 / 0 -> 1
			"""
		retval = []
		for x in args:
			for i,y in enumerate(x):
				string = ''
				if i % 2:
					for j,z in enumerate(y):
						if j % 2:
							string += str(abs(int(z) - 1))
						else:
							string += z
				else:
					for z in y:
						string += str(abs(int(z) - 1))
				retval.append(string)
		return retval

	def chunk_logic_switch_alt_offset(*args) -> List[str]:
		"""Switches every-other bit by byte, offset by 1 position
			1 -> 0 / 0 -> 1
			"""
		retval = []
		for x in args:
			for i,y in enumerate(x):
				string = ''
				if i % 2:
					for z in y:
						string += str(abs(int(z) - 1))
				else:
					for j,z in enumerate(y):
						if j % 2:
							string += str(abs(int(z) - 1))
						else:
							string += z
				retval.append(string)
		return retval

	_encoding_tuple = (whole_logic_switch_alt, whole_logic_switch_alt_offset, chunk_logic_switch_alt, chunk_logic_switch_alt_offset)


import numpy as np


def normalize(x: str, length: int) -> str:
	i = x.index('x') + 1
	return x[:i] + x[i:].rjust(length, '0').upper()


def apply(a: np.ndarray, func):
	if a.ndim == 1:
		return np.array([func(b) for b in a])
	elif a.ndim == 2:
		for i in a:
			print(i)
			for j in i:
				print(j)
		return np.array([[func(c) for c in b] for b in a])
	elif a.ndim == 3:
		return np.array([[[func(d) for d in c] for c in b] for b in a])
	elif a.ndim == 4:
		return np.array([[[[func(e) for e in d] for d in c] for c in b] for b in a])


def temp():
	gridspace = np.zeros((25, 40, 40))
	gs = gridspace.view()
	for i in np.arange(25):
		gs[i] = np.random.randint(2, size=(40, 40))
	np.set_printoptions(edgeitems=100, linewidth=1000)
	# print(gs.sum(axis=0))
	# for i in np.arange(25):
	# 	for j in np.arange(40):
	# 		for k in np.arange(40):
	# 			if gs[i,j,k] == max(gs.sum(axis=0)):
	# print(apply(gs.sum(axis=0), lambda x: int(x.all() == max(gs.sum(axis=0)))))
	def compile_data(c, max_iter):
		z = c
		for n in np.arange(max_iter):
			print(z)
			if abs(z) > 2:
				return n
			z = (z*z) + c
		else:
			return max_iter
	from matplotlib import pyplot as plt
	ge = np.random.choice(2, size=(96, 96), p=[0.85, 0.15])
	print(compile_data(complex(0.1, 1), 500))
	for i in range(4):
		print()
		print()
		for y in np.arange(1, ge.shape[0] - 1):
			string = ''
			for x in np.arange(1, ge.shape[1] - 1):
				if ge[y, x] == 1:
					string += '\u2591'
				else:
					string += '\u2588'
			print(string)
		ge2 = np.zeros_like(ge)
		for y in np.arange(1, ge.shape[0]-1):
			for x in np.arange(1, ge.shape[1]-1):
				v_total, h_total = ge[y - 1:y + 2, x].sum(), ge[y, x - 1:x + 2].sum()
				total = v_total + h_total
				if ge[y, x]:
					if 3 <= total < 4:
						ge2[y, x] = 1
					else:
						ge2[y, x] = 0
				else:
					if 2 <= total:
						ge2[y, x] = 1
					else:
						ge2[y, x] = 0
		ge = ge2.copy()


	# 2588, 2591, 2592, 2593
	# 2581, 258F, 2594, 2595
	# psbl = np.arange(25, dtype=np.int64).reshape((5,5))-1
	# psbl[0,0] = 1
	# b = np.full_like(psbl, 2)
	# b[0,0] = 0
	# psbl = np.power(b, psbl)
	# print(psbl)
	# a = apply(psbl, lambda x: normalize(hex(x), 6))
	# print(a)

temp()

# test = DSL_Reader('This is a test', 'so is this', 'oh and this as well')
# test.save(r'C:\Users\mfgpc00\Documents\GitHub\bi_entry\TEST')
# test = DSL_Reader.open(r'C:\Users\mfgpc00\Documents\GitHub\bi_entry\TEST')
# test.save()
