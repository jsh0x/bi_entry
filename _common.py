#!/usr/bin/env python
import datetime
import decimal
import logging
import pathlib
import re
import threading
from collections import Counter, UserDict, UserList, defaultdict, namedtuple
from concurrent.futures import ThreadPoolExecutor
from string import punctuation, ascii_lowercase
from random import choices
from sys import exc_info
from time import sleep
from typing import Any, Callable, Dict, Iterable, List, NamedTuple, Optional, Tuple, Union
from numbers import Number
import queue

import numpy as np
import pprofile
import psutil
import pyautogui as pag
import pywinauto as pwn
import win32gui
from PIL import ImageGrab
from pywinauto.controls import common_controls, uia_controls, win32_controls

from config import *
from constants import (CARRIER_DICT, CELLULAR_BUILDS, REGEX_BUILD, REGEX_BUILD_ALT, REGEX_RESOLUTION,
                       REGEX_WINDOW_MENU_FORM_NAME, SUFFIX_DICT, SYTELINE_WINDOW_TITLE)
from exceptions import *


log = logging.getLogger(__name__)
completion_dict = {'Queued': 'C1', 'Scrap': 'C2', 'Reason': 'C3'}

Dialog = NamedTuple('Dialog', [('self', pwn.WindowSpecification), ('Title', str), ('Text', str),
                               ('Buttons', Dict[str, win32_controls.ButtonWrapper])])

observer_affect = lambda: sleep(0.0001)
# - - - - - - - - - - - - - - - - - - -  CLASSES  - - - - - - - - - - - - - - - - - - - -
# Move classes to bi_entry.py?
# TODO: DOCSTRINGS!!!

def legacy(func: Callable, *args, **kwargs):
	def wrapper(*args, **kwargs):
		log.debug(f"Function {func.__name__} is deprecated, avoid further usage!")
		return func(*args, **kwargs)

	return wrapper

# TODO: Refine Coordinates and Rectangle classes with properties: top, left, right, bottom, width, and height. Maybe __contains__?
class Coordinates(NamedTuple):
	x: int
	y: int

class Rectangle(NamedTuple):
	left: Coordinates
	top: Coordinates
	right: Coordinates
	bottom: Coordinates

class Part:
	def __init__(self, sql, part_number: str, quantity: int = 1, spec_build: str = None):
		if '-' in part_number:
			self.part_number = part_number
			"""# FOR 206's:
				;With t as 
				(Select DISTINCT [DispName], [PartNum] FROM [Parts] WHERE [Product] = 'HomeGuard' And [Operation] = 'Update' and [Build] = '206'
				Union All
				Select DISTINCT [DispName], [PartNum] FROM [Parts] WHERE [Product] = 'HomeGuard' And [Operation] = 'Update' and [Build] = 'All')
				Select distinct * from t"""
			if spec_build:
				_data = sql.execute(
					f"SELECT [Qty],[DispName],[Location],[PartName] FROM Parts WHERE [PartNum] = '{self.part_number}' AND [Build] = '{spec_build}'") if sql.execute(
					f"SELECT [Qty],[DispName],[Location],[PartName] FROM Parts WHERE [PartNum] = '{self.part_number}' AND [Build] = '{spec_build}'") \
					else sql.execute(
					f"SELECT [Qty],[DispName],[Location],[PartName] FROM Parts WHERE [PartNum] = '{self.part_number}'")
			else:
				_data = sql.execute(
					f"SELECT [Qty],[DispName],[Location],[PartName] FROM Parts WHERE [PartNum] = '{self.part_number}' AND [Build] = 'All'") if sql.execute(
					f"SELECT [Qty],[DispName],[Location],[PartName] FROM Parts WHERE [PartNum] = '{self.part_number}' AND [Build] = 'All'") \
					else sql.execute(
					f"SELECT [Qty],[DispName],[Location],[PartName] FROM Parts WHERE [PartNum] = '{self.part_number}'")
		else:
			_data = sql.execute(
				f"SELECT [PartNum],[Qty],[DispName],[Location],[PartName] FROM Parts WHERE [ID] = {part_number}")
			self.part_number = _data.PartNum
		self.quantity = quantity * _data.Qty
		self.display_name = _data.DispName
		self.part_name = _data.PartName
		self.location = _data.Location

	def __repr__(self):
		return f"<Part object; {self.part_number}x{self.quantity}>"

	def __str__(self):
		return f"{self.display_name}({self.part_number}) x {self.quantity}"

