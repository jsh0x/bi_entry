#! python3 -W ignore
# coding=utf-8

import logging
import pathlib
import queue
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from time import sleep
from typing import List, Tuple, Union

import psutil
from _globals import *
from core.Timer import Timer
from utils.tools import enumerate_screens

from core.Application import Application

log = logging.getLogger('root')


class PuppetMaster:  # THINK: Make iterable?
	_children = set()
	pids = defaultdict(list)

	# _instance = None  # Keep instance reference
	#
	# def __new__(cls, *args, **kwargs):
	# 	"""Singleton"""
	# 	if not cls._instance:
	# 		cls._instance = cls.__new__(cls, *args, **kwargs)
	# 	return cls._instance

	def __init__(self, fp, app_count: int = 0, start_new: bool = True, grab_old: bool = False, skip_opt: bool = False):
		#  TODO: Grab is VERY time intensive (~10sec minimum), reduce
		timer = Timer.start()
		if app_count > 0:
			if grab_old:
				for i in range(app_count):
					app = self.grab(fp)
					if not app:
						break
				app_count -= len(self.children())
			if start_new:
				for i in range(app_count):
					app = self.start(fp)
					if not app:
						break
			if app_count > 0:
				return None
			if not skip_opt:
				self.optimize_screen_space()
			print("PM INIT DONE", timer.restart())

	def start(self, fp: Union[str, pathlib.Path], name: str = None) -> 'Puppet':
		# try:
		if name is None:
			base_name = pathlib.Path(str(fp)).stem[:4].lower()
			name = base_name + '1'
			count = 2
			while name in self._children:
				name = base_name + str(count)
				count += 1
		app = Application.start(str(fp))
		app.win32.top_window().exists()
		# except Exception:
		# 	return None
		# else:
		self.__setattr__(name, self.Puppet(app, name))
		self.pids[fp].append(self.__getattribute__(name).app.pid)
		self._children.add(name)
		return self.__getattribute__(name)

	def grab(self, fp: Union[str, pathlib.Path]) -> 'Puppet':
		try:
			base_name = pathlib.Path(str(fp)).stem[:4].lower()
			name = base_name + '1'
			count = 2
			while name in self._children:
				name = base_name + str(count)
				count += 1
			app = Application.connect(pathlib.Path(str(fp)), self.pids[fp])
			app.win32.top_window().exists()
		except Exception:
			return None
		else:
			self.__setattr__(name, self.Puppet(app, name))
			self.pids[fp].append(self.__getattribute__(name).app.pid)
			self._children.add(name)
			return self.__getattribute__(name)

	def optimize_screen_space(self, win_size: Tuple[int, int] = (1024, 750), screen_pref: str = None):
		# {l:2017 t:122 r:3040 b:872}
		all_scrn = enumerate_screens()
		if screen_pref.lower() == 'left':
			all_scrn = all_scrn[:1]
		elif screen_pref.lower() == 'right':
			all_scrn = all_scrn[-1:]
		windows = len(self.children())
		m = windows // len(all_scrn) if (windows // len(all_scrn)) > 1 else 2
		for i, ch in enumerate(self.children()):
			ch.app.size = win_size
			scrn = all_scrn[i // m]
			x_step = ((scrn[2] - scrn[0]) - win_size[0]) // (m - 1)
			y_step = ((scrn[3] - scrn[1]) - win_size[1])
			if (((scrn[2] - scrn[0]) - win_size[0]) / (m - 1)) - x_step >= 0.5:
				x_step += 1
			x = scrn[0] + (x_step * (i % m))
			y = scrn[1] + (y_step * ((i % m) % 2))
			ch.app.location = (x, y)

	def children(self) -> List['Puppet']:
		return [self.__getattribute__(ch) for ch in self._children]

	# def apply_all(self, func: Callable, *args, **kwargs):
	# 	with ThreadPoolExecutor(max_workers=len(self.children())) as e:
	# 		for ch in self.children():
	# 			e.submit(func, ch, *args, **kwargs)
	# 			sleep(1)

	def get_puppet(self, ppt: Union[str, int, 'Puppet']) -> 'Puppet':
		if type(ppt) is str:
			if ppt in self._children:
				ppt = self.__getattribute__(ppt)
			elif ppt.startswith('ppt') and ppt[3:].isnumeric():
				ppt = int(ppt[3:])
			else:
				raise ValueError()
		if type(ppt) is int:
			if 0 <= ppt < len(self.children()):
				ppt = self.children()[ppt]
			else:
				raise ValueError()
		if ppt is not None and ppt not in self.children():
			raise ValueError()
		if ppt is None:
			for ch in self.children():
				# print(ch, ch.status)
				if ch.status == 'Idle':
					ppt = ch
					break
			else:
				raise ValueError()
		return ppt

	def wait_for_puppets(self, puppets, max_time=10):
		puppets = [self.get_puppet(ppt) for ppt in puppets]
		res = []
		timer = Timer.start()
		while len(res) < len(puppets):
			if __debug__:
				pass
			sleep(0.001)
			for ppt in puppets:
				res2 = ppt.get_output()
				if res2:
					res.append(res2)
				elif ppt.status == 'Idle':
					res.append(ppt.status)
			if timer.lap() > max_time:
				raise TimeoutError()

	class Puppet(threading.Thread):
		"""Thread class with a stop() method. The thread itself has to check
		regularly for the stopped() condition."""

		def __bool__(self):
			return True

		def target(self):
			while True:
				try:
					command, args, kwargs = self.q_in.get_nowait()
				except queue.Empty:
					sleep(0.0001)
				else:
					self.status = 'Busy'
					self.q_out.put_nowait(command(self, *args, **kwargs))
				self.status = 'Idle'

		def __init__(self, app: Application, name):
			self.q_in = queue.Queue()
			self.q_out = queue.Queue()
			self.app = app
			self.status = 'Idle'
			super().__init__(target=self.target, daemon=True, name=name)
			self.start()
			self._stop_event = threading.Event()

		def set_input(self, func: callable, *args, **kwargs):
			self.q_in.put_nowait({'cmd': func, 'args': tuple(arg for arg in args), 'kwargs': {k: v for k, v in kwargs.items()}})

		def get_output(self):
			try:
				value = self.q_out.get_nowait()
			except queue.Empty:
				return None
			else:
				return value

		def stop(self):
			self._stop_event.set()

		def stopped(self):
			return self._stop_event.is_set()

	def __enter__(self):
		return self

	def __exit__(self, etype, value, traceback):
		procs = [ch.app for ch in self.children()]
		for p in procs:
			# print(p)
			try:
				p.quick_log_out()
			except Exception:
				pass
			p.terminate()
		gone, still_alive = psutil.wait_procs(procs, timeout=3)
		for p in still_alive:
			# print(p)
			p.kill()


class SyteLinePupperMaster(PuppetMaster):
	def __init__(self, n: int, fp=application_filepath, start_new: bool = True, grab_old: bool = False, skip_opt: bool = True, forms=[]):
		# print(n, forms)
		user_list = ['bigberae', username, 'BISync01', 'BISync02', 'BISync03']
		pwd_list = ['W!nter17', password, 'N0Trans@cti0ns', 'N0Re@s0ns', 'N0Gue$$!ng']
		super().__init__(fp, n, start_new, grab_old, skip_opt)
		for ppt, usr, pwd in zip(self.children(), user_list, pwd_list):
			ppt.set_input(lambda x, y: x.app.quick_log_in(*y), [usr, pwd])
		self.wait_for_puppets(self.children(), 4)
		self.optimize_screen_space(screen_pref='left')
		if forms:
			for form, ppt in zip(forms, self.children()):
				if type(form) is str:
					form = [form]
				ppt.set_input(lambda x, y: x.app.quick_open_form(*y), form)
				sleep(1)
			while not all(ppt.status == 'Idle' for ppt in self.children()):
				sleep(0.0001)

	@classmethod
	def for_processes(cls, *processes):
		return cls(len([proc for proc in processes]), forms=[proc.required_forms for proc in processes])

	@classmethod
	def for_forms(cls, *forms):
		return cls(len([form for form in forms]), forms=[form for form in forms])

	def open_forms(self, *names):
		with ThreadPoolExecutor(max_workers=len(names)) as e:
			for ppt, forms in zip(self.children(), names):
				e.submit(lambda x, y: x.quick_open_form(*y), ppt.app, forms)
				sleep(0.5)
		sleep(1)

	def run_process(self, process, ppt: Union[str, int, 'Puppet'] = None) -> bool:
		"""Run process, return whether it was successful or not."""
		ppt = self.get_puppet(ppt)
		if hasattr(process, 'starting_forms'):
			ppt.set_input(lambda x, y: x.app.quick_open_form(*y), process.starting_forms)
			sleep(1)
			while ppt.status != 'Idle':
				sleep(0.01)
		if hasattr(process, 'get_units'):
			units = process.get_units(exclude=[sn for ch in self.children() for sn in ch.units])
			if units:
				while ppt.status != 'Idle':
					sleep(0.01)
				units2 = {unit.serial_number for unit in units}
				ppt.run_process(process, units2, units)
				while ppt.status != 'Idle':
					sleep(0.01)
				return ppt
			return False
		else:
			ppt.run_process(process)
			while ppt.status != 'Idle':
				sleep(0.01)
			return ppt

	class Puppet(PuppetMaster.Puppet):
		def target(self):
			while True:
				try:
					values = self.q_in.get_nowait()
				except queue.Empty:
					sleep(0.0001)
				else:
					self.status = 'Busy'
					command = values['cmd']
					args = values['args']
					kwargs = values['kwargs']
					if hasattr(command, 'run'):
						from processes import transact
						res = transact.main(self, *args, **kwargs)
						print(callable(transact.main))
						print(type(transact.main), type(transact.main) is function)
					else:
						res = command(self, *args, **kwargs)
					self.q_out.put_nowait(res)
					self.status = 'Idle'
					self.units.clear()

		def __init__(self, app: Application, name):
			self.units = set()
			self.status = 'Idle'
			super().__init__(app, name)

		def run_process(self, proc, unit_sn=None, *args, **kwargs):
			self.q_in.put_nowait({'cmd': proc, 'args': tuple(arg for arg in args), 'kwargs': {k: v for k, v in kwargs.items()}})
			if unit_sn:
				thing = {str(sn) for sn in unit_sn}
				self.units = thing


__all__ = ['SyteLinePupperMaster', 'PuppetMaster']
