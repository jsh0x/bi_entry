#!/usr/bin/env python
import datetime
import decimal
import logging
import pathlib
import queue
import threading
from collections import Counter, UserDict, UserList, UserString, defaultdict, namedtuple
from concurrent.futures import ThreadPoolExecutor
from functools import singledispatch
from string import punctuation
from time import sleep
from typing import Any, Callable, Dict, Iterable, List, NamedTuple, Optional, Tuple, Union

import numpy as np
import pprofile
import psutil
import pyautogui as pag
import pywinauto as pwn
import win32gui
from PIL import ImageGrab
import pywinauto.timings
from pywinauto.win32structures import RECT, POINT
from pywinauto.backend import registry
from pywinauto.base_wrapper import BaseWrapper
from pywinauto import WindowSpecification
from pywinauto.controls import common_controls, uia_controls, win32_controls

from config import *
from constants import REGEX_WINDOW_MENU_FORM_NAME, SYTELINE_WINDOW_TITLE, carrier_dict, cellular_builds, part_number_regex, unit_type_dict, row_number_regex
from exceptions import *
from utils.tools import prepare_string, just_over_half

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


# TODO: Refine Coordinates and Rectangle classes with properties: top, left, right, bottom, width, and height.
# THINK: Maybe __contains__?
class Coordinates(NamedTuple):
	x: int
	y: int


class Dimensions(NamedTuple):
	width: int
	height: int