class Unit:
	def __init__(self, msssql, slsql, args: NamedTuple):
		self._msssql = msssql
		self._slsql = slsql
		self.version = version
		tbl_mod = table
		self._table = 'PyComm' if int(tbl_mod) else 'PyComm2'
		self.id, self.serial_number, self.operation, self.operator, self.datetime, self.notes, self._status = (
			args.Id, args.Serial_Number, args.Operation, args.Operator, args.DateTime, args.Notes, args.Status)
		self._status2 = self._status
		self._status = 'Queued' if self._status2 == 'Custom(Queued)' else self._status
		self.operation = self.operation.strip() if self.operation is not None else None
		self.operator = self.operator.strip() if self.operator is not None else None
		self.notes = self.notes.strip() if self.notes is not None else None
		log.debug(f"Attribute id={self.id}")
		log.debug(f"Attribute serial_number='{self.serial_number}'")
		log.debug(f"Attribute operation='{self.operation}'")
		log.debug(f"Attribute operator='{self.operator}'")
		log.debug(f"Attribute notes='{self.notes}'")
		log.debug(f"Attribute _status='{self._status}'")
		log.debug(f"Property datetime='{self.datetime}'")
		"""From PyComm p
				Cross apply dbo.Split(p.Parts, ',') b
				Inner join Parts n
				on b.items = n.PartNum
				Where p.[Serial Number] = @SN
		"""
		self._serial_number_prefix = self._product = self.whole_build = self._operator_initials = self.eff_date = self.sro_num = self.sro_line = self.SRO_Operations_status = self.SRO_Line_status = None
		self.parts_transacted = []
		self.timer = TestTimer()
		self._life_timer = TestTimer()
		self._life_timer.start()
		self._start_time = datetime.datetime.now().time().strftime("%H:%M:%S.%f")
		self._date = datetime.datetime.now().date().strftime("%Y-%m-%d")
		self.sro_operations_time = datetime.timedelta(0)
		self.sro_transactions_time = datetime.timedelta(0)
		self.misc_issue_time = datetime.timedelta(0)
		self.sro_operations_timer = TestTimer()
		self.sro_transactions_timer = TestTimer()
		self.misc_issue_timer = TestTimer()
		log.debug(f"Property product='{self.product}'")
		log.debug(f"Property operator_initials='{self.operator_initials}'")
		sn1 = sn2 = f"{self.serial_number_prefix}{self.serial_number}"
		if self.serial_number_prefix == 'BE':
			sn2 = f"ACB{self.serial_number}"
		build_data = self._slsql.execute("Select top 1 * from ("
		                                 "select ser_num, item, "
		                                 "Case when loc is null then 'Out of Inventory' "
		                                 "else loc "
		                                 "end as [Inv_Stat], whse "
		                                 f"from serial (nolock) where ser_num = '{sn1}' "
		                                 "Union All "
		                                 "select ser_num, item, "
		                                 "Case when loc is null then 'Out of Inventory' "
		                                 "else loc "
		                                 "end as [Inv_Stat], whse "
		                                 f"from serial (nolock) where ser_num = '{sn2}') t")
		if build_data is None:
			if self._status.lower() != 'scrap':
				raise NoSROError(serial_number=self.serial_number)
			loc, whse = 'Out of Inventory', None
			gc, item = self.get_serial_build()
			log.debug(f"Property serial_number_prefix='{self.serial_number_prefix}'")
			self.update_sl_data()
		else:
			gc, item, loc, whse = build_data
			if gc.upper().startswith('BE'):
				self.serial_number_prefix = 'BE'
			elif gc.upper().startswith('ACB'):
				self.serial_number_prefix = 'ACB'
			log.debug(f"Property serial_number_prefix='{self.serial_number_prefix}'")
			self.update_sl_data()
		if self.sl_data is None:
			self.sro_num, self.sro_line, self.eff_date, self.SRO_Line_status, self.SRO_Operations_status = None, None, None, 'Closed', 'Closed'
		log.debug(f"Attribute sro_num='{self.sro_num}'")
		log.debug(f"Attribute sro_line='{self.sro_line}'")
		log.info(f"Unit sro_num='{self.sro_num}'")
		log.info(f"Unit sro_line='{self.sro_line}'")
		log.debug(f"Attribute eff_date='{self.eff_date}'")
		log.debug(f"Attribute SRO_Line_status='{self.SRO_Line_status}'")
		log.debug(f"Attribute SRO_Operations_status='{self.SRO_Operations_status}'")
		self._regex_dict = REGEX_BUILD_ALT.match(item.upper()).groupdict(default='-') if REGEX_BUILD_ALT.match(
			item.upper()) is not None else REGEX_BUILD.match(item.upper()).groupdict(default='-')
		log.debug(self._regex_dict.items())
		self.location = loc
		log.debug(f"Attribute location='{self.location}'")
		self.warehouse = whse
		log.debug(f"Attribute warehouse='{self.warehouse}'")
		self.build = self._regex_dict['build'][1:] if self._regex_dict['carrier'].isnumeric() else self._regex_dict[
			                                                                                           'build'][:3]
		log.debug(f"Attribute build='{self.build}'")
		self.suffix = SUFFIX_DICT[self._regex_dict['suffix']]
		log.debug(f"Attribute suffix='{self.suffix}'")
		self.whole_build = item.upper()
		log.debug(f"Attribute whole_build='{self.whole_build}'")
		self.phone = self.whole_build in CELLULAR_BUILDS
		log.debug(f"Attribute phone={self.phone}")
		self.carrier = CARRIER_DICT[self._regex_dict['carrier']]
		log.debug(f"Attribute carrier='{self.carrier}'")
		if self._status.lower() != 'scrap' and self.SRO_Line_status == 'Closed':
			if self.sro_num is None:
				raise NoSROError(serial_number=str(self.serial_number))
			else:
				raise NoOpenSROError(serial_number=str(self.serial_number), sro=str(self.sro_num))
		self.parts = args.Parts
		log.debug(f"Property parts='{self.parts}'")
		self.general_reason = 1000
		self.specific_reason = 20
		self.general_resolution = 10000
		self.specific_resolution = 100
		if 'queued' not in self._status.lower():
			try:
				if 'queued' not in self._status.lower() and REGEX_RESOLUTION.match(self.notes):
					self.general_resolution, self.specific_resolution = [int(x) for x in
					                                                     REGEX_RESOLUTION.match(self.notes).groups()]
					if 'scrap' in self._status.lower():
						self.specific_resolution_name = self._status.upper()
					self.general_resolution_name = msssql.execute(
						f"SELECT TOP 1 [Failure] FROM FailuresRepairs WHERE [ReasonCodes] = '{self.notes}'")[0]
			except TypeError as ex:
				raise InvalidReasonCodeError(reason_code=str(self.notes), spec_id=str(self.id), msg=str(ex))
			# TODO: For HG, allow Invalid Reason Codes, just enter in operator initials
		if self._status.lower() != 'scrap':
			self.start()

	def start(self):
		self._msssql.execute(
			f"UPDATE {self._table} SET [Status] = 'Started({self._status2})' WHERE [Id] = {self.id} AND [Serial Number] = '{self.serial_number}'")
		self._life_timer = TestTimer()
		self._life_timer.start()
		self._start_time = datetime.datetime.now().time().strftime("%H:%M:%S.%f")
		self._date = datetime.datetime.now().date().strftime("%Y-%m-%d")

	def complete(self, batch_amt: int = None):
		if batch_amt is None:
			batch_amt = 10 if self._status.lower() == 'scrap' else 1
		log.debug(f"Batch amount: {batch_amt}")
		self.sro_operations_time += self.sro_operations_timer.stop()
		self.sro_transactions_time += self.sro_transactions_timer.stop()
		self.misc_issue_time += self.misc_issue_timer.stop()
		life_time = self._life_timer.stop().total_seconds()
		if len(self.parts_transacted) > 0:
			try:
				t_parts = ', '.join(x.part_number + ' x ' + str(x.quantity) for x in self.parts_transacted)
			except TypeError:
				t_parts = 'None'
		else:
			t_parts = 'None'
		process = 'Transaction' if self._status == 'Queued' else self._status
		life_time /= batch_amt
		end_time = datetime.datetime.now().time().strftime("%H:%M:%S.%f")
		len_parts = len(self.parts) if self.parts is not None else 0
		parts = ', '.join(
			x.part_number + ' x ' + str(x.quantity) for x in self.parts) if self.parts is not None else None
		carrier = self.carrier[0].upper() if self.carrier is not None else '-'
		self._msssql.execute("INSERT INTO [Statistics]"
		                     "([Serial Number],[Carrier],[Build],[Suffix],[Operator],[Operation],"
		                     "[Part Nums Requested],[Part Nums Transacted],[Parts Requested],[Parts Transacted],[Input DateTime],[Date],"
		                     "[Start Time],[SRO Operations Time],[SRO Transactions Time],[Misc Issue Time],[End Time],"
		                     "[Total Time],[Process],[Results],[Version])"
		                     f"VALUES ('{self.serial_number}','{carrier}','{self.build}',"
		                     f"'{self.suffix}','{self.operator}','{self.operation}','{parts}',"
		                     f"'{t_parts}',{len_parts},{len(self.parts_transacted)},"
		                     f"'{self.datetime.strftime('%m/%d/%Y %H:%M:%S')}','{self._date}','{self._start_time}',"
		                     f"{self.sro_operations_time.total_seconds()},{self.sro_transactions_time.total_seconds()},"
		                     f"{self.misc_issue_time.total_seconds()},'{end_time}',"
		                     f"{life_time},'{process}','Completed','{self.version}')")
		self._msssql.execute(
			f"UPDATE {self._table} SET [Status] = '{completion_dict[self._status]}' WHERE [Id] = {self.id} AND [Serial Number] = '{self.serial_number}'")

	def skip(self, reason: Optional[str] = None, batch_amt: int = None):
		if batch_amt is None:
			batch_amt = 10 if self._status.lower() == 'scrap' else 1
		log.debug(f"Batch amount: {batch_amt}")
		self.sro_operations_time += self.sro_operations_timer.stop()
		self.sro_transactions_time += self.sro_transactions_timer.stop()
		self.misc_issue_time += self.misc_issue_timer.stop()
		life_time = self._life_timer.stop().total_seconds()
		reason = 'Skipped' if reason is None else reason
		if len(self.parts_transacted) > 0:
			try:
				t_parts = ', '.join(x.part_number + ' x ' + str(x.quantity) for x in self.parts_transacted)
			except TypeError:
				t_parts = 'None'
		else:
			t_parts = 'None'
		process = 'Transaction' if self._status == 'Queued' else self._status
		life_time /= batch_amt
		end_time = datetime.datetime.now().time().strftime("%H:%M:%S.%f")
		len_parts = len(self.parts) if self.parts is not None else 0
		parts = ', '.join(
			x.part_number + ' x ' + str(x.quantity) for x in self.parts) if self.parts is not None else None
		addon = f"({sro})" if reason == 'No Open SRO' else ""
		carrier = self.carrier[0].upper() if self.carrier is not None else '-'
		self._msssql.execute(
			f"UPDATE {self._table} SET [Status] = '{reason}({self._status2}){addon}' WHERE [Id] = {self.id} AND [Serial Number] = '{self.serial_number}'")
		self._msssql.execute("INSERT INTO [Statistics]"
		                     "([Serial Number],[Carrier],[Build],[Suffix],[Operator],[Operation],"
		                     "[Part Nums Requested],[Part Nums Transacted],[Parts Requested],[Parts Transacted],[Input DateTime],[Date],"
		                     "[Start Time],[SRO Operations Time],[SRO Transactions Time],[Misc Issue Time],[End Time],"
		                     "[Total Time],[Process],[Results],[Reason],[Version])"
		                     f"VALUES ('{self.serial_number}','{carrier}','{self.build}',"
		                     f"'{self.suffix}','{self.operator}','{self.operation}','{parts}',"
		                     f"'{t_parts}',{len_parts},{len(self.parts_transacted)},"
		                     f"'{self.datetime.strftime('%m/%d/%Y %H:%M:%S')}','{self._date}','{self._start_time}',"
		                     f"{self.sro_operations_time.total_seconds()},{self.sro_transactions_time.total_seconds()},"
		                     f"{self.misc_issue_time.total_seconds()},'{end_time}',"
		                     f"{life_time},'{process}','Skipped','{reason}','{self.version}')")

	def reset(self):
		self._msssql.execute(
			f"UPDATE {self._table} SET [Status] = '{self._status2}' WHERE [Id] = {self.id} AND [Serial Number] = '{self.serial_number}'")

	def update_sl_data(self):
		try:
			self.sro_num, self.sro_line, self.eff_date, self.SRO_Operations_status, self.SRO_Line_status = self.sl_data
		except TypeError as ex:
			if re.search(r"NoneType.*not iterable", str(exc_info()[1])) is None:
				raise ex

	@property
	def sl_data(self) -> NamedTuple:
		return self._slsql.execute("Select TOP 1 s.sro_num, l.sro_line, c.eff_date as 'Eff Date', "
		                           "Case when o.stat = 'C' then 'Closed' else 'Open' end as [SRO Operation Status], "
		                           "Case when l.stat = 'C' then 'Closed' else 'Open' end as [SRO Line Status] "
		                           "From fs_sro s (nolock) "
		                           "Inner join fs_sro_line l (nolock) "
		                           "on s.sro_num = l.sro_num "
		                           "Inner join fs_unit_cons c (nolock) "
		                           "on l.ser_num = c.ser_num "
		                           "Inner join fs_sro_oper o (nolock) "
		                           "on l.sro_num = o.sro_num and l.sro_line = o.sro_line "
		                           "Left join fs_unit_cons c2 (nolock) "
		                           "on c.ser_num = c2.ser_num and c.eff_date < c2.eff_date "
		                           "Where c2.eff_date IS NULL AND "
		                           f"l.ser_num = '{self.serial_number_prefix+self.serial_number}' "
		                           "Order by s.open_date DESC")

	def get_serial_build(self) -> NamedTuple:
		return self._slsql.execute("Select top 1 * from "
		                           "(Select ser_num, item from serial "
		                           f"(nolock) where ser_num = '{self.serial_number_prefix+self.serial_number}' "
		                           "Union All "
		                           "Select ser_num, item from fs_unit "
		                           f"(nolock) where ser_num = '{self.serial_number_prefix+self.serial_number}') t")

	@property
	def serial_number_prefix(self) -> str:
		try:
			if self._serial_number_prefix is None:
				value = self._msssql.execute(
					f"SELECT p.[Prefix] FROM Prefixes p INNER JOIN Prefixes r ON r.[Product]=p.[Product] WHERE r.[Prefix] = '{self.serial_number[:2]}' AND r.[Type] = 'N' AND p.[Type] = 'P'")[
					0]
			else:
				value = self._serial_number_prefix
		except Exception as ex:
			raise ex
		except (ValueError, KeyError, IndexError):
			value = None
		finally:
			self._serial_number_prefix = value
			return self._serial_number_prefix

	@serial_number_prefix.setter
	def serial_number_prefix(self, value: str):
		self._serial_number_prefix = value

	@property
	def parts(self) -> List[Part]:
		return self._parts

	@parts.setter
	def parts(self, value):
		if value:
			value = value.strip()
			value = value.split(',')
			if value != ['']:
				if '206' in self.whole_build:
					self._parts = list({Part(self._msssql, x, spec_build='206') for x in value})
				elif '200' in self.whole_build:
					self._parts = list({Part(self._msssql, x, spec_build='200') for x in value})
				else:
					self._parts = list({Part(self._msssql, x) for x in value})
		else:
			self._parts = None

	@property
	def datetime(self) -> datetime.datetime:
		return self._datetime

	@datetime.setter
	def datetime(self, value: str):
		if type(value) is str:
			self._datetime = datetime.datetime.strptime(value, "%m/%d/%Y %I:%M:%S %p")
		else:
			self._datetime = value

	@property
	def operator_initials(self):
		if self._operator_initials is None:
			first, last = self._msssql.execute(
				f"SELECT [FirstName],[LastName] FROM Users WHERE [Username] = '{self.operator}'")
			self._operator_initials = first.strip()[0].upper() + last.strip()[0].upper()
		return self._operator_initials

	@operator_initials.setter
	def operator_initials(self, value):
		self._operator_initials = value

	@property
	def product(self):
		if self._product is None:
			data = self._msssql.execute(
				f"SELECT [Product] FROM Prefixes WHERE [Prefix] = '{self.serial_number_prefix}'")
			if not data:
				raise ValueError
			self._product = data[0]
		return self._product

	@product.setter
	def product(self, value):
		self._product = value

