#! python3 -W ignore
# coding=utf-8

import datetime
import decimal
import logging
import threading
from collections import Counter, UserDict, UserList, namedtuple
from time import sleep
from typing import Any, Iterable, List, Tuple, Union, Callable
import queue

import numpy as np
import pyautogui as pag
import pywinauto.findwindows
import pywinauto.timings
from _globals import *
from constants import SYTELINE_WINDOW_TITLE, row_number_regex
from pywinauto import WindowSpecification
from pywinauto.backend import registry
from pywinauto.base_wrapper import BaseWrapper
from pywinauto.controls import uia_controls
from pywinauto.win32structures import RECT
from utils.tools import get_screen_exact, just_over_half, split_RECT

from core.Application import Application

log = logging.getLogger('root')
free = True

# THINK: Maybe Cell class?
class Cell:
	def __init__(self, cell: uia_controls.ListItemWrapper):
		self.cell_control = cell
		self.color = (255, 255, 255)
		self.value = cell.legacy_properties()['Value'].strip()

	def update_color(self):
		rect = self.cell_control.rectangle()
		scrn = get_screen_exact()
		partial = np.array(scrn)[rect.top:rect.bottom, rect.left:rect.right]
		count = Counter()
		for y in range(partial.shape[0]):
			for x in range(partial.shape[1]):
				count[str(partial[y, x].tolist())] += 1
		color_str = count.most_common(1)[0][0].strip('[] ').replace(', ', ',')
		self.color = [int(x) for x in color_str.split(',')]
		return self.color


# THINK: Maybe Row class?
class Row(UserDict):
	def __init__(self, columns: Union[str, Iterable[str]]):
		if type(columns) is str:
			columns = [columns]
		super().__init__((col, None) for col in columns)


# THINK: Maybe Column class?
class Column(UserList):
	type_hierarchy = {0: lambda x: None, 1: bool, 2: int, 3: float}
	type_hierarchy_r = {str(type(None)): 0, str(bool): 1, str(int): 2, str(float): 3}

	def __init__(self, name, *args):
		self.name = name
		self._type_rank = 0
		for arg in args:
			self.type_rank = self.type_hierarchy_r[str(type(arg))]
		super().__init__(args)

	def update_types(self):
		for i, val in enumerate(self.data):
			self.data[i] = self.type_rank(val)

	@property
	def type_rank(self):
		return self.type_hierarchy[self._type_rank]

	@type_rank.setter
	def type_rank(self, value):
		assert type(value) is int
		old_rank = self._type_rank
		self._type_rank = max(self._type_rank, value)
		if old_rank != self._type_rank:
			self.update_types()

	def __setitem__(self, i, value):
		assert type(i) is int
		type_num = self.type_hierarchy_r[str(type(value))]
		self.type_rank = type_num
		if type_num >= self._type_rank:
			self.data[i] = self.type_rank(value)
		elif value is None:
			self.data[i] = value