class Unit:  # TODO: Special methods __repr__ and __str__
	#  THINK: Maybe Singleton/Serial Number-based restriction

	class SerialNumber(UserString):  # FIXME: UNIT TEST THIS
		def __init__(self, prefix: str, number: str):
			self._prefix = prefix
			self._number = number
			data = mssql.execute("""SELECT Product FROM Prefixes WHERE Prefix = %s AND Type = 'P'""", self._prefix)
			if not data:
				raise ValueError()  # TODO: Specify error
			self.product = data[0].Product
			super().__init__(str(self._prefix) + str(self._number))

		@property
		def prefix(self):
			return self._prefix

		@prefix.setter
		def prefix(self, value):
			self._prefix = value
			data = mssql.execute("""SELECT Product FROM Prefixes WHERE Prefix = %s AND Type = 'P'""", self._prefix)
			if not data:
				raise ValueError()  # TODO: Specify error
			self.product = data[0].Product
			self.data = str(self._prefix) + str(self._number)

		@property
		def number(self):
			return self._number

		@number.setter
		def number(self, value):
			self._number = value
			self.data = str(self._prefix) + str(self._number)

		@classmethod
		def from_base_number(cls, number: str):
			number = prepare_string(number, remove_all_whitespace=True)
			results = mssql.execute("""SELECT p.Prefix FROM Prefixes p INNER JOIN Prefixes r ON r.Product=p.Product WHERE r.Prefix = %s AND r.Type = 'N' AND p.Type = 'P'""", number[:2])
			if not results:
				raise InvalidSerialNumberError(number)
			for res in results:
				if slsql.execute("""SELECT ser_num FROM serial ( NOLOCK ) WHERE ser_num = %s""", (res.Prefix + number)):
					return cls(res.Prefix, number)
			else:
				raise ValueError()  # TODO: Specify error

	class Build(UserString):  # FIXME: UNIT TEST THIS
		def __init__(self, prefix: str, core: str, suffix: str = None, *, type_: str, carrier_ref: Union[str, int] = None, carrier: str = None):
			self.prefix = str(prefix).upper()
			self.core = str(core).upper()
			self.suffix = str(suffix).upper() if suffix else suffix
			self.type = str(type_).title() if not str(type_).isupper() else str(type_).upper()
			self.carrier = carrier
			self.carrier_ref = carrier_ref
			self._carrier_type = type(carrier_ref)
			self._cellular = core in cellular_builds
			if self.suffix:
				retval = self.prefix + '-' + self.core_with_carrier + '-' + self.suffix
			else:
				retval = self.prefix + '-' + self.core_with_carrier
			super().__init__(retval)

		@property
		def data(self):
			if self.suffix:
				return self.prefix + '-' + self.core_with_carrier + '-' + self.suffix
			else:
				return self.prefix + '-' + self.core_with_carrier

		@data.setter
		def data(self, value):
			pass

		@property
		def cellular(self) -> bool:
			return self._cellular

		@property
		def carrier_type(self) -> type:
			return self._carrier_type

		@property
		def core_with_carrier(self) -> str:
			if self.carrier_type is int:
				return str(self.carrier_ref) + self.core
			elif self.carrier_type is str:
				return self.core + self.carrier_ref
			elif self.carrier_type is type(None):
				return self.core
			else:
				raise TypeError()  # TODO: Specify error

		@classmethod
		def from_string(cls, build: str, suffix_default: str = 'RTS'):  # TODO: Handle len(build.split('-')) == 1: 600, 800, etc and figure out prefix from related product
			build = prepare_string(build, remove_all_whitespace=True)
			print(build)
			prefix, core = build.split('-')[:2]
			if core.isnumeric():
				core_base = core[-3:]
				carrier = int(core[0]) if core[0] else None
			else:
				core_base = core[:3]
				carrier = core[-1]
			suffix = [k for k, v in unit_type_dict.items() if build.endswith(k)]
			if suffix:
				return cls(prefix, core_base, suffix[0], type_=unit_type_dict[suffix[0]], carrier_ref=carrier, carrier=carrier_dict[carrier])
			else:
				return cls(prefix, core_base, type_=suffix_default, carrier_ref=carrier, carrier=carrier_dict[carrier])

		@classmethod
		def from_SerialNumber(cls, serial_number: 'SerialNumber', suffix: str):
			build = slsql.execute("""SELECT item FROM serial ( NOLOCK ) WHERE ser_num = %s""", serial_number)
			return cls.from_string(build[0].item, suffix_default=suffix)

		def __repr__(self):
			if self.carrier:
				return f"<Build object; {self.core}, ({self.carrier[0]}), {self.type}>"
			else:
				return f"<Build object; {self.core}, {self.type}>"

	class Part:  # THINK: Maybe expand upon iterable functionality, taking into account posted/un-posted/un-transacted parts
		def __init__(self, ID: int, quantity: int):
			data = mssql.execute("""SELECT PartNum, Qty, DispName, Location, PartName FROM Parts WHERE ID = %d""", ID)
			if not data:
				raise ValueError()  # TODO: Specify error
			self.ID = ID
			self.part_number = data[0].PartNum
			self._Qty = data[0].Qty
			self._modifier = quantity
			self.quantity = self._modifier * self._Qty
			self.display_name = data[0].DispName
			self.part_name = data[0].PartName
			self.location = data[0].Location

		@classmethod
		def from_part_number(cls, part_number: str, build: 'Build', quantity: int = 1):
			part = None
			if part_number_regex.fullmatch(part_number):
				part_id = mssql.execute("""SELECT ID FROM Parts WHERE PartNum = %s""", part_number)
				if part_id:
					part = int(part_id[0].ID)
				part_id = mssql.execute("""SELECT ID FROM Parts WHERE PartNum = %s AND Build = 'All'""", part_number)
				if part_id:
					part = int(part_id[0].ID)
				part_id = mssql.execute("""SELECT ID FROM Parts WHERE PartNum = %s AND Build = %s""", (part_number, build.core))
				if part_id:
					part = int(part_id[0].ID)
				if part is None:
					raise InvalidPartNumberError(str(part_number))
			else:
				part = int(part_number)
			return {cls(part, quantity)}

		@classmethod
		def from_string(cls, csv: str, build: 'Build'):  # From Comma-Separated Values
			csv = prepare_string(csv, remove_all_whitespace=True)
			if csv is None:
				return set()
			parts = {}
			part_quantities = defaultdict(int)
			for part in csv.split(','):
				if part_number_regex.fullmatch(part):
					part_id = mssql.execute("SELECT ID FROM Parts WHERE PartNum = %s", part)
					if part_id:
						parts[part] = int(part_id[0].ID)
					part_id = mssql.execute("SELECT ID FROM Parts WHERE PartNum = %s AND Build = 'All'", part)
					if part_id:
						parts[part] = int(part_id[0].ID)
					part_id = mssql.execute("SELECT ID FROM Parts WHERE PartNum = %s AND Build = %s", (part, build.core))
					if part_id:
						parts[part] = int(part_id[0].ID)
				else:
					parts[part] = int(part)
				part_quantities[parts[part]] += 1
			return {cls(v, part_quantities[v]) for v in parts.values()}

		def __repr__(self):
			return f"<Part object; {self.part_number}x{self.quantity}>"

		def __str__(self):
			# return f"{self.display_name}({self.part_number}) x {self.quantity}"
			return f"{self.part_number} x {self.quantity}"

	class Operator(UserString):
		def __init__(self, ID: int):
			data = mssql.execute("""SELECT Username,FirstName,LastName FROM Users WHERE USERID = %d""", ID)
			if not data:
				raise ValueError()  # TODO: Specify error
			self.ID = ID
			self.username = data[0].Username
			self.initials = data[0].FirstName.upper() + data[0].LastName.upper()
			super().__init__(self.initials)

		@classmethod
		def from_username(cls, username: str):
			data = mssql.execute("""SELECT USERID FROM Users WHERE Username = %s""", username)
			if not data:
				raise ValueError()  # TODO: Specify error
			return cls(data[0].USERID)

	class Operation(UserString):
		def __init__(self, ID: int):
			data = mssql.execute("""SELECT Process FROM Processes WHERE ID = %d""", ID)
			if not data:
				raise ValueError()  # TODO: Specify error
			self.ID = ID
			self.process = data[0].Process
			super().__init__(self.process)

		@classmethod
		def from_string(cls, process: str, product: str):
			data = mssql.execute("""SELECT ID FROM Processes WHERE Process = %s AND Product = %s""", (process, product))
			if not data:
				raise ValueError()  # TODO: Specify error
			return cls(data[0].ID)

	def __init__(self, ID: int):  # TODO: Split long __init__ into separate functions
		self.version = version
		self.ID = ID
		log.info(f"Attribute ID={self.ID}")

		data = mssql.execute("""SELECT [Serial Number],Suffix,Operation,Operator,Parts,DateTime,Notes,Status FROM PyComm WHERE Id = %d""", self.ID)
		if not data:
			raise ValueError()  # TODO: Specify error

		self.serial_number = self.SerialNumber.from_base_number(data[0].Serial_Number)
		log.info(f"Attribute serial_number='{self.serial_number}'")

		self.product = self.serial_number.product
		log.info(f"Attribute product='{self.product}'")

		self.build = self.Build.from_SerialNumber(self.serial_number, data[0].Suffix)
		log.info(f"Attribute build='{self.build}'")

		self.parts = self.Part.from_string(data[0].Parts, self.build)
		if self.parts:
			part_string = "('" + "', '".join(str(part) for part in self.parts) + "')"
		else:
			part_string = 'None'
		log.info(f"Attribute parts={part_string}")

		self.operation = self.Operation.from_string(data[0].Operation, self.product)
		log.info(f"Attribute operation='{self.operation}'")

		self.operator = self.Operator.from_username(data[0].Operator)
		log.info(f"Attribute operator='{self.operator.username}'")

		self.is_QC = 'QC' in self.operation
		log.info(f"Attribute is_QC={self.is_QC}")

		self.is_cellular = self.build.cellular
		log.info(f"Attribute is_cellular={self.is_cellular}")

		self.datetime = data[0].DateTime
		datetime_str = self.datetime.strftime('%m/%d/%Y %H:%M:%S')
		log.info(f"Attribute datetime='{datetime_str}'")

		self.notes = data[0].Notes
		log.info(f"Attribute notes='{self.notes}'")

		self.status = data[0].Status
		log.info(f"Attribute status='{self.status}'")

		self.parts_transacted = set()

		self.sro, self.sro_line = self.get_sro(self.serial_number)
		log.info(f"Attribute sro='{self.sro}'")
		log.info(f"Attribute sro_line={self.sro_line}")

		self.eff_date = self.get_eff_date(self.serial_number)
		eff_date_str = self.eff_date.strftime('%m/%d/%Y')
		log.info(f"Attribute eff_date={eff_date_str}")

		self.sro_open_status = self.get_statuses(self.serial_number)
		log.info(f"Attribute sro_open_status={self.sro_open_status}")

		self.location = self.get_location(self.serial_number)
		log.info(f"Attribute location='{self.location}'")

		self.warehouse = self.get_warehouse(self.serial_number)
		log.info(f"Attribute warehouse='{self.warehouse}'")

		self.batch_amt_default = 1

		self.sro_operations_time = 0
		self.sro_transactions_time = 0
		self.misc_issue_time = 0

		self.life_timer = Timer().start()
		self.start_time = datetime.datetime.now().time().strftime("%H:%M:%S.%f")
		self.start_date = datetime.datetime.now().date().strftime("%Y-%m-%d")
		# if build_data is None:
		# 	if self._status.lower() != 'scrap':
		# 		raise NoSROError(serial_number=self.serial_number)
		# 	loc, whse = 'Out of Inventory', None
		# 	gc, item = self.get_serial_build()
		# 	log.debug(f"Property serial_number_prefix='{self.serial_number_prefix}'")
		# 	self.update_sl_data()
		# else:
		# 	gc, item, loc, whse = build_data
		# 	if gc.upper().startswith('BE'):
		# 		self.serial_number_prefix = 'BE'
		# 	elif gc.upper().startswith('ACB'):
		# 		self.serial_number_prefix = 'ACB'
		# 	log.debug(f"Property serial_number_prefix='{self.serial_number_prefix}'")
		# 	self.update_sl_data()
		# if self.sl_data is None:
		# 	self.sro_num, self.sro_line, self.eff_date, self.SRO_Line_status, self.SRO_Operations_status = None, None, None, 'Closed', 'Closed'
		# if self._status.lower() != 'scrap' and self.SRO_Line_status == 'Closed':
		# 	if self.sro_num is None:
		# 		raise NoSROError(serial_number=str(self.serial_number))
		# 	else:
		# 		raise NoOpenSROError(serial_number=str(self.serial_number), sro=str(self.sro_num))
		self.general_reason = 1000
		self.specific_reason = 20
		self.general_resolution = 10000
		self.specific_resolution = 100

	# if 'queued' not in self._status.lower():
	# 	try:
	# 		if 'queued' not in self._status.lower() and REGEX_RESOLUTION.match(self.notes):
	# 			self.general_resolution, self.specific_resolution = [int(x) for x in
	# 			                                                     REGEX_RESOLUTION.match(self.notes).groups()]
	# 			if 'scrap' in self._status.lower():
	# 				self.specific_resolution_name = self._status.upper()
	# 			self.general_resolution_name = mssql.execute(  # FIXME: SQL command w/ parameters
	# 					f"SELECT TOP 1 [Failure] FROM FailuresRepairs WHERE [ReasonCodes] = '{self.notes}'")[0]
	# 	except TypeError as ex:
	# 		raise InvalidReasonCodeError(reason_code=str(self.notes), spec_id=str(self.id), msg=str(ex))
	# 	# TODO: For HG, allow Invalid Reason Codes, just enter in operator initials
	# if self._status.lower() != 'scrap':
	# 	self.start()
	# pass

	@classmethod
	def from_serial_number(cls, serial_number: Union[str, SerialNumber], status: str):
		ID = mssql.execute("SELECT Id FROM PyComm WHERE [Serial Number] = %s AND Status = %s", (serial_number, status))
		if ID:
			return [cls(i.Id) for i in ID]
		else:
			return None

	def get_location(self, serial_number: SerialNumber = None) -> str:
		if serial_number is None:
			serial_number = self.serial_number
		location = slsql.execute("""SELECT CASE WHEN loc IS NULL THEN 'Out of Inventory'
		ELSE loc END AS Inv_Stat FROM serial ( NOLOCK ) 
		WHERE ser_num = %s""", serial_number)
		if location:
			return location[0].Inv_Stat
		else:
			return None

	def get_warehouse(self, serial_number: SerialNumber = None) -> str:
		if serial_number is None:
			serial_number = self.serial_number
		warehouse = slsql.execute("""SELECT whse FROM serial ( NOLOCK ) WHERE ser_num = %s""", serial_number)
		if warehouse:
			return warehouse[0].whse
		else:
			return None

	def get_sro(self, serial_number: SerialNumber = None) -> Tuple[str, int]:
		if serial_number is None:
			serial_number = self.serial_number
		sro_data = slsql.execute("""SELECT TOP 1
	s.sro_num,
	t.sro_line
FROM fs_sro s
	INNER JOIN fs_sro_line t ( NOLOCK )
		ON s.sro_num = t.sro_num
	INNER JOIN fs_unit_cons c ( NOLOCK )
		ON t.ser_num = c.ser_num
	INNER JOIN fs_sro_oper o ( NOLOCK )
		ON t.sro_num = o.sro_num AND t.sro_line = o.sro_line
	LEFT JOIN fs_unit_cons c2 ( NOLOCK )
		ON c.ser_num = c2.ser_num AND c.eff_date < c2.eff_date
WHERE c2.eff_date IS NULL AND
      t.ser_num = %s
ORDER BY s.open_date DESC""", serial_number)
		if sro_data:
			return sro_data[0][0], sro_data[0][1]
		else:
			return None

	def get_statuses(self, serial_number: SerialNumber = None) -> Dict[str, bool]:
		if serial_number is None:
			serial_number = self.serial_number
		statuses = slsql.execute("""SELECT TOP 1
	CASE WHEN t.stat = 'C'
		THEN 'Closed'
	ELSE 'Open' END AS [SRO Line Status],
	CASE WHEN o.stat = 'C'
		THEN 'Closed'
	ELSE 'Open' END AS [SRO Operation Status]
FROM fs_sro s
	INNER JOIN fs_sro_line t ( NOLOCK )
		ON s.sro_num = t.sro_num
	INNER JOIN fs_unit_cons c ( NOLOCK )
		ON t.ser_num = c.ser_num
	INNER JOIN fs_sro_oper o ( NOLOCK )
		ON t.sro_num = o.sro_num AND t.sro_line = o.sro_line
	LEFT JOIN fs_unit_cons c2 ( NOLOCK )
		ON c.ser_num = c2.ser_num AND c.eff_date < c2.eff_date
WHERE c2.eff_date IS NULL AND
      t.ser_num = %s
ORDER BY s.open_date DESC""", serial_number)
		if statuses:
			return {'Lines':      statuses[0][0] == 'Open',
			        'Operations': statuses[0][1] == 'Open'}
		else:
			return None

	def get_eff_date(self, serial_number: SerialNumber = None) -> datetime.date:
		if serial_number is None:
			serial_number = self.serial_number
		eff_date = slsql.execute("""SELECT TOP 1 c.eff_date AS 'Eff Date'
FROM fs_sro s
	INNER JOIN fs_sro_line t ( NOLOCK )
		ON s.sro_num = t.sro_num
	INNER JOIN fs_unit_cons c ( NOLOCK )
		ON t.ser_num = c.ser_num
	INNER JOIN fs_sro_oper o ( NOLOCK )
		ON t.sro_num = o.sro_num AND t.sro_line = o.sro_line
	LEFT JOIN fs_unit_cons c2 ( NOLOCK )
		ON c.ser_num = c2.ser_num AND c.eff_date < c2.eff_date
WHERE c2.eff_date IS NULL AND
      t.ser_num = %s
ORDER BY s.open_date DESC""", serial_number)
		if eff_date:
			return eff_date[0].Eff_Date.date()
		else:
			return None

	def start(self):
		started_status = f"Started({self.status})"
		mssql.execute("""UPDATE PyComm SET Status = %s WHERE Id = %d""", (started_status, self.ID))
		self.life_timer = Timer.start()
		self.start_time = datetime.datetime.now().time().strftime("%H:%M:%S.%f")
		self.start_date = datetime.datetime.now().date().strftime("%Y-%m-%d")

	def end(self, *, results: str, reason: str, batch_amt: int = None):
		if batch_amt is None:
			batch_amt = self.batch_amt_default
		log.info(f"Batch amount: {batch_amt}")
		life_time = self.life_timer.stop().total_seconds()
		parts_count = len(self.parts)
		parts_transacted_count = len(self.parts_transacted)
		if self.parts:
			parts_string = ", ".join(str(part) for part in self.parts)
			if len(self.parts_transacted) > 0:
				parts_transacted_string = ", ".join(str(part) for part in self.parts_transacted)
			else:
				parts_transacted_string = 'None'
		else:
			parts_string = 'None'
			parts_transacted_string = 'None'
		process = 'Transaction' if self.status == 'Queued' else self.status
		life_time /= batch_amt
		end_time = datetime.datetime.now().time().strftime("%H:%M:%S.%f")
		carrier_str = self.build.carrier[0].upper() if self.build.carrier is not None else '-'
		mssql.execute("""INSERT INTO [Statistics] ([Serial Number], 
Carrier, 
Build, 
Suffix, 
Operator, 
Operation, 
[Part Nums Requested], 
[Part Nums Transacted], 
[Parts Requested], 
[Parts Transacted], 
[Input DateTime], 
Date, 
[Start Time], 
[SRO Operations Time], 
[SRO Transactions Time], 
[Misc Issue Time], 
[End Time], 
[Total Time], 
Process, 
Results, 
Reason,
Version
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %d, %d, %s, %s, %s, %d, %d, %d, %s, %d, %s, %s, %s, %s)""",
		              (self.serial_number.number, carrier_str, self.build.core, self.build.type, self.operator.username, self.operation, parts_string, parts_transacted_string,
		               parts_count, parts_transacted_count, self.datetime.strftime('%m/%d/%Y %H:%M:%S'), self.start_date, self.start_time, self.sro_operations_time,
		               self.sro_transactions_time, self.misc_issue_time, end_time, life_time, process, results, reason, version))

	def complete(self, *, batch_amt: int = None):
		self.end(results='Completed', reason='None', batch_amt=batch_amt)
		mssql.execute("""UPDATE PyComm
SET Status = %s
WHERE Id = %d""", (completion_dict[self.status], self.ID))

	@singledispatch
	def skip(self, reason=None, *, batch_amt: int = None):
		reason = 'Skipped' if reason is None else reason
		addon = f"({self.sro})" if reason == 'No Open SRO' else ""
		self.end(results='Skipped', reason=reason, batch_amt=batch_amt)
		status_string = f"{reason}({self.status}){addon}"
		mssql.execute("""UPDATE PyComm SET Status = %s WHERE Id = %d""", (status_string, self.ID))

	@skip.register(str)
	def _(self, reason: str=None, *, batch_amt: int = None):
		reason = 'Skipped' if reason is None else reason
		addon = f"({self.sro})" if reason == 'No Open SRO' else ""
		self.end(results='Skipped', reason=reason, batch_amt=batch_amt)
		status_string = f"{reason}({self.status}){addon}"
		mssql.execute("""UPDATE PyComm SET Status = %s WHERE Id = %d""", (status_string, self.ID))

	@skip.register(BI_EntryError)
	def _(self, reason: BI_EntryError=None, *, batch_amt: int = None):
		try:
			reason = reason.status
		except AttributeError:
			reason = None
		reason = 'Skipped' if reason is None else reason
		addon = f"({self.sro})" if reason == 'No Open SRO' else ""
		self.end(results='Skipped', reason=reason, batch_amt=batch_amt)
		status_string = f"{reason}({self.status}){addon}"
		mssql.execute("""UPDATE PyComm SET Status = %s WHERE Id = %d""", (status_string, self.ID))

	def reset(self):
		mssql.execute("""UPDATE PyComm SET Status = %s WHERE Id = %d""", (self.status, self.ID))


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
			if (not self.win32.SignIn.exists(1, 0.09)) or ('(EM)' in self.win32.top_window().texts()[0]):
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

	def get_popup(self, timeout=1) -> Dialog:
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

	def __init__(self, fp, app_count: int = 0, skip_opt: bool = False):
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

	def apply_all(self, func: Callable, *args, **kwargs):
		with ThreadPoolExecutor(max_workers=len(self.children())) as e:
			for ch in self.children():
				e.submit(func, ch, *args, **kwargs)
				sleep(1)

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
	def __init__(self, n: int, fp=application_filepath, skip_opt: bool = True, forms=[]):
		# print(n, forms)
		user_list = ['bigberae', username, 'BISync01', 'BISync02', 'BISync03']
		pwd_list = ['W!nter17', password, 'N0Trans@cti0ns', 'N0Re@s0ns', 'N0Gue$$!ng']
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

	def run_process(self, process, ppt: Union[str, int, 'Puppet'] = None) -> bool:
		"""Run process, return whether it was successful or not."""
		ppt = self.get_puppet(ppt)
		if hasattr(process, 'get_units'):
			units = process.get_units(exclude=[sn for ch in self.children() for sn in ch.units])
			if units:
				ppt.run_process(process, {unit.serial_number for unit in units}, units)
				return ppt
			return False
		else:
			ppt.run_process(process)
			return ppt

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
					print(args)
					self.q_out.put_nowait(command(self, *args, **kwargs))
					self.status = 'Idle'
					self.units.clear()
				self.status = 'Idle'

		def __init__(self, app: Application, name):
			self.units = set()
			super().__init__(app, name)

		def run_process(self, proc, unit_sn=None, *args, **kwargs):
			self.q_in.put_nowait((proc.run, tuple(arg for arg in args), {k: v for k, v in kwargs.items()}))
			if unit_sn:
				self.units = {str(sn) for sn in unit_sn}


