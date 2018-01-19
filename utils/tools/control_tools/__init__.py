# coding=utf-8
from functools import singledispatch
from typing import Tuple

import pywinauto as pwn
from pywinauto import WindowSpecification
from pywinauto.backend import registry
from pywinauto.base_wrapper import BaseWrapper
from pywinauto.win32structures import RECT

__all__ = ['swap_backend', 'split_RECT', 'center']

from . import cell_tools
from .cell_tools import *

__all__ += cell_tools.__all__

def swap_backend(control: WindowSpecification) -> WindowSpecification:
	if control.handle is None:
		return control
	if control.backend == registry.backends['uia']:
		app = pwn.Application(backend='win32').connect(process=control.process_id())
	elif control.backend == registry.backends['win32']:
		app = pwn.Application(backend='uia').connect(process=control.process_id())
	return app.window(handle=control.handle)


@singledispatch
def split_RECT(control: BaseWrapper) -> Tuple[int, int, int, int]:
	rect = control.rectangle()
	return rect.left, rect.top, rect.right, rect.bottom


@split_RECT.register(RECT)
def _(control):
	return control.left, control.top, control.right, control.bottom


# Not one Item Price exists for Item that has
@singledispatch
def center(arg) -> Tuple[int, int]:
	"""Return the center of given coordinates.
	:rtype: tuple
	"""
	x1, y1, x2, y2 = split_RECT(arg)
	x2 -= x1
	y2 -= y1
	return x1 + (x2 // 2), y1 + (y2 // 2)


@center.register(int)
def _(arg, y1: int, x2: int, y2: int) -> Tuple[int, int]:
	assert 0 < arg < x2
	assert 0 < y1 < y2
	x2 -= arg
	y2 -= y1
	return arg + (x2 // 2), y1 + (y2 // 2)