class DataGrid:
	# TODO: Dynamic type checking for DataRow and DataColumn NamedTuple's
	# TODO: General refinement/redundancy reduction
	# TODO: __iter__ attribute iterates through grid much like numpy-array
	# TODO: Maybe __contains__ returns all instances/first instance of value
	# TODO: Auto-detect max number of rows
	# TODO: Multi-threaded grid population
	def __init__(self, grid: uia_controls.ListViewWrapper, columns: Union[str, Iterable[str]], row_limit: int):
		if type(columns) is str:
			columns = [columns]
		self.grid_control = grid
		self.row_limit = row_limit
		DataRow = namedtuple('DataRow', field_names=[col.replace(' ', '_') for col in columns])
		retval = [DataRow(**{col.replace(' ', '_'): (
			self.get_cell_value(self._get_cell_control(row_index + self.get_row_index(1), col)),
			self._get_cell_control(row_index + self.get_row_index(1), col)) for col in columns}) for row_index, i in
		          enumerate(grid.children()[self.get_row_index(1):])]
		# TODO: Row and column type setting based on populated cells
		# self.DataRow = NamedTuple('DataRow', field_names=[col.replace(' ', '_') for col in columns])
		self.DataRow = DataRow
		self.DataColumn = namedtuple('DataRow', field_names=[f'Row{i}' for i in range(1, len(retval) + 1)])
		self.grid = retval
		old_rect = grid.rectangle()
		h = self._get_row_control(self.top_row_index).rectangle().height()
		self.visibility_window = {'left':   old_rect.left, 'top': old_rect.top - h, 'right': old_rect.right,
		                          'bottom': old_rect.bottom}

	@classmethod
	def from_name(cls, app: Application, name: str = 'DataGridView', columns: Union[str, Iterable[str]] = None, row_limit: int = None):
		sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
		name_new = name.title().replace(' ', '')
		grid = uia_controls.ListViewWrapper(sl_uia.__getattribute__(name_new).element_info)
		return cls(grid, columns, row_limit)

	@property
	def top_row_index(self) -> int:
		return self.get_row_index('Top Row')

	def get_row_index(self, row: Union[str, int]) -> int:
		if type(row) is str:
			return self.grid_control.children_texts().index(row)
		else:
			return self.grid_control.children_texts().index(f"Row {row-1}")

	def get_column_index(self, name: str) -> int:
		"""top_row_index = self.get_row_index('Top Row')
		children = self.grid_control.children()
		child = children[top_row_index]
		gen2_children_texts = child.children_texts()
		col_index = gen2_children_texts.index(name)
		return col_index"""
		return self.grid_control.children()[self.top_row_index].children_texts().index(name)

	def get_row_control(self, row: Union[str, int]) -> uia_controls.ListViewWrapper:
		row_index = self.get_row_index(row)
		return self._get_row_control(row_index)

	def _get_row_control(self, row_index: int) -> uia_controls.ListViewWrapper:
		"""children = self.grid_control.children()
		new_row = children[row_index]
		row_control = uia_controls.ListViewWrapper(new_row.element_info)
		return row_control"""
		return uia_controls.ListViewWrapper(self.grid_control.children()[row_index].element_info)

	def get_cell_control(self, row: Union[str, int], col: str) -> uia_controls.ListItemWrapper:
		row_index = self.get_row_index(row)
		return self._get_cell_control(row_index, col)

	def _get_cell_control(self, row_index: int, col: str) -> uia_controls.ListItemWrapper:
		"""row = self._get_row_control(row_index)
		item_index = self.get_column_index(col)
		item = row.item(item_index)
		element_info = item.element_info
		return uia_controls.ListItemWrapper(element_info)"""
		return uia_controls.ListItemWrapper(
				self._get_row_control(row_index).item(self.get_column_index(col)).element_info)

	def is_row_visible(self, row: Union[str, int]) -> bool:
		row_index = self.get_row_index(row)
		return self._is_row_visible(row_index)

	def _is_row_visible(self, row_index: int) -> bool:
		rect = self._get_row_control(row_index).rectangle()
		h = rect.height() // 2
		return ((self.visibility_window['bottom'] - h) > rect.top) and (
			(self.visibility_window['top'] + h) < rect.bottom)

	def get_cell_value(self, cell: uia_controls.ListItemWrapper) -> Any:
		return self.adapt_cell(cell.legacy_properties()['Value'].strip())

	@staticmethod
	def adapt_cell(value):
		if value == '(null)':
			return None
		elif value == 'False':
			return False
		elif value == 'True':
			return True
		else:
			try:
				retval = decimal.Decimal(value)
			except decimal.InvalidOperation:
				pass
			else:
				retval = retval.normalize()
				if int(retval) == retval:
					return int(retval)
				else:
					return float(retval)
		return value

	@staticmethod
	def upper_center(x1: int, y1: int, x2: int, y2: int) -> Tuple[int, int]:
		assert 0 < x1 < x2
		assert 0 < y1 < y2
		x2 -= x1
		y2 -= y1
		return x1 + (x2 // 2), y1 + (y2 // 3)

	def get_column(self, column: Union[str, int]):
		if type(column) is str:
			return self.DataColumn(*[row.__getattribute__(column) for row in self.grid])
		else:
			return self.DataColumn(*[row[column] for row in self.grid])

	def get_row(self, row_num: int):
		return self.grid[row_num - 1]

	def get_cell(self, column: Union[str, int], row_num: int) -> uia_controls.ListItemWrapper:
		if type(column) is str:
			return self.grid[row_num - 1].__getattribute__(column.replace(' ', '_'))[1]
		else:
			return self.grid[row_num - 1][column][1]

	def __getitem__(self, key) -> Any:
		# TODO: singular key -> regular getitem method
		column, row_num = key
		return self.get_cell_value(self.get_cell(column, row_num))

	def __setitem__(self, key, value) -> bool:
		# TODO: singular key -> regular setitem method
		column, row_num = key
		if not self.is_row_visible(row_num):
			pag.scroll(-20)
		if not self.is_row_visible(row_num):
			pag.scroll(40)
		if not self.is_row_visible(row_num):
			return False
		cell = self.get_cell(column, row_num)
		rect = cell.rectangle()
		x, y = self.upper_center(rect.left, rect.top, rect.right, rect.bottom)
		pag.click(x, y)
		sleep(0.2)
		pag.typewrite(str(value))
		sleep(0.2)

	# TODO: Verify correct row creation


class DataGridNEW:
	# TODO: This^
	# TODO: Base on pywinauto.controls.uia_controls.ListViewWrapper
	# TODO: Multithreaded grid population
	_type_dict = {0: bool, 1: int, 2: float, 3: datetime.datetime}
	q = queue.Queue()
	_workers = []

	def __init__(self, control: WindowSpecification, columns: Union[str, Iterable[str]], rows: int):
		# TODO: If columns and/or rows == None, auto-detect
		assert control.backend == registry.backends['uia']
		self.window_spec = control
		self.control = uia_controls.uiawrapper.UIAWrapper(control.element_info)
		self.scrollbar_h = self.window_spec.child_window(title='Horizontal Scroll Bar')
		self.scrollbar_v = self.window_spec.child_window(title='Vertical Scroll Bar')
		self.top_row = self.window_spec.child_window(title='Top Row')
		if columns:
			self.column_names = columns
		else:
			self.column_names = self.get_column_names()
		self.column_number_dict = {i: name for i, name in enumerate(self.column_names)}
		self.column_name_dict = {}
		try:
			for i, name in enumerate(self.get_column_names()):
				if name not in self.column_name_dict:
					self.column_name_dict[name] = i
		except Exception:
			pass
		self.master_grid = np.empty((self.row_count, len(self.column_names), 3), dtype=object)
		self.grid = self.master_grid[..., 0].view()
		self.types_grid = self.master_grid[..., 1].view()
		self.visibility_grid = self.master_grid[..., 2].view().astype(dtype=np.bool_, copy=False)
		for row in self.control.children():
			# if row_number_regex.fullmatch(row.texts()[0].strip()):
			# 	log.debug("Row", str(int(row_number_regex.fullmatch(row.texts()[0].strip()).group('row_number')) + 1))
			log.debug(row.texts()[0])

	@property
	def row_count(self) -> int:
		return self.count_rows()

	@property
	def element_info(self):
		return self.control.element_info

	# def apply_all(self, func: Callable, *args, **kwargs):
	# 	with ThreadPoolExecutor(max_workers=len(self.children())) as e:
	# 		for ch in self.children():
	# 			e.submit(func, ch, *args, **kwargs)
	# 			sleep(1)

	@property
	def grid_area(self) -> RECT:
		x1, y1, x2, y2 = split_RECT(self.control)
		row_header_width = column_header_height = vertical_scrollbar_width = horizontal_scrollbar_height = 0

		top_row_rect = self.top_row.rectangle()
		first_column_rect = self.top_row.child_window(title=self.column_names[0]).rectangle()
		corner_rect = RECT(top_row_rect.left, top_row_rect.top, first_column_rect.right, top_row_rect.bottom)

		column_header_height = corner_rect.height()
		row_header_width = corner_rect.width()

		if self.scrollbar_h.exists():
			horizontal_scrollbar_rect = self.scrollbar_h.rectangle()
			horizontal_scrollbar_height = horizontal_scrollbar_rect.height()

		if self.scrollbar_v.exists():
			vertical_scrollbar_rect = self.scrollbar_v.rectangle()
			vertical_scrollbar_width = vertical_scrollbar_rect.width()

		return RECT((x1 + row_header_width),
		            (y1 + column_header_height),
		            (x2 - vertical_scrollbar_width),
		            (y2 - horizontal_scrollbar_height))

	@classmethod
	def from_name(cls, app: Application, name: str, columns: Union[str, Iterable[str]] = None, rows: int = None):
		sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
		return cls(sl_uia.__getattribute__(name), columns, rows)

	@classmethod
	def from_AutomationId(cls, app: Application, auto_id: str, columns: Union[str, Iterable[str]] = None, rows: int = None):
		sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
		return cls(sl_uia.child_window(auto_id=auto_id), columns, rows)

	@classmethod
	def default(cls, app: Application, columns: Union[str, Iterable[str]] = None, rows: int = None):
		return cls.from_name(app, 'DataGridView', columns, rows)

	def select_cell(self, cell: WindowSpecification):
		cell.invoke()

	def legacy_populate(self):
		for y in np.arange(self.grid.shape[0], dtype=np.intp):
			for x in np.arange(self.grid.shape[1], dtype=np.intp):
				col = self.column_number_dict[x]
				try:
					cell = self.get_cell(col, y + 1)
					self.grid[y, x] = self.pyType_to_cellType(cell.iface_value.CurrentValue)
				except Exception:
					cell = self.get_cell(col, y + 1, specific=1)
					self.grid[y, x] = self.pyType_to_cellType(cell.iface_value.CurrentValue)

	def parse_row(self, y: int, row_values: str):
		if isinstance(row_values, list) or isinstance(row_values, tuple):
			row_values = row_values[0]
		row = [self.pyType_to_cellType(val.strip()) for val in row_values.split(';')]
		if not (len(row) == 1 and row[0] == '(Create New)'):
			for x, name in enumerate(self.column_names):
				i = self.column_name_dict[name]
				self.grid[y, x] = row[i]

	# col = self.column_number_dict[x]
	# try:
	# 	cell = self.get_cell(col, y + 1)
	# 	self.grid[y, x] = self.pyType_to_cellType(cell.iface_value.CurrentValue)
	# except Exception:
	# 	cell = self.get_cell(col, y + 1, specific=1)
	# 	self.grid[y, x] = self.pyType_to_cellType(cell.iface_value.CurrentValue)

	def get_rows(self):
		return {int(row_number_regex.fullmatch(row.texts()[0].strip()).group('row_number')): row for row in self.control.children() if row_number_regex.fullmatch(row.texts()[0].strip())}

	def populate(self):
		# TODO: Only do requested columns and/or rows
		# THINK: Use row value string to define values?
		rows = self.get_rows()
		for i, row in rows.items():
			worker = threading.Thread(target=self.parse_row, args=(i, row.legacy_properties()['Value']), daemon=True)
			worker.start()
		worker.join()

	def row(self, name: str):
		pywinauto.timings.wait_until_passes(20, 0.09, self.control.children, ValueError)
		retval = [row for row in self.control.children() if row.texts()[0].strip() == name]
		if retval:
			return retval[0]
		else:
			return None

	def count_rows(self) -> int:
		pywinauto.timings.wait_until_passes(20, 0.09, self.control.children, ValueError)
		return max([int(row_number_regex.fullmatch(row.texts()[0].strip()).group('row_number')) + 1 for row in self.control.children() if row_number_regex.fullmatch(row.texts()[0].strip())] + [0, 0])

	def get_column_names(self) -> List[str]:
		pywinauto.timings.wait_until_passes(20, 0.09, self.control.children, ValueError)
		return [col.texts()[0].strip() for col in self.top_row.children() if col.texts()[0]]

	def get_cell(self, column: str, row: int, *, visible_only: bool = False, specific: int = 0) -> Union[WindowSpecification, List[WindowSpecification]]:
		log.debug(f'{column} Row {row - 1} Started')
		if row > self.row_count:
			return None
		column_count = self.column_names.count(column)
		for x in range(3):
			log.debug(f'{column} Row {row - 1} Iteration {x+1}')
			specific += x
			if column_count > 1:  # Best-Match method, slower
				if specific:
					return self.window_spec.child_window(best_match=f'{column}Row{row - 1}DataItem{specific}', visible_only=visible_only)
				return [self.window_spec.child_window(best_match=f'{column}Row{row - 1}DataItem{i + 1}', visible_only=visible_only) for i in range(column_count)]
			elif specific:
				return self.window_spec.child_window(best_match=f'{column}Row{row - 1}DataItem{specific}', visible_only=visible_only)
			else:  # Title-Match method, faster & more precise
				log.debug(f'{column} Row {row - 1} Completed')
				return self.window_spec.child_window(title=f'{column} Row {row - 1}', visible_only=visible_only)

	def set_cell(self, column: str, row: int, value, *, visible_only: bool = False, specific: int = 0):
		cell = self.get_cell(column, row, visible_only=visible_only, specific=specific)
		if str(value) in {'True', 'False'}:
			pass
		else:
			global free
			while not free:
				sleep(0.01)
			else:
				free = False
				try:
					self.select_cell(cell)
					cell.iface_value.SetValue(str(value))
					valid = self.validate_cell(cell)
					if not valid:
						raise ZeroDivisionError()
				except Exception as ex:
					raise ex
				finally:
					free = True
		self.update_grid_size()
		self.grid[row, self.column_names.index(column)] = self.pyType_to_cellType(cell.iface_value.CurrentValue)

	def worker_thread(self, value, column, row, func: Callable, *args, **kwargs):
		cell = func(*args, **kwargs)
		self.q.put((value, column, row, cell, uia_controls.EditWrapper(cell.element_info)))

	def quick_set_cell(self, column: str, row: int, value, *, visible_only: bool = False, specific: int = 0):
		worker = threading.Thread(target=self.worker_thread, args=(value, column, row, self.get_cell, column, row), kwargs={'visible_only': visible_only, 'specific': specific}, daemon=True)
		worker.start()
		self._workers.append(worker)

	def quick_set_execute(self):
		while not self.q.empty():
			value, column, row, cell, edit_control = self.q.get()
			cell.click_input()
			edit_control.type_keys(str(value) + '{ENTER 5}', with_spaces=True, with_newlines=True)
			self.grid[row, self.column_names.index(column)] = self.pyType_to_cellType(cell.iface_value.CurrentValue)
		self.update_grid_size()
		self._workers.clear()

	def quick_set_cell_alt(self, column: str, row: int, value, *, visible_only: bool = False, specific: int = 0):
		cell = self.get_cell(column, row, visible_only=visible_only, specific=specific)
		edit_control = uia_controls.EditWrapper(cell.element_info)
		cell.click_input()
		edit_control.type_keys(str(value) + '{ENTER 8}', with_spaces=True, with_newlines=True)
		# self.grid[row, self.column_names.index(column)] = self.pyType_to_cellType(cell.iface_value.CurrentValue)
		self.update_grid_size()

	def set_cells(self, *args: List[Tuple[str, int, Any]]):
		for column, row, value in args:
			worker = threading.Thread(target=self.set_cell, args=(column, row, value))
			worker.start()

	def update_grid_size(self):
		old_shape = self.master_grid.shape
		zero_pad = np.zeros((1, old_shape[1], old_shape[2]))
		while self.master_grid.shape[0] < self.row_count:
			self.master_grid = np.vstack((self.master_grid, zero_pad))
		new_shape = self.master_grid.shape
		if old_shape != new_shape:
			self.grid = self.master_grid[..., 0].view()
			self.types_grid = self.master_grid[..., 1].view()
			self.visibility_grid = self.master_grid[..., 2].view().astype(dtype=np.bool_, copy=False)
			log.debug(f"Master Grid shape changed from {old_shape} to {new_shape}")

	# TODO: singledispatch for cell input and column/row input
	def validate_cell(self, cell: WindowSpecification) -> bool:
		value = cell.iface_value.CurrentValue.strip()
		cell.click_input()
		edit_control = uia_controls.EditWrapper(cell.element_info)
		edit_control.type_keys(value + '{ENTER 20}', with_spaces=True, with_newlines=True)
		return cell.iface_value.CurrentValue.strip() == value

	def get_visible_cells(self):
		max_x = max_y = min_x = min_y = None
		for i in np.arange(min(self.grid.shape[:2]), dtype=np.intp):
			y = x = i
			col = self.column_number_dict[x]
			column_count = self.column_names.count(col)
			specific = 1
			if column_count > 1:
				column_count_dict = {k2: i for i, k2 in enumerate({k: v for k, v in self.column_number_dict.items() if v == col}.keys())}
				specific += column_count_dict[x]
			cell = self.get_cell(col, y, specific=specific)
			visible = cell.is_visible()
			self.visibility_grid[y, x] = visible
			if min_x is None and visible:
				min_x = min_y = i
			elif min_x is not None and not visible:
				max_x = max_y = i - 1
				break

		for dim in ('max', 'min'):
			while True:
				try:
					if dim == 'max':
						x2, y2 = x, y = max_x, max_y
						while True:
							x2 += 1
							if x2 >= self.grid.shape[1]:
								max_x = x2 - 1
								break
							col = self.column_number_dict[x2]
							column_count = self.column_names.count(col)
							specific = 1
							if column_count > 1:
								column_count_dict = {k2: i for i, k2 in enumerate({k: v for k, v in self.column_number_dict.items() if v == col}.keys())}
								specific += column_count_dict[x2]
							cell = self.get_cell(col, y, specific=specific)
							visible = cell.is_visible()
							self.visibility_grid[y, x2] = visible
							if not visible:
								max_x = x2 - 1
								break
						while True:
							y2 += 1
							if y2 >= self.grid.shape[0]:
								max_y = y2 - 1
								break
							col = self.column_number_dict[x]
							column_count = self.column_names.count(col)
							specific = 1
							if column_count > 1:
								column_count_dict = {k2: i for i, k2 in enumerate({k: v for k, v in self.column_number_dict.items() if v == col}.keys())}
								specific += column_count_dict[x]
							cell = self.get_cell(col, y2, specific=specific)
							visible = cell.is_visible()
							self.visibility_grid[y2, x] = visible
							if not visible:
								max_y = y2 - 1
								break
					elif dim == 'min':
						x2, y2 = x, y = min_x, min_y
						while True:
							x2 -= 1
							if x2 < 0:
								min_x = x2 + 1
								break
							col = self.column_number_dict[x2]
							column_count = self.column_names.count(col)
							specific = 1
							if column_count > 1:
								column_count_dict = {k2: i for i, k2 in enumerate({k: v for k, v in self.column_number_dict.items() if v == col}.keys())}
								specific += column_count_dict[x2]
							cell = self.get_cell(col, y, specific=specific)
							visible = cell.is_visible()
							self.visibility_grid[y, x2] = visible
							if not visible:
								min_x = x2 + 1
								break
						while True:
							y2 -= 1
							if y2 < 0:
								min_y = y2 + 1
								break
							col = self.column_number_dict[x]
							column_count = self.column_names.count(col)
							specific = 1
							if column_count > 1:
								column_count_dict = {k2: i for i, k2 in enumerate({k: v for k, v in self.column_number_dict.items() if v == col}.keys())}
								specific += column_count_dict[x]
							cell = self.get_cell(col, y2, specific=specific)
							visible = cell.is_visible()
							self.visibility_grid[y2, x] = visible
							if not visible:
								min_y = y2 + 1
								break
				except Exception:
					break

		return min_x, min_y, max_x, max_y

	@staticmethod
	def get_min_area(cell: BaseWrapper, *, anchor: str) -> RECT:
		rect = cell.rectangle()
		w, h = rect.width(), rect.height()
		w_factor, h_factor = [min(2 ** x for x in range(3, 10) if (just_over_half(y, x) - z) < 10) for y, z in ((w, w / 2), (h, h / 2))]
		left, top, right, bottom = split_RECT(cell)

		if 'l' in anchor:
			right = left + int(w * w_factor)
		elif 'r' in anchor:
			left = right - int(w * w_factor)

		if 't' in anchor:
			bottom = top + int(h * h_factor)
		elif 'b' in anchor:
			top = bottom - int(h * h_factor)

		return RECT(left, top, right, bottom)

	@staticmethod
	def pyType_to_cellType(value):
		# TODO: Regex for datetime, Item Number, etc
		if value == '(null)':
			value = 'None'
		if '-' in value:
			retval = value
		elif '/' in value and ':' in value:
			retval = datetime.datetime.strptime(value, '%m/%d/%y %H:%M:%S')
		elif '/' in value:
			retval = datetime.datetime.strptime(value, '%m/%d/%Y').date()
		elif ':' in value:
			retval = datetime.datetime.strptime(value, '%H:%M:%S').time()
		else:
			try:
				retval = eval(value)
			except Exception:
				retval = value
		return retval

	@staticmethod
	def cellType_to_pyType(value):
		# TODO: Regex for datetime, Item Number, etc
		if value == None:
			value = '(null)'
		if '-' in value:
			retval = value
		elif '/' in value and ':' in value:
			retval = datetime.datetime.strptime(value, '%m/%d/%y %H:%M:%S')
		elif '/' in value:
			retval = datetime.datetime.strptime(value, '%m/%d/%Y').date()
		elif ':' in value:
			retval = datetime.datetime.strptime(value, '%H:%M:%S').time()
		else:
			try:
				retval = eval(value)
			except Exception:
				retval = value
		return retval


__all__ = ['DataGridNEW']