class Timer:
	def __init__(self, *, start_time=None, return_timedelta: bool=False):
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

	def stop(self) -> float:
		retval = self.lap()
		self.reset()
		return retval


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
	def from_name(cls, app: Application, name: str='DataGridView', columns: Union[str, Iterable[str]]=None, row_limit: int=None):
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

class DataGrid:
	_type_dict = {0: bool, 1: int, 2: float, 3: datetime.datetime}
	def __init__(self, control: WindowSpecification,  columns: Union[str, Iterable[str]], rows: int):
		assert control.backend == registry.backends['uia']
		self.window_spec = control
		self.control = uia_controls.uiawrapper.UIAWrapper(control.element_info)
		self.scrollbar_h = self.window_spec.child_window(title='Horizontal Scroll Bar')
		self.scrollbar_v = self.window_spec.child_window(title='Vertical Scroll Bar')
		self.top_row = self.window_spec.child_window(title='Top Row')
		self.column_names = self.get_column_names()
		self.column_number_dict = {i: name for i, name in enumerate(self.column_names)}
		self.master_grid = np.zeros((len(self.column_names), self.row_count, 3), dtype=object)
		self.grid = self.master_grid[..., 0].view().astype(dtype=np.float, copy=False)
		self.types_grid = self.master_grid[..., 1].view()
		self.visibility_grid = self.master_grid[..., 2].view().astype(dtype=np.bool_, copy=False)

	@property
	def row_count(self) -> int:
		return self.count_rows()

	@property
	def element_info(self):
		return self.control.element_info

	def apply_all(self, func: Callable, *args, **kwargs):
		with ThreadPoolExecutor(max_workers=len(self.children())) as e:
			for ch in self.children():
				e.submit(func, ch, *args, **kwargs)
				sleep(1)

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
	def default(cls, app: Application, columns: Union[str, Iterable[str]] = None, rows: int = None):
		return cls.from_name(app, 'DataGridView', columns, rows)

	def row(self, name: str):
		pywinauto.timings.wait_until_passes(20, 0.09, self.control.children, ValueError)
		retval = [row for row in self.control.children() if row.texts()[0].strip() == name]
		if retval:
			return retval[0]
		else:
			return None

	def count_rows(self) -> int:
		pywinauto.timings.wait_until_passes(20, 0.09, self.control.children, ValueError)
		return max([int(row_number_regex.fullmatch(row.texts()[0].strip()).group('row_number')) + 1 for row in self.control.children() if row_number_regex.fullmatch(row.texts()[0].strip())]+[0, 0])

	def get_column_names(self) -> List[str]:
		pywinauto.timings.wait_until_passes(20, 0.09, self.control.children, ValueError)
		return [col.texts()[0].strip() for col in self.top_row.children() if col.texts()[0]]

	@singledispatch
	def get_cell(self, column: str, row: int, visible_only: bool=False, *, specific: int=0):
		if row > self.row_count:
			return None
		column_count = self.column_names.count(column)
		if column_count > 1:  # Best-Match method, slower
			if specific:
				return self.window_spec.child_window(best_match=f'{column}Row{row - 1}DataItem{specific}', visible_only=visible_only)
			return [self.window_spec.child_window(best_match=f'{column}Row{row - 1}DataItem{i + 1}', visible_only=visible_only) for i in range(column_count)]
		else:  # Title-Match method, faster & more precise
			return self.window_spec.child_window(title=f'{column} Row {row - 1}', visible_only=visible_only)

	def get_visible_cells(self):
		min_dim = max_dim = None
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
			if min_dim is None and visible:
				min_dim = i
			if min_dim is not None and not visible:
				max_dim = i
				break

		for dim in ('max', 'min'):
			for mode in ('horizontal', 'vertical'):
				while True:
					try:
						if mode == 'horizontal':
							if dim == 'max':
								pass
							elif dim == 'min':
								pass
						elif mode == 'vertical':
							if dim == 'max':
								pass
							elif dim == 'min':
								pass
					except Exception:
						break






	@staticmethod
	def get_min_area(cell: BaseWrapper, *, anchor: str) -> RECT:
		rect = cell.rectangle()
		w, h = rect.width(), rect.height()
		w_factor, h_factor = [min(2 ** x for x in range(3,10) if (just_over_half(y, x) - z) < 10) for y,z in ((w, w / 2), (h, h / 2))]
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