class Application(psutil.Process):
	# TODO: Make Simpleton?
	# TODO: Handle login pop-ups, including occasional required password change
	def __init__(self, pid):
		psutil.Process.__init__(self, pid=pid)
		self.nice(psutil.HIGH_PRIORITY_CLASS)
		self.win32 = pwn.Application(backend='win32').connect(process=self.pid)
		self.uia = pwn.Application(backend='uia').connect(process=self.pid)
		self._logged_in = False
		self._user = None

	@classmethod
	def start(cls, fp: Union[str, pathlib.Path]):
		return cls(psutil.Popen(str(fp)).pid)

	@classmethod
	def connect(cls, fp: Union[str, pathlib.Path], exclude: Union[int, Iterable[int]] = None):
		return cls(process_pid(fp, exclude))

	def log_in(self, usr: str = username, pwd: str = password) -> bool:
		if not self.logged_in and self.win32.SignIn.exists(10, 0.09):
			log.info("SyteLine not logged in, starting login procedure")
			self.win32.SignIn.UserLoginEdit.set_text(usr)
			self.win32.SignIn.PasswordEdit.set_text(pwd)
			self.win32.SignIn.set_focus()
			self.win32.SignIn.OKButton.click()
			if not self.win32.SignIn.exists(10, 0.09):
				self.win32.window(title_re=SYTELINE_WINDOW_TITLE).wait('ready', 2, 0.09)
				self._logged_in = True
				self._user = usr
				log.info(f"Successfully logged in as '{self._user}'")
				sleep(4)
				return True
			else:
				log.warning(f"Login attempt as '{usr}' unsuccessful")
		return False

	def log_out(self) -> bool:
		if self.logged_in and not self.win32.SignIn.exists(10, 0.09):
			log.info("SyteLine logged in, starting logout procedure")
			sl_uia = self.uia.window(title_re=SYTELINE_WINDOW_TITLE)
			so = [item for item in sl_uia.MenuBar.items() if item.texts()[0].lower().strip() == 'sign out'][0]
			sl_uia.set_focus()
			r_i = so.rectangle()
			c_coords = center(x1=r_i.left, y1=r_i.top, x2=r_i.right, y2=r_i.bottom)
			pag.click(*c_coords)
			if self.win32.SignIn.exists(10, 0.09):
				self.win32.SignIn.wait('ready', 2, 0.09)
				self._logged_in = False
				self._user = None
				log.info(f"Successfully logged out")
				sleep(4)
				return True
			else:
				log.warning(f"Logout attempt unsuccessful")
		return False

	def quick_log_in(self, usr: str = username, pwd: str = password) -> bool:
		if not self.logged_in and self.win32.SignIn.exists(1, 0.09):
			log.info("SyteLine not logged in, starting login procedure")
			self.win32.SignIn.UserLoginEdit.set_text(usr)
			self.win32.SignIn.PasswordEdit.set_text(pwd)
			self.win32.SignIn.set_focus()
			self.win32.SignIn.OKButton.click()
			for i in range(8):
				top_window = self.win32.top_window()
				top_window.send_keystrokes('{ENTER}')
			sleep(0.5)
			log.debug(self.win32.top_window().texts()[0])
			if __debug__:
				print(self.win32.top_window().texts()[0])
			if (not self.win32.SignIn.exists(1,  0.09)) or ('(EM)' in self.win32.top_window().texts()[0]):
				self._logged_in = True
				self._user = usr
				log.info(f"Successfully logged in as '{self._user}'")
				return True
			else:
				log.warning(f"Login attempt as '{usr}' unsuccessful")
		return False

	def quick_log_out(self) -> bool:
		if not self.win32.SignIn.exists(1, 0.09):
			log.info("SyteLine logged in, starting logout procedure")
			sl_uia = self.uia.window(title_re=SYTELINE_WINDOW_TITLE)
			so = [item for item in sl_uia.MenuBar.items() if item.texts()[0].lower().strip() == 'sign out'][0]
			sl_uia.set_focus()
			r_i = so.rectangle()
			c_coords = center(x1=r_i.left, y1=r_i.top, x2=r_i.right, y2=r_i.bottom)
			pag.click(*c_coords)
			sleep(0.5)
			log.debug(self.win32.top_window().texts()[0])
			if 'Sign In' in self.win32.top_window().texts()[0]:
				self._logged_in = False
				log.info(f"Successfully logged out")
				return True
			else:
				log.warning(f"Logout attempt unsuccessful")
		return False

	def move_and_resize(self, left: int, top: int, right: int, bottom: int):
		coord = {'left': left, 'top': top, 'right': right, 'bottom': bottom}
		win32gui.MoveWindow(self.hwnd, int(coord['left']) - 7, coord['top'], coord['right'] - coord['left'],
		                    coord['bottom'] - coord['top'], True)

	def open_form(self, *names):
		open_forms = self.forms.keys()
		log.debug(f"Opening form(s): {', '.join(names)}")
		for name in names:
			if name in open_forms:
				continue
			sl_win = self.win32.window(title_re=SYTELINE_WINDOW_TITLE)
			sl_win.send_keystrokes('^o')
			self.win32.SelectForm.AllContainingEdit.set_text(name)
			self.win32.SelectForm.set_focus()
			self.win32.SelectForm.FilterButton.click()
			common_controls.ListViewWrapper(self.win32.SelectForm.ListView).item(name).click()
			self.win32.SelectForm.set_focus()
			self.win32.SelectForm.OKButton.click()
			log.debug(f"Form '{name}' opened")
			sleep(4)

	def quick_open_form(self, *names):
		for name in names:
			sl_win = self.win32.window(title_re=SYTELINE_WINDOW_TITLE)
			sl_win.send_keystrokes('^o')
			self.win32.SelectForm.AllContainingEdit.set_text(name)
			self.win32.SelectForm.set_focus()
			self.win32.SelectForm.FilterButton.click()
			common_controls.ListViewWrapper(self.win32.SelectForm.ListView).item(name).click()
			self.win32.SelectForm.set_focus()
			self.win32.SelectForm.OKButton.click()
			sleep(2)

	def find_value_in_collection(self, collection: str, property_: str, value, case_sensitive=False):
		sl_win = self.win32.window(title_re=SYTELINE_WINDOW_TITLE)
		sl_win.send_keystrokes('%e')
		sleep(0.02)
		sl_win.send_keystrokes('v')
		find_window = self.win32['Find']
		find_window.InCollectionComboBox.select(collection)
		find_window.InPropertyComboBox.select(property_)
		find_window.FindEdit.set_text(value)
		if case_sensitive:
			find_window.CaseSensitiveButton.check()
		find_window.set_focus()
		find_window.OKButton.click()

	def change_form(self, name: str):
		forms = self.forms
		if name in forms:
			if name == self.get_focused_form():
				pass
			else:
				forms[name].select()
		else:
			raise ValueError(f"Form '{name}' not open")

	@property
	def forms(self) -> Dict[str, uia_controls.MenuItemWrapper]:
		# TODO: Possible form object including 'is_checked' property
		sl_uia = self.uia.window(title_re=SYTELINE_WINDOW_TITLE)
		retval = {REGEX_WINDOW_MENU_FORM_NAME.search(item.texts()[0]).group(1): item for item in
		          sl_uia.WindowMenu.items() if
		          (item.texts()[0].lower() != 'cascade') and (item.texts()[0].lower() != 'tile') and (
			          item.texts()[0].lower() != 'close all')}
		log.debug(f"Forms open: {', '.join(retval.keys())}")
		return retval

	@property
	def logged_in(self):
		if self.win32.SignIn.exists(10, 0.09):
			self._logged_in = False
		else:
			self._logged_in = True
		return self._logged_in

	@property
	def hwnd(self):
		return self.win32.top_window().handle

	@property
	def window_rect(self):
		rect = win32gui.GetWindowRect(self.hwnd)
		return int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3])

	@property
	def size(self):
		x, y = self.window_rect[:2]
		w = abs(self.window_rect[2] - x)
		h = abs(self.window_rect[3] - y)
		return w, h

	@size.setter
	def size(self, value):
		w, h = value
		x, y = self.location
		win32gui.MoveWindow(self.hwnd, x, y, w, h, True)

	@property
	def location(self):
		return self.window_rect[:2]

	@location.setter
	def location(self, value):
		x, y = value
		w, h = self.size
		win32gui.MoveWindow(self.hwnd, x, y, w, h, True)

	def get_focused_form(self) -> str:
		"""0x100000  1048576  0b100000000000000000000  focusable
		   0x100004  1048580  0b100000000000000000100  focusable, focused
		   0x100084  1048708  0b100000000000010000100  focusable, focused, hot-tracked
		   0x100094  1048724  0b100000000000010010100  focusable, focused, hot-tracked, checked
		   0x100010  1048592  0b100000000000000010000  focusable, checked

		   0x000004  0000004  0b000000000000000000100  focused
		   0x000010  0000016  0b000000000000000010000  checked
		   0x000040  0000064  0b000000000000001000000  read-only
		   0x000080  0000128  0b000000000000010000000  hot-tracked
		   0x100000  1048576  0b100000000000000000000  focusable"""
		for item in self.forms.items():
			name, form = item
			state = form.legacy_properties()['State']
			bin_state = bin(state)
			log.debug(f"Form State: {state}")
			if int(bin_state[-5], base=2):  # If the fifth bit == 1
				return name

	def verify_form(self, name: str):
		if name not in self.forms.keys():
			self.open_form(name)
		if name != self.get_focused_form():
			self.change_form(name)

	def get_popup(self, timeout=2) -> Dialog:
		dlg = self.win32.window(class_name="#32770")
		if dlg.exists(timeout, 0.09):
			title = ''.join(text.strip() for text in dlg.texts())
			text = ''.join(text.replace('\r\n\r\n', '\r\n').strip() for cls in dlg.children() if
			               cls.friendly_class_name() == 'Static' for text in cls.texts())
			buttons = {text.strip(punctuation + ' '): cls for cls in dlg.children() if
			           cls.friendly_class_name() == 'Button' for text in cls.texts()}
			return Dialog(dlg, title, text, buttons)
		else:
			return None

	def get_user(self):
		sl_win = self.win32.window(title_re=SYTELINE_WINDOW_TITLE)
		sl_uia = self.uia.window(title_re=SYTELINE_WINDOW_TITLE)
		self.quick_open_form("User Information")
		self._user = sl_win.UserIDEdit.texts()[0]
		sl_uia.CancelCloseButton.click()

