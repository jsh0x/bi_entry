# coding=utf-8
import pathlib
from typing import Iterable, Optional, Union

import psutil


def process_pid(filename: str, exclude: Optional[Union[int, Iterable[int]]] = None) -> int:
	if isinstance(filename, pathlib.Path):
		filename = filename.name
	for proc in psutil.process_iter():
		try:
			if exclude is not None and ((isinstance(exclude, int) and proc.pid == exclude) or proc.pid in exclude):
				continue
			if proc.name().lower() == filename.lower():
				return proc.pid
		except psutil.NoSuchProcess:
			pass
	return None


def is_running(filename: str, exclude: Optional[Union[int, Iterable[int]]] = None) -> bool:
	# processes = win32process.EnumProcesses()    # get PID list
	# for pid in processes:
	# 	try:
	# 		if exclude is not None and ((type(exclude) is int and exclude == pid) or (pid in exclude)):
	# 			continue
	# 		handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid)
	# 		exe = win32process.GetModuleFileNameEx(handle, 0)
	# 		if exe.lower() == filename.lower():
	# 			return True
	# 	except:
	# 		pass
	# return False
	if isinstance(filename, pathlib.Path):
		filename = filename.name
	for proc in psutil.process_iter():
		try:
			if exclude is not None and ((isinstance(exclude, int) and proc.pid == exclude) or proc.pid in exclude):
				continue
			if proc.name().lower() == filename.lower():
				return True
		except (psutil.NoSuchProcess, psutil.AccessDenied):
			pass
	return False


__all__ = ['process_pid', 'is_running']