# - - - - - - - - - - - - - - - - - - - FUNCTIONS - - - - - - - - - - - - - - - - - - - -  # THINK: Maybe move to tools?
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
		sql.execute(f"SELECT COUNT({distinct}[Serial Number]) as [SN_Count] FROM {table} WHERE [Status] = '{status}'")[  # FIXME: SQL command w/ parameters
			0]


def check_serial_number(sql, serial_number: str, status: str, table: str = 'PyComm') -> str:
	"""Verify that serial number hasn't been skipped. Return string."""
	rows = sql.execute(f"SELECT DISTINCT [Status] FROM {table} WHERE [Serial Number] = '{serial_number}'",  # FIXME: SQL command w/ parameters
	                   fetchall=True)
	for row in rows:
		if status not in row.Status:
			continue
		elif (row.Status != status) and (status in row.Status):
			break
	else:
		return status
	return row.Status

@singledispatch
def split_RECT(control: BaseWrapper) -> Tuple[int, int, int, int]:
	rect = control.rectangle()
	return rect.left, rect.top, rect.right, rect.bottom

@split_RECT.register(RECT)
def _(control):
	return control.left, control.top, control.right, control.bottom

# Not one Item Price exists for Item that has
@singledispatch
def center(arg, y1: int, x2: int, y2: int) -> Tuple[int, int]:
	"""Return the center of given coordinates.
	:rtype: tuple
	"""
	assert 0 < arg < x2
	assert 0 < y1 < y2
	x2 -= arg
	y2 -= y1
	return arg + (x2 // 2), y1 + (y2 // 2)

@center.register(int)
def _(arg, y1: int, x2: int, y2: int) -> Tuple[int, int]:
	assert 0 < arg < x2
	assert 0 < y1 < y2
	x2 -= arg
	y2 -= y1
	return arg + (x2 // 2), y1 + (y2 // 2)

# @center.register(RECT)
@center.register(BaseWrapper)
def _(arg) -> Tuple[int, int]:
	x1, y1, x2, y2 = split_RECT(arg)
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


def camelcase_splitter(text: str) -> str:
	return ''.join(y if not (i > 0 and text[i - 1].islower() and text[i].isupper()) else (' ' + y) for i, y in enumerate(text))


def date_string(dt: datetime.datetime, century: bool = False) -> str:
	return dt.strftime("%m/%d/%Y") if century else dt.strftime("%m/%d/%y")


def time_string(dt: datetime.datetime, military: bool = True) -> str:
	return dt.strftime("%H:%M:%S") if military else dt.strftime("%I:%M:%S %p")


def week_number(dt: datetime.datetime, start: str = 'S') -> int:
	values = {'M': 0, 'S': 1}
	start = start.upper()
	if start not in values:
		raise ValueError()  # TODO: Specify error
	return int(dt.strftime("%U")) if values[start] else int(dt.strftime("%W"))


def weekday_string(dt: datetime.datetime, abbreviated: bool = True) -> str:
	return dt.strftime("%a") if abbreviated else dt.strftime("%A")


def month_string(dt: datetime.datetime, abbreviated: bool = True) -> str:
	return dt.strftime("%b") if abbreviated else dt.strftime("%B")


def pprint_dict(text: Dict[str, Union[Any, Tuple[Any, int]]], justify_keys: int = 0, justify_values: int = 0):
	warning_string = (' ' * (justify_keys + justify_values + 1)) + '<!WARNING!> {} OVER THRESHOLD <!WARNING!>'

	def modify(x):
		if type(x) is str:
			x = camelcase_splitter(x)
		if type(x) is datetime.datetime:
			x = date_string(x)
		return x

	max_key_length = max((len(str(modify(k))) for k in text.keys()))
	if all(type(t) is tuple for t in text.values()):
		max_value_length = max((len(str(modify(v[0]))) for v in text.values()))
		if justify_keys and justify_values:
			[print(str(modify(k) + ':').ljust(max_key_length + justify_keys), str(modify(v[0])).rjust(max_value_length + justify_values) + (warning_string.format(v[1]) if v[1] else '')) for k, v in
			 text.items()]
		elif justify_keys:
			[print(str(modify(k) + ':').ljust(max_key_length + justify_keys), str(modify(v[0])) + (warning_string.format(v[1]) if v[1] else '')) for k, v in text.items()]
		elif justify_values:
			[print(str(modify(k) + ':'), str(modify(v[0])).rjust(max_value_length + justify_values) + (warning_string.format(v[1]) if v[1] else '')) for k, v in text.items()]
		else:
			[print(str(modify(k) + ':'), str(modify(v))) for k, v in text.items()]
	else:
		max_value_length = max((len(str(modify(v))) for v in text.values()))
		if justify_keys and justify_values:
			[print(str(modify(k) + ':').ljust(max_key_length + justify_keys), str(modify(v)).rjust(max_value_length + justify_values)) for k, v in text.items()]
		elif justify_keys:
			[print(str(modify(k) + ':').ljust(max_key_length + justify_keys), str(modify(v))) for k, v in text.items()]
		elif justify_values:
			[print(str(modify(k) + ':'), str(modify(v)).rjust(max_value_length + justify_values)) for k, v in text.items()]
		else:
			[print(str(modify(k) + ':'), str(modify(v))) for k, v in text.items()]


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


# THINK: New type for type annotating that specifies range of possible return values(for overloading)?
# example 1: arg1 -> string.length(5) | arg2 -> string.length(8)
# example 2: arg1 -> int_range(00, 01, …, 23) | arg2 -> int_range(01, 02, …, 12)

# THINK: New type for type annotating that specifies range of possible argument values(for overloading)?
# example 1: int_range(00, 01, …, 11) -> retval else raise Index/Type/ValueError
# example 2: possible_args('S', 'M') -> retval else raise Index/Type/ValueError

# THINK: Functions within argument, ie str.upper() -> performs upper() on provided argument, ensuring specific case
# TODO: Test possible solution: Decorators, wrapping with

# THINK: Functions within retval, ie int() -> performs int() on provided retval, ensuring specific result
# TODO: Possible solution: Decorators, wrapping with


# TODO: When positional-only arguments are finally added
# PEP 457: https://www.python.org/dev/peps/pep-0457/

# hcursor 65543 == loading

"""
def sql_connect(cls, [address: str, username: str, password: str,] database: str, [detect_types: int = 0,] *, key: str, legacy_encryption: bool = True, quiet: bool = False):
either:    address, username, password, database
or:                                     database, detect_types
"""

__all__ = ['Unit', 'Application', 'center', 'access_grid', 'parse_numeric_ranges', 'process_pid', 'Timer',
           'is_running', 'get_screen_size', 'count_screens', 'total_screen_space', 'enumerate_screens', 'DataGrid',
           '_check_units', 'check_serial_number']