class Puppet(threading.Thread):
	def target(self): ...

	def __init__(self, app: Application, name):
		raise NotImplementedError()
		self.q_in = queue.Queue()
		self.q_out = queue.Queue()
		self.app = app
		self.status = 'Idle'
		self.units = set()
		super().__init__(target=self.target, daemon=True, name=name)
		self.start()
		self._stop_event = threading.Event()

	def set_input(self, func: callable, *args, **kwargs): ...

	def run_process(self, proc, unit_sn, *args, **kwargs): ...

	def get_output(self) -> Any: ...

	def stop(self): ...

	def stopped(self) -> bool: ...


class PuppetMaster:
	_children = set()
	pids = defaultdict(list)

	def __init__(self, fp, app_count: int = 0, skip_opt: bool=False):
		if app_count > 0:
			for i in range(app_count):
				app = self.grab(fp)
				if not app:
					break
			app_count -= len(self.children())
			for i in range(app_count):
				app = self.start(fp)
				if not app:
					break
			if app_count > 0:
				return None
			if not skip_opt:
				self.optimize_screen_space()

	def start(self, fp: Union[str, pathlib.Path], name: str = None) -> Puppet:
		try:
			if name is None:
				base_name = pathlib.Path(str(fp)).stem[:4].lower()
				name = base_name + '1'
				count = 2
				while name in self._children:
					name = base_name + str(count)
					count += 1
			app = Application.start(str(fp))
			app.win32.top_window().exists()
		except Exception:
			return None
		else:
			self.__setattr__(name, self.Puppet(app, name))
			self.pids[fp].append(self.__getattribute__(name).app.pid)
			self._children.add(name)
			return self.__getattribute__(name)

	def grab(self, fp: Union[str, pathlib.Path]) -> Puppet:
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

	def optimize_screen_space(self, win_size: Tuple[int, int] = (1024, 750), screen_pref: str=None):
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

	def children(self) -> List[Puppet]:
		return [self.__getattribute__(ch) for ch in self._children]

	def apply_all(self, func: Callable, *args, **kwargs):
		with ThreadPoolExecutor(max_workers=len(self.children())) as e:
			for ch in self.children():
				e.submit(func, ch, *args, **kwargs)
				sleep(1)

	def get_puppet(self, ppt: Union[str, int, Puppet]) -> Puppet:
		print(ppt)
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
				print(ch, ch.status)
				if ch.status == 'Idle':
					ppt = ch
					break
			else:
				raise ValueError()
		return ppt

	def wait_for_puppets(self, puppets, max_time=10):
		puppets = [self.get_puppet(ppt) for ppt in puppets]
		res = []
		start_time = datetime.datetime.now()
		while len(res) < len(puppets):
			if __debug__:
				pass
				# print(res, (datetime.datetime.now() - start_time).total_seconds())
			sleep(0.001)
			for ppt in puppets:
				res2 = ppt.get_output()
				if res2:
					res.append(res2)
			if (datetime.datetime.now() - start_time).total_seconds() > max_time:
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
					observer_affect()
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
			self.q_in.put_nowait((func, tuple(arg for arg in args), {k: v for k, v in kwargs.items()}))

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

	def __exit__(self, type, value, traceback):
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
	def __init__(self, n: int, fp=application_filepath, skip_opt: bool=True, forms=[]):
		print(n, forms)
		user_list = [username, 'BISync01', 'BISync02', 'BISync03']
		pwd_list = [password, 'N0Trans@cti0ns', 'N0Re@s0ns', 'N0Gue$$!ng']
		super().__init__(fp, n, skip_opt)
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
				observer_affect()

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

	def run_process(self, process, ppt: Union[str, int, Puppet]=None) -> bool:
		"""Run process, return whether it was successful or not."""
		ppt = self.get_puppet(ppt)
		units = process.get_units(mssql, sl_sql, exclude=[sn for ch in self.children() for sn in ch.units])
		print(units)
		if units:
			ppt.run_process(process, {unit.serial_number for unit in units}, units)
			print(ppt.units)
			return ppt
		return False

	class Puppet(PuppetMaster.Puppet):
		def target(self):
			while True:
				self.status = 'Idle'
				observer_affect()
				try:
					command, args, kwargs = self.q_in.get_nowait()
				except queue.Empty:
					observer_affect()
				else:
					self.status = 'Busy'
					self.q_out.put_nowait(command(self, *args, **kwargs))
					self.status = 'Idle'
					self.units.clear()
				self.status = 'Idle'

		def __init__(self, app: Application, name):
			self.units = set()
			super().__init__(app, name)

		def run_process(self, proc, unit_sn, *args, **kwargs):
			self.q_in.put_nowait((proc.run, tuple(arg for arg in args), {k: v for k, v in kwargs.items()}))
			self.units = {str(sn) for sn in unit_sn}

