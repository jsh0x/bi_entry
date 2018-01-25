# coding=utf-8
import datetime
from time import sleep
from typing import Union, Sequence

from utils.tools.datetime_tools import *
from utils.tools.numeric_tools import *


class Scheduler_ALT:
	_start = _end = active_hours = active_days = None

	def __init__(self, active_days: Union[int, range, Sequence[int], Sequence[range]] = None, active_hours: Union[int, range, Sequence[int], Sequence[range]] = None):
		"""Accepts numeric range for both active_days and active_hours, returns decorator"""
		if active_days:
			self.active_days = tuple(normalize_numeric_range(active_days))
			if any([(x < 0) or (x > 6) for x in self.active_days]):
				raise ValueError

		if active_hours:
			self.active_hours = tuple(normalize_numeric_range(active_hours))
			if any([(x < 0) or (x > 23) for x in self.active_hours]):
				raise ValueError

		self.started = False

	def __init_subclass__(cls, **kwargs):
		if 'active_hours' in kwargs:
			active_hours = tuple(normalize_numeric_range(kwargs['active_hours']))
			if any([(x < 0) or (x > 23) for x in active_hours]):
				raise ValueError
			cls.active_hours = active_hours

		if 'active_days' in kwargs:
			active_days = tuple(normalize_numeric_range(kwargs['active_days']))
			if any([(x < 0) or (x > 23) for x in active_days]):
				raise ValueError
			cls.active_days = active_days

		if 'start' in kwargs:
			start, args, kwargs = kwargs['start']
			if not callable(start):
				raise ValueError
			cls._start = (start, args, kwargs)

		if 'end' in kwargs:
			end, args, kwargs = kwargs['end']
			if not callable(end):
				raise ValueError
			cls._end = (end, args, kwargs)

		return cls

	def __call__(self, func):
		if not callable(func):
			raise ValueError

		class _scheduler(scheduler, active_days=self.active_days, active_hours=self.active_hours):
			def __init__(self, func):
				self.func = func
				super().__init__()

			def __call__(self, *args, **kwargs):
				now = datetime.datetime.now()
				now_hour = now.hour
				now_day = fix_isoweekday(now)

				if now_day in self.active_days and now_hour in self.active_hours:
					if not self.started:
						self.start()
					self.func(*args, **kwargs)
				else:
					if self.started:
						self.end()
					sleep(1)

			def register_start(self, func=None, args: Sequence = [], kwargs: dict = {}):
				self._start = (func, args, kwargs)

			def register_end(self, func=None, args: Sequence = [], kwargs: dict = {}):
				self._end = (func, args, kwargs)

		return _scheduler(func)

	def start(self):
		if self._start:
			self._start[0](*self._start[1], **self._start[2])
		self.started = True

	def end(self):
		if self._end:
			self._end[0](*self._end[1], **self._end[2])
		self.started = False


class Scheduler:
	start_proc = end_proc = start_args = end_args = data = None
	
	def __init__(self, main_proc):
		self.main_proc = main_proc
		self._started = False

	def __call__(self, *args, **kwargs):
		now = datetime.datetime.now()

		if self._started:
			if now.minute in self.active_minutes:
				self.main_proc(*args, **kwargs)
			else:
				self.end()
		else:
			if now.minute in self.active_minutes:
				self.start()
			else:
				pass

	@property
	def active_days(self):
		return [x for x in self.data.keys()]

	@property
	def active_hours(self):
		now = datetime.datetime.now()
		try:
			retval = self.data[fix_isoweekday(now)]
		except KeyError:
			return []
		else:
			return [x for x in retval.keys()]

	@property
	def active_minutes(self):
		now = datetime.datetime.now()
		try:
			retval = self.data[fix_isoweekday(now)][now.hour]
		except KeyError:
			return []
		else:
			return retval

	def register_schedule(self, sched_dict):
		self.data = sched_dict

	def register_start(self, start_proc, start_args):
		self.start_proc = start_proc
		self.start_args = start_args
	
	def register_end(self, end_proc, end_args):
		self.end_proc = end_proc
		self.end_args = end_args

	def start(self):
		self.start_proc(*self.start_args)

	def end(self):
		self.end_proc(*self.end_args)


__all__ = ['Scheduler']