# coding=utf-8
from typing import Callable
import pprofile
import datetime

from .tools.datetime_tools import *

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
			retval = self.data[str(fix_isoweekday(now))]
		except KeyError:
			return []
		else:
			return [x for x in retval.keys()]

	@property
	def active_minutes(self):
		now = datetime.datetime.now()

		try:
			retval = self.data[str(fix_isoweekday(now))][str(now.hour)]
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
		self._started = True

	def end(self):
		self.end_proc(*self.end_args)
		self._started = False


def legacy(func: Callable):
	def wrapper(*args, **kwargs):
		print(f"Function {func.__name__} is deprecated, avoid further usage!")
		return func(*args, **kwargs)

	return wrapper


def someHotSpotCallable(func: Callable, *args, **kwargs):
	# Deterministic profiler
	prof = pprofile.Profile()
	with prof():
		func(*args, **kwargs)
	prof.print_stats()


def someOtherHotSpotCallable(func: Callable, *args, **kwargs):
	# Statistic profiler
	prof = pprofile.StatisticalProfile()
	with prof(period=0.001, single=True):
		func(*args, **kwargs)
	prof.print_stats()


def scheduler(func: Callable):
	return Scheduler(func)

__all__ = ['legacy', 'scheduler', 'someHotSpotCallable', 'someOtherHotSpotCallable']
