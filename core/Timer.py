#! python3 -W ignore
# coding=utf-8

import datetime
from functools import singledispatch


class Timer:
	def __init__(self, *, start_time=None, return_timedelta: bool = False):
		self._start_time = start_time
		self._return_timedelta = return_timedelta

	@singledispatch
	def start(self):
		self._start_time = datetime.datetime.now()

	@classmethod
	def start(cls):
		return cls(start_time=datetime.datetime.now())

	def lap(self):
		if self._start_time:
			retval = datetime.datetime.now() - self._start_time
			if self._return_timedelta:
				return retval
			else:
				return retval.total_seconds()
		else:
			if self._return_timedelta:
				return datetime.timedelta(0)
			else:
				return datetime.timedelta(0).total_seconds()

	def reset(self):
		self._start_time = None

	def restart(self):
		retval = self.lap()
		self._start_time = datetime.datetime.now()
		return retval

	def stop(self) -> float:
		retval = self.lap()
		self.reset()
		return retval

__all__ = ['Timer']

