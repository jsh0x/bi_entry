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
from common import *
from _globals import *
from core.Timer import Timer
from utils.tools import enumerate_screens

from core.Application import Application

log = logging.getLogger('root')


def target(func, args, q):
	try:
		func(*args)
	except Exception as ex:
		raise ex
	else:
		q.put(True)


class Puppet:
	"""Thread class with a stop() method. The thread itself has to check
	regularly for the stopped() condition."""

	def __init__(self, app: Application, name):
		self.app = app
		self.name = name
		self.worker = None
		self.status = 'Idle'
		self.q_out = queue.Queue(maxsize=1)

	def start(self, proc, *args):
		self.status = 'Busy'
		self.q_out.empty()
		print(proc, args)
		args = (proc, tuple(args), self.q_out)
		self.worker = threading.Thread(target=target, args=args, name=self.name)
		self.worker._stop_event = threading.Event()
		self.worker.start()

	def ready(self) -> bool:
		if self.q_out.not_empty is True:
			return True
		else:
			return False

	def stop(self):
		self.worker._stop_event.set()

	def stopped(self):
		return self.worker._stop_event.is_set()


class PuppetMaster:  # THINK: Make iterable?
	_children = {}
	pids = defaultdict(list)

	def __init__(self, fp: Filepath, app_count: int = 0, opt: bool = True):
		#  TODO: Grab is VERY time intensive (~10sec minimum), reduce
		timer = Timer.start()
		all_ppts = []
		for i in range(app_count):
			ppt = self.create_puppet(fp, f'ppt{i}')
			all_ppts.append(ppt)
			if not ppt:
				break
		if app_count > 0:
			return None
		if opt:
			self.optimize_screen_space()
			print("PM INIT DONE", timer.restart())

	def create_puppet(self, fp: Filepath, name: str) -> Puppet:
		fp = normalize_filepath(fp)
		assert name not in self._children

		app = Application.start(fp.as_posix())
		app.win32.top_window().exists()
		ppt = Puppet(app, name)
		self.pids[fp.as_posix()].append(app.pid)
		self._children[name] = ppt
		return ppt

	# def start(self, fp: Union[str, pathlib.Path], name: str = None) -> 'Puppet':
	# 	# try:
	# 	if name is None:
	# 		base_name = pathlib.Path(str(fp)).stem[:4].lower()
	# 		name = base_name + '1'
	# 		count = 2
	# 		while name in self._children:
	# 			name = base_name + str(count)
	# 			count += 1
	# 	app = Application.start(str(fp))
	# 	app.win32.top_window().exists()
	# 	# except Exception:
	# 	# 	return None
	# 	# else:
	# 	self.__setattr__(name, self.Puppet(app, name))
	# 	self.pids[fp].append(self.__getattribute__(name).app.pid)
	# 	self._children.add(name)
	# 	return self.__getattribute__(name)

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
		windows = len(self._children)
		m = windows // len(all_scrn) if (windows // len(all_scrn)) > 1 else 2
		for i, ppt in enumerate(self._children.values()):
			ppt.app.size = win_size
			scrn = all_scrn[i // m]
			x_step = ((scrn[2] - scrn[0]) - win_size[0]) // (m - 1)
			y_step = ((scrn[3] - scrn[1]) - win_size[1])
			if (((scrn[2] - scrn[0]) - win_size[0]) / (m - 1)) - x_step >= 0.5:
				x_step += 1
			x = scrn[0] + (x_step * (i % m))
			y = scrn[1] + (y_step * ((i % m) % 2))
			ppt.app.location = (x, y)

	# def get_puppet(self, ppt: Union[str, int, 'Puppet']) -> 'Puppet':
	# 	if type(ppt) is str:
	# 		if ppt in self._children:
	# 			ppt = self.__getattribute__(ppt)
	# 		elif ppt.startswith('ppt') and ppt[3:].isnumeric():
	# 			ppt = int(ppt[3:])
	# 		else:
	# 			raise ValueError()
	# 	if type(ppt) is int:
	# 		if 0 <= ppt < len(self.children()):
	# 			ppt = self.children()[ppt]
	# 		else:
	# 			raise ValueError()
	# 	if ppt is not None and ppt not in self.children():
	# 		raise ValueError()
	# 	if ppt is None:
	# 		for ch in self.children():
	# 			# print(ch, ch.status)
	# 			if ch.status == 'Idle':
	# 				ppt = ch
	# 				break
	# 		else:
	# 			raise ValueError()
	# 	return ppt

	# def wait_for_puppets(self, puppets, max_time=10):
	# 	puppets = [self.get_puppet(ppt) for ppt in puppets]
	# 	res = []
	# 	timer = Timer.start()
	# 	while len(res) < len(puppets):
	# 		if __debug__:
	# 			pass
	# 		sleep(0.001)
	# 		for ppt in puppets:
	# 			res2 = ppt.get_output()
	# 			if res2:
	# 				res.append(res2)
	# 			elif ppt.status == 'Idle':
	# 				res.append(ppt.status)
	# 		if timer.lap() > max_time:
	# 			raise TimeoutError()

	def optimize_time(self):
		raise NotImplementedError

	def __iter__(self):
		return (x for x in self._children.values())

	def __enter__(self):
		return self

	def __exit__(self, etype, value, traceback):
		procs = [ch.app for ch in self]
		self._children.clear()
		for p in procs:
			# print(p)
			try:
				p.quick_log_out()
			except Exception:
				pass
			try:
				p.terminate()
			except psutil.NoSuchProcess:
				pass
		gone, still_alive = psutil.wait_procs(procs, timeout=3)
		for p in still_alive:
			# print(p)
			p.kill()

	def end(self):
		self.__exit__(None, None, None)

class SyteLinePuppetMasterBase(PuppetMaster):
	def __init__(self, n: int, fp=application_filepath, opt: bool = True):
		# print(n, forms)
		user_list = ['bigberae', username, 'BISync01', 'BISync02', 'BISync03']
		pwd_list = ['W!nter17', password, 'N0Trans@cti0ns', 'N0Re@s0ns', 'N0Gue$$!ng']
		super().__init__(fp, n, opt)
		for ppt, usr, pwd in zip([x for x in self], user_list, pwd_list):
			ppt.start(ppt.app.quick_log_in, usr, pwd)
		timer = Timer.start()

		while not all([x.ready() for x in self]):
			if timer.lap() > 30:
				raise TimeoutError

		self.optimize_screen_space(screen_pref='left')


class SyteLinePuppetMaster(SyteLinePuppetMasterBase):
	_instance = None  # Keep instance reference

	def __new__(cls, *args, **kwargs):
		"""Singleton"""
		if not cls._instance:
			cls._instance = SyteLinePuppetMasterBase.__new__(cls)
		return cls._instance


__all__ = ['SyteLinePuppetMaster', 'PuppetMaster']
