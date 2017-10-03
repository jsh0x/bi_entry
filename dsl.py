import re
from itertools import tee
import pathlib
from os import PathLike
from collections import UserList
from typing import Union, List
from random import getrandbits
import binhex
from string import (ascii_lowercase as char_lower, ascii_uppercase as char_upper,
                    ascii_letters as char, digits as num, punctuation as sym)


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
	def __init__(self, initlist=None):
		super().__init__(initlist)
		print(self.data)
		if all([type(i) is bytes for i in self.data]):
			self.data = [self.decode(val) for val in self.data]

	@classmethod
	def open(cls, fp: Union[str, bytes, PathLike]):
		path = pathlib.Path(fp)
		if not path.suffix:
			path = pathlib.Path(fp).with_suffix('.dsl')
		if not path.exists():
			raise FileNotFoundError(f"Filepath {path} does not exist")
		with open(path.as_posix(), mode='rb') as f:
			retlist = [line[:-2] for line in f]
		return DSL_Reader(retlist)

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
		string = ''.join(y for x in self._encoding_tuple[int(rand_encoding, base=2)](byte_string[i:i+8] for i in range(0, len(byte_string), 8)) for y in x)
		return ''.join(int(string[i:i + 8], base=2).to_bytes(1, 'little').decode() for i in range(0, len(string), 8))

	def compile(self, filename: str):
		with open(filename+'.dsl', mode='wb') as f:
			for line in self.data:
				f.write(self.encode(line+'\r\n'))

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


reader = DSL_Reader.open(r'C:\Users\mfgpc00\Documents\GitHub\bi_entry\TEST')
reader.append('BLARGH')
print(reader.data)