class TestTimer:
	def __init__(self):
		self._start_time = None

	def start(self):
		self._start_time = datetime.datetime.now()

	def lap(self):
		if self._start_time:
			retval = datetime.datetime.now() - self._start_time
			return retval
		else:
			return datetime.timedelta(0)

	def reset(self):
		self._start_time = None

	def stop(self):
		retval = self.lap()
		self.reset()
		return retval

# TODO: Maybe Cell class?
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

# TODO: Maybe Row class?
class Row(UserDict):
	def __init__(self, columns: Union[str, Iterable[str]]):
		if type(columns) is str:
			columns = [columns]
		super().__init__((col, None) for col in columns)

# TODO: Maybe Column class?
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
	def from_name(cls, app: Application, name: str, columns: Union[str, Iterable[str]], row_limit: int):
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

# class Singleton(type):
# 	"""
# 	Define an Instance operation that lets clients access its unique
# 	instance.
# 	"""
#
# 	def __init__(cls, name, bases, attrs, **kwargs):
# 		super().__init__(name, bases, attrs)
# 		cls._instance = None
#
# 	def __call__(cls, *args, **kwargs):
# 		if cls._instance is None:
# 			cls._instance = super().__call__(*args, **kwargs)
# 		return cls._instance
#
# class MyClass():
# 	"""
# 	Example class.
# 	"""
#
# 	pass
""""""
"""reason_gen	description
1000	No Reason Given
10000	Unable to Duplicate Issue.
1001	Returned for Testing/Updates
1002	Defective
1003	Returned for transmitter problem
1004	Returned for FMD problem
1005	Will not call in/out
1006	Change Phone Number
1007	Excessive Leaves/Enters (TIR/TOR)
1008	No Enters/Leaves
1009	No power up, no lights
1010	Missed Callback/late (MCL)
1011	False leaves/enters (TIR/TOR)
1012	Host Busy Messages (HBS)
1013	No location verify
1014	Speaker failure
1016	Low Batt Msg (LBR, CBL, TEB)
1017	Power Connection Broken
1018	False Tampers (TCS/TOS)
1019	Will Not Tamper
1020	Will Not Activate, Dead
1021	Will Not Find Transmitter (TNF)
1022	Default Serial Number
1023	Rattles
1024	Water Damage
1025	Client/Case Damage
1026	Calibration
1027	Communication Problems
1028	Keyswitch Broken
1029	Will Not Transmit
1030	Smoking/Burnt Transformer
1031	Solenoid problem (VCE)
1032	Will Not Enroll
1033	Phone Jack Broken
1034	Voice Module Failure (VMF)
1035	Room Noise Failure
1036	Storm/Lightning Damage
1037	Unit Burned
1039	Reset problems
1040	Will not do Alcohol Test
1041	Time Stamping Errors
1042	Enrollment Error/Problems
1043	Cheek Sensor Problems
1045	Duplicate Serial Number
1046	Case Tamper
1047	HG  swap
1048	Return of Demo Equipment
1049	End of Lease
1050	RTS
1051	Suspect NTC;Y1
1052	Excess Inventory
1053	Failure Analysis  *****
1054	Switching to GWOW
1055	Lost Contract
1056	"out of box" failure
1057	No GPS signal
1058	Returned for Tin Whiskers
1059	Explain - for CBS purposes  *****
1060	Not responding to officer key
1061	Stuck in cell phone mode
1062	Missing Charger XFMR
1063	Missing Charge Cord
1064	Missing Black Zipper Case: Soberlink
1068	Stripped Screws
1069	No-Motion Failure
1100	TDA 375
1101	Malfunction of push button
1102	Malfunction of transformer
1103	No lights blinking
1104	Stuck ADM
1105	Broken ADM
1106	Tamper won't clear
1107	Absconded
1108	Battery error
1109	Reduced range
1110	On enter fail
1111	No cellular signal
1112	Beacon failed
1113	Return to BI for maintenance
1114	Excessive Tamper Alerts
1115	Will Not Charge
1116	Will not hold a charge"""

# - - - - - - - - - - - - - - - - - - - FUNCTIONS - - - - - - - - - - - - - - - - - - - -
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

@legacy
def _adapt_cell(x):
	if x == '(null)':
		return None
	elif x == 'False':
		return False
	elif x == 'True':
		return True
	elif '.' in x:
		if x.rsplit('.', 1)[0].isnumeric():
			return int(x.rsplit('.', 1)[0].isnumeric())
	else:
		return x

@legacy
def access_grid(grid: uia_controls.ListViewWrapper, columns: Union[str, Iterable[str]],
                condition: Optional[Tuple[str, Any]] = None, requirement: str = None) -> List[NamedTuple]:
	if type(columns) is str:
		columns = [columns]
	# TODO: regex datetime
	# TODO: better condition handling (exec string?)
	DataRow = namedtuple('DataRow', field_names=[col.replace(' ', '_') for col in columns])
	if requirement is not None:
		if condition is None:
			retval = [DataRow(**{col.replace(' ', '_'): _adapt_cell(uia_controls.ListViewWrapper(row.element_info).item(
				grid.children()[grid.children_texts().index('Top Row')].children_texts().index(
					col)).legacy_properties()['Value'].strip()) for col in columns}) for row in
			          grid.children()[grid.children_texts().index('Row 0'):] if _adapt_cell(
					uia_controls.ListViewWrapper(row.element_info).item(
						grid.children()[grid.children_texts().index('Top Row')].children_texts().index(
							requirement)).legacy_properties()['Value'].strip()) != None]
		else:
			retval = [DataRow(**{col.replace(' ', '_'): _adapt_cell(uia_controls.ListViewWrapper(row.element_info).item(
				grid.children()[grid.children_texts().index('Top Row')].children_texts().index(
					col)).legacy_properties()['Value'].strip()) for col in columns}) for row in
			          grid.children()[grid.children_texts().index('Row 0'):] if _adapt_cell(
					uia_controls.ListViewWrapper(row.element_info).item(
						grid.children()[grid.children_texts().index('Top Row')].children_texts().index(
							condition[0])).legacy_properties()['Value'].strip()) == condition[1] and _adapt_cell(
					uia_controls.ListViewWrapper(row.element_info).item(
						grid.children()[grid.children_texts().index('Top Row')].children_texts().index(
							requirement)).legacy_properties()['Value'].strip()) != None]
	else:
		if condition is None:
			retval = [DataRow(**{col.replace(' ', '_'): _adapt_cell(uia_controls.ListViewWrapper(row.element_info).item(
				grid.children()[grid.children_texts().index('Top Row')].children_texts().index(
					col)).legacy_properties()['Value'].strip()) for col in columns}) for row in
			          grid.children()[grid.children_texts().index('Row 0'):]]
		else:
			retval = [DataRow(**{col.replace(' ', '_'): _adapt_cell(uia_controls.ListViewWrapper(row.element_info).item(
				grid.children()[grid.children_texts().index('Top Row')].children_texts().index(
					col)).legacy_properties()['Value'].strip()) for col in columns}) for row in
			          grid.children()[grid.children_texts().index('Row 0'):] if _adapt_cell(
					uia_controls.ListViewWrapper(row.element_info).item(
						grid.children()[grid.children_texts().index('Top Row')].children_texts().index(
							condition[0])).legacy_properties()['Value'].strip()) == condition[1]]
	log.debug(f"Grid Accessed: {retval}")
	return retval

def _check_units(sql, status: str, table: str = 'PyComm', group_serial: bool = False) -> int:
	"""Count the number of entries in SQL connection and table that match status. Return integer."""
	distinct = ''
	table = str(table)
	if group_serial:
		distinct = 'DISTINCT '
	return \
		sql.execute(f"SELECT COUNT({distinct}[Serial Number]) as [SN_Count] FROM {table} WHERE [Status] = '{status}'")[
			0]

def check_serial_number(sql, serial_number: str, status: str, table: str = 'PyComm') -> str:
	"""Verify that serial number hasn't been skipped. Return string."""
	rows = sql.execute(f"SELECT DISTINCT [Status] FROM {table} WHERE [Serial Number] = '{serial_number}'",
	                   fetchall=True)
	for row in rows:
		if status not in row.Status:
			continue
		elif (row.Status != status) and (status in row.Status):
			break
	else:
		return status
	return row.Status

# Not one Item Price exists for Item that has
# @overload
def center(x1: int, y1: int, x2: int, y2: int) -> Tuple[int, int]:
	"""Return the center of given coordinates.
	:rtype: tuple
	"""
	assert 0 < x1 < x2
	assert 0 < y1 < y2
	x2 -= x1
	y2 -= y1
	return x1 + (x2 // 2), y1 + (y2 // 2)

# noinspection SpellCheckingInspection
def sigfig(template, x):
	x_str, y_str = map(str, [template, x])
	x_len = len(x_str.split('.', 1)[1].strip())
	y_sub1, y_sub2 = y_str.split('.', 1)
	y_sub2 = y_sub2.ljust(x_len, '0')
	y_new = eval(f"{y_sub1}.{y_sub2[:x_len]}")
	if len(y_sub2) > x_len and eval(y_sub2[x_len]) >= 5:
		val = 10 ** x_len
		y_new = ((y_new * val) + 1) / val
	return y_new

def get_screen_exact():
	sleep(0.05)
	pag.press('printscreen')
	sleep(0.1)
	return ImageGrab.grabclipboard()

def get_screen_size() -> List[Tuple[int, int]]:
	size1 = get_screen_exact().size
	size2 = ImageGrab.grab().size
	return [size2] * (size1[0] // size2[0])

def count_screens() -> int:
	return len(get_screen_size())

def total_screen_space() -> Tuple[int, int]:
	w = 0
	for scrn in get_screen_size():
		w += scrn[0]
		h = scrn[1]
	return (w, h)

def enumerate_screens() -> List[Tuple[int, int, int, int]]:
	total = total_screen_space()
	step = total[0] // count_screens()
	return [(x, 0, x + step, total[1]) for x in range(0, total[0], step)]

def parse_numeric_ranges(x: Union[str, List[int]], sep: str = ',') -> List[Tuple[int, int]]:
	"""Inclusive (min, max) range parser"""
	nums = sorted([int(y) for y in x.split(sep)]) if type(x) is str else sorted(x)
	retval = []
	temp_set = set([])
	for x in nums:
		if not temp_set:
			temp_set.add(x)
		elif max(temp_set) + 1 == x:
			temp_set.add(x)
		else:
			if len(temp_set) > 1:
				retval.append((min(temp_set), max(temp_set)))
			else:
				retval.append((max(temp_set), max(temp_set)))
			temp_set = {x}
	else:
		if len(temp_set) > 1:
			retval.append((min(temp_set), max(temp_set)))
		elif len(temp_set) == 1:
			retval.append((max(temp_set), max(temp_set)))
	return retval

# def someHotSpotCallable(func: Callable):
# 	# Deterministic profiler
# 	def _my_decorator(*args, **kwargs):
# 		prof = pprofile.Profile()
# 		with prof():
# 			func(*args, **kwargs)
# 		prof.print_stats()
# 	return _my_decorator
#
# def someOtherHotSpotCallable(func: Callable):
# 	# Statistic profiler
# 	def _my_decorator(*args, **kwargs):
# 		prof = pprofile.StatisticalProfile()
# 		with prof(period=0.001, single=True):
# 			func(*args, **kwargs)
# 		prof.print_stats()
# 	return _my_decorator
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

timer = TestTimer()

__all__ = ['Unit', 'Application', 'center', 'access_grid', 'parse_numeric_ranges', 'TestTimer', 'timer', 'process_pid',
           'is_running', 'get_screen_size', 'count_screens', 'total_screen_space', 'enumerate_screens', 'DataGrid',
           '_check_units', 'check_serial_number']
