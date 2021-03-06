import configparser
import datetime
import logging.config
import pathlib
import re
from collections import defaultdict, namedtuple
from random import choice
from string import ascii_lowercase, punctuation
from sys import exc_info
from time import sleep
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Tuple, Union

import psutil
import pyautogui as pag
import pywinauto as pwn
import win32gui
from pywinauto.controls import common_controls, uia_controls, win32_controls

from constants import CARRIER_DICT, CELLULAR_BUILDS, REGEX_BUILD, REGEX_BUILD_ALT, REGEX_RESOLUTION, REGEX_WINDOW_MENU_FORM_NAME, SUFFIX_DICT, SYTELINE_WINDOW_TITLE
from exceptions import *
from sql import MS_SQL

logging.config.fileConfig('config.ini')
log = logging

config = configparser.ConfigParser()

"""Select ser_num, item from fs_unit (nolock)
Inner join 
( VALUES ('ACB'),('BE'),('BS'),('GMU'),('HB'),('HG'),('HGM'),('HGR'),('HGS'),('LC'),('LCB'),('OT'),('PM'),('SL'),('TD')) as p ([Prefix])
On LEFT(ser_num,LEN(p.Prefix)) = p.Prefix
Where Right(ser_num, Len(ser_num) - len(p.Prefix)) IN 
(('SN1'),('SN2'),('SN3')...)
"""

completion_dict = {'Queued': 'C1', 'Scrap': 'C2', 'Reason': 'C3'}

Dialog = NamedTuple('Dialog', [('self', pwn.WindowSpecification), ('Title', str), ('Text', str),
                               ('Buttons', Dict[str, win32_controls.ButtonWrapper])])


# - - - - - - - - - - - - - - - - - - -  CLASSES  - - - - - - - - - - - - - - - - - - - -
class Part:
	def __init__(self, sql: MS_SQL, part_number: str, quantity: int = 1, spec_build: str = None):
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
						f"SELECT [Qty],[DispName],[Location],[PartName] FROM Parts WHERE [PartNum] = '{self.part_number}' AND [Build] = '{spec_build}'") \
					if sql.execute(
						f"SELECT [Qty],[DispName],[Location],[PartName] FROM Parts WHERE [PartNum] = '{self.part_number}' AND [Build] = '{spec_build}'") \
					else sql.execute(
						f"SELECT [Qty],[DispName],[Location],[PartName] FROM Parts WHERE [PartNum] = '{self.part_number}'")
			else:
				_data = sql.execute(
						f"SELECT [Qty],[DispName],[Location],[PartName] FROM Parts WHERE [PartNum] = '{self.part_number}' AND [Build] = 'All'") \
					if sql.execute(
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
	def __init__(self, mssql: MS_SQL, slsql: MS_SQL, args: NamedTuple):
		config.read_file(open('config.ini'))
		self._mssql = mssql
		self._slsql = slsql
		self.version = config.get('DEFAULT', 'version')
		tbl_mod = config.get('DEFAULT', 'table')
		self._table = 'PyComm' if int(tbl_mod) else 'PyComm2'
		self.id, self.serial_number, self.operation, self.operator, \
		self.datetime, self.notes, self._status = (args.Id, args.Serial_Number, args.Operation, args.Operator,
		                                           args.DateTime, args.Notes, args.Status)
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
		if self._status.lower() == 'reason' and self.notes is None:
			raise InvalidReasonCodeError(reason_code=str(self.notes), spec_id=str(self.id))
		# elif self._status.lower() == 'scrap' and self.notes is None:
		# 	raise InvalidReasonCodeError(reason_code=str(self.notes), spec_id=str(self.id))
		self._serial_number_prefix = self._product = self.whole_build = self._operator_initials = \
			self.eff_date = self.sro_num = self.sro_line = self.SRO_Operations_status = self.SRO_Line_status = None
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
					self.general_resolution_name = \
						mssql.execute(f"SELECT TOP 1 [Failure] FROM FailuresRepairs WHERE [ReasonCodes] = '{self.notes}'")[
							0]
			except TypeError as ex:
				raise InvalidReasonCodeError(reason_code=str(self.notes), spec_id=str(self.id), msg=str(ex))
			# TODO: For HG, allow Invalid Reason Codes, just enter in operator initials
		if self._status.lower() != 'scrap':
			self.start()

	def start(self):
		self._mssql.execute(
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
		self._mssql.execute("INSERT INTO [Statistics]"
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
		self._mssql.execute(
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
		self._mssql.execute(
				f"UPDATE {self._table} SET [Status] = '{reason}({self._status2}){addon}' WHERE [Id] = {self.id} AND [Serial Number] = '{self.serial_number}'")
		self._mssql.execute("INSERT INTO [Statistics]"
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
		self._mssql.execute(
				f"UPDATE {self._table} SET [Status] = '{self._status2}' WHERE [Id] = {self.id} AND [Serial Number] = '{self.serial_number}'")

	def update_sl_data(self):
		try:
			self.sro_num, self.sro_line, self.eff_date, self.SRO_Operations_status, self.SRO_Line_status = self.sl_data
			self.eff_date = self._slsql.execute(f"""Select TOP 1 c.eff_date as 'Eff Date'
From fs_sro s (nolock)
 Inner join fs_sro_line l (nolock)
 on s.sro_num = l.sro_num
 Inner join fs_unit_cons c (nolock)
 on l.ser_num = c.ser_num
 Inner join fs_sro_oper o (nolock)
 on l.sro_num = o.sro_num and l.sro_line = o.sro_line
 Where
 c.eff_date < '{self.datetime.date().strftime("%m/%d/%Y")}' and
 l.ser_num = '{self.serial_number_prefix+self.serial_number}'
  Order by c.eff_date DESC""")[0]
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
				value = self._mssql.execute(
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
					self._parts = list({Part(self._mssql, x, spec_build='206') for x in value})
				elif '200' in self.whole_build:
					self._parts = list({Part(self._mssql, x, spec_build='200') for x in value})
				else:
					self._parts = list({Part(self._mssql, x) for x in value})
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
			first, last = self._mssql.execute(
					f"SELECT [FirstName],[LastName] FROM Users WHERE [Username] = '{self.operator}'")
			self._operator_initials = first.strip()[0].upper() + last.strip()[0].upper()
		return self._operator_initials

	@operator_initials.setter
	def operator_initials(self, value):
		self._operator_initials = value

	@property
	def product(self):
		if self._product is None:
			data = self._mssql.execute(f"SELECT [Product] FROM Prefixes WHERE [Prefix] = '{self.serial_number_prefix}'")
			if not data:
				raise ValueError
			self._product = data[0]
		return self._product

	@product.setter
	def product(self, value):
		self._product = value

	def get_oldest_datetime(self):
		date = self.eff_date.strftime('%m/%d/%Y')
		return self._mssql.execute(f"SELECT [DateTime] FROM PyComm WHERE [Serial Number] = '{self.serial_number}' AND [DateTime] >= '{date}' ORDER BY [DateTime] ASC")[0]

class Unit_ALT:
	def __init__(self, mssql: MS_SQL, slsql: MS_SQL, sn: str):
		self.SKIPME = False
		self._mssql = mssql
		self._slsql = slsql
		self.serial_number = sn
		self._serial_number_prefix = self.eff_date = self.sro_num = self.sro_line = self.SRO_Operations_status = self.SRO_Line_status = None
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
			self.SKIPME = True
		else:
			gc, item, loc, whse = build_data
			if gc.upper().startswith('BE'):
				self.serial_number_prefix = 'BE'
			elif gc.upper().startswith('ACB'):
				self.serial_number_prefix = 'ACB'
			self.update_sl_data()
		if self.sl_data is None:
			self.SKIPME = True
		elif self.SRO_Line_status == 'Closed':
			self.SKIPME = True
		elif self.SRO_Operations_status == 'Closed':
			self.SKIPME = True

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
				value = self._mssql.execute(
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


class Application(psutil.Process):
	def __init__(self, fp: Union[str, pathlib.Path], exclude: Union[int, Iterable[int]] = None):
		if type(fp) is pathlib.Path:
			fp = str(fp)
		# TODO: Improve catching already open and available application instances
		if is_running(fp, exclude):
			super().__init__(process_pid(fp, exclude))
		else:
			super().__init__(psutil.Popen(fp).pid)
		self.fp = fp
		self.nice(psutil.HIGH_PRIORITY_CLASS)
		self.win32 = pwn.Application(backend='win32').connect(process=self.pid)
		self.uia = pwn.Application(backend='uia').connect(process=self.pid)
		self._user = None
		self.logged_in = False

	def log_in(self, usr: str, pwd: str):
		if not self.logged_in and self.win32.SignIn.exists(10, 0.09):
			log.info("SyteLine not logged in, starting login procedure")
			self.win32.SignIn.UserLoginEdit.set_text(usr)
			self.win32.SignIn.PasswordEdit.set_text(pwd)
			self.win32.SignIn.set_focus()
			self.win32.SignIn.OKButton.click()
			if not self.win32.SignIn.exists(10, 0.09):
				self.win32.window(title_re=SYTELINE_WINDOW_TITLE).wait('ready', 2, 0.09)
				self.logged_in = True
				log.info(f"Successfully logged in as '{usr}'")
				sleep(4)
			else:
				log.warning(f"Login attempt as '{usr}' unsuccessful")

	def log_out(self):
		if self.logged_in and self.uia.window(title_re=SYTELINE_WINDOW_TITLE).exists(10, 0.09):
			log.info("SyteLine logged in, starting logout procedure")
			sl_uia = self.uia.window(title_re=SYTELINE_WINDOW_TITLE)
			so = [item for item in sl_uia.MenuBar.items() if item.texts()[0].lower().strip() == 'sign out'][0]
			sl_uia.set_focus()
			r_i = so.rectangle()
			c_coords = center(x1=r_i.left, y1=r_i.top, x2=r_i.right, y2=r_i.bottom)
			pag.click(*c_coords)
			if self.win32.SignIn.exists(10, 0.09):
				self.win32.SignIn.wait('ready', 2, 0.09)
				self.logged_in = False
				log.info(f"Successfully logged out")
				sleep(4)
			else:
				log.warning(f"Logout attempt unsuccessful")

	def move_and_resize(self, left: int, top: int, right: int, bottom: int):
		self._hwnd = self.win32.handle
		# hwnd = win32gui.GetForegroundWindow()
		# coord = Coordinates(left=left, top=top, right=right, bottom=bottom)
		coord = {'left': left, 'top': top, 'right': right, 'bottom': bottom}
		win32gui.MoveWindow(self._hwnd, int(coord['left']) - 7, coord['top'], coord['right'] - coord['left'],
		                    coord['bottom'] - coord['top'], True)

	def open_form(self, *names):
		open_forms = self.forms.keys()
		log.debug(f"Opening form(s): {', '.join(names)}")
		for name in names:
			if name in open_forms:
				raise ValueError(f"Form '{name}' already open")
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
		          sl_uia.WindowMenu.items()
		          if (item.texts()[0].lower() != 'cascade') and (item.texts()[0].lower() != 'tile') and (
			          item.texts()[0].lower() != 'close all')}
		log.debug(f"Forms open: {', '.join(retval.keys())}")
		return retval

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


class Application_ALT(psutil.Process):
	def __init__(self, fp: Union[str, pathlib.Path], exclude: Union[int, Iterable[int]] = None):
		if type(fp) is pathlib.Path:
			fp = str(fp)
		if is_running(fp, exclude):
			super().__init__(process_pid(fp, exclude))
		else:
			super().__init__(psutil.Popen(fp).pid)
		self.fp = fp
		self.nice(psutil.HIGH_PRIORITY_CLASS)
		self.win32 = pwn.Application(backend='win32').connect(process=self.pid)
		self.uia = pwn.Application(backend='uia').connect(process=self.pid)
		self._user = None
		self.logged_in = False

	def log_in(self, usr: str, pwd: str):
		if not self.logged_in and self.win32.SignIn.exists(10, 0.09):
			self.win32.SignIn.UserLoginEdit.set_text(usr)
			self.win32.SignIn.PasswordEdit.set_text(pwd)
			self.win32.SignIn.set_focus()
			self.win32.SignIn.OKButton.click()
			if not self.win32.SignIn.exists(10, 0.09):
				self.win32.window(title_re=SYTELINE_WINDOW_TITLE).wait('ready', 2, 0.09)
				self.logged_in = True
				sleep(4)

	def open_form(self, *names):
		open_forms = self.forms.keys()
		for name in names:
			if name in open_forms:
				raise ValueError(f"Form '{name}' already open")
			sl_win = self.win32.window(title_re=SYTELINE_WINDOW_TITLE)
			sl_win.send_keystrokes('^o')
			self.win32.SelectForm.AllContainingEdit.set_text(name)
			self.win32.SelectForm.set_focus()
			self.win32.SelectForm.FilterButton.click()
			common_controls.ListViewWrapper(self.win32.SelectForm.ListView).item(name).click()
			self.win32.SelectForm.set_focus()
			self.win32.SelectForm.OKButton.click()
			sleep(4)

	def find_value_in_collection(self, collection: str, property_: str, value, case_sensitive=False):
		sl_win = self.win32.window(title_re=SYTELINE_WINDOW_TITLE)
		sl_win.send_keystrokes('%e')
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
		sl_uia = self.uia.window(title_re=SYTELINE_WINDOW_TITLE)
		retval = {REGEX_WINDOW_MENU_FORM_NAME.search(item.texts()[0]).group(1): item for item in
		          sl_uia.WindowMenu.items()
		          if (item.texts()[0].lower() != 'cascade') and (item.texts()[0].lower() != 'tile') and (
			          item.texts()[0].lower() != 'close all')}
		return retval

	def get_focused_form(self) -> str:
		for item in self.forms.items():
			name, form = item
			state = form.legacy_properties()['State']
			bin_state = bin(state)
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


class PuppetMaster:
	_children = set()
	pids = defaultdict(list)

	def __init__(self, fp: Optional[Union[str, pathlib.Path]] = None):
		if fp is not None:
			self.start(fp)

	def start(self, fp: Union[str, pathlib.Path]) -> Application:
		name = ''.join(choice(ascii_lowercase) for i in range(4))
		while name in self._children:
			name = ''.join(choice(ascii_lowercase) for i in range(4))
		self.__setattr__(name, Application(fp, exclude=list(self.pids.values())))
		self.pids[fp].append(self.__getattribute__(name).pid)
		self._children.add(name)
		return self.__getattribute__(name)

	def children(self):
		return [self.__getattribute__(ch) for ch in self._children]

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		procs = self.children()
		for p in procs:
			# print(p)
			p.terminate()
		gone, still_alive = psutil.wait_procs(procs, timeout=3)
		for p in still_alive:
			# print(p)
			p.kill()


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


# - - - - - - - - - - - - - - - - - - - FUNCTIONS - - - - - - - - - - - - - - - - - - - -
def process_pid(filename: str, exclude: Optional[Union[int, Iterable[int]]] = None) -> int:
	for proc in psutil.process_iter():
		try:
			if exclude is not None and ((isinstance(exclude, int) and proc.pid == exclude) or proc.pid in exclude):
				continue
			if proc.exe().lower() == filename.lower():
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
	for proc in psutil.process_iter():
		try:
			if exclude is not None and ((isinstance(exclude, int) and proc.pid == exclude) or proc.pid in exclude):
				continue
			if proc.exe().lower() == filename.lower():
				return True
		except (psutil.NoSuchProcess, psutil.AccessDenied):
			pass
	return False


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


def access_grid(grid: uia_controls.ListViewWrapper, columns: Union[str, Iterable[str]],
                condition: Optional[Tuple[str, Any]] = None, requirement: str = None) -> List[NamedTuple]:
	if type(columns) is str:
		columns = [columns]
	# TODO: regex datetime
	# TODO: better condition handling (exec string?)
	DataRow = namedtuple('DataRow', field_names=[col.replace(' ', '_') for col in columns])
	if requirement is not None:
		if condition is None:
			retval = [DataRow(**{
				col.replace(' ', '_'): _adapt_cell(
						uia_controls.ListViewWrapper(row.element_info).item(
								grid.children()[grid.children_texts().index('Top Row')].children_texts().index(
										col)).legacy_properties()['Value'].strip())
				for col in columns}) for row in grid.children()[grid.children_texts().index('Row 0'):] if _adapt_cell(
					uia_controls.ListViewWrapper(row.element_info).item(
							grid.children()[grid.children_texts().index('Top Row')].children_texts().index(
									requirement)).legacy_properties()['Value'].strip()) != None]
		else:
			retval = [DataRow(**{
				col.replace(' ', '_'): _adapt_cell(
						uia_controls.ListViewWrapper(row.element_info).item(
								grid.children()[grid.children_texts().index('Top Row')].children_texts().index(
										col)).legacy_properties()['Value'].strip())
				for col in columns}) for row in grid.children()[grid.children_texts().index('Row 0'):] if _adapt_cell(
					uia_controls.ListViewWrapper(row.element_info).item(
							grid.children()[grid.children_texts().index('Top Row')].children_texts().index(
									condition[0])).legacy_properties()[
						'Value'].strip()) == condition[1] and _adapt_cell(
					uia_controls.ListViewWrapper(row.element_info).item(
							grid.children()[grid.children_texts().index('Top Row')].children_texts().index(
									requirement)).legacy_properties()['Value'].strip()) != None]
	else:
		if condition is None:
			retval = [DataRow(**{col.replace(' ', '_'): _adapt_cell(uia_controls.ListViewWrapper(row.element_info).item(
					grid.children()[grid.children_texts().index('Top Row')].children_texts().index(
							col)).legacy_properties()['Value'].strip())
			                     for col in columns}) for row in grid.children()[grid.children_texts().index('Row 0'):]]
		else:
			retval = [DataRow(**{
				col.replace(' ', '_'): _adapt_cell(uia_controls.ListViewWrapper(row.element_info).item(
						grid.children()[grid.children_texts().index('Top Row')].children_texts().index(
								col)).legacy_properties()['Value'].strip())
				for col in columns}) for row in grid.children()[grid.children_texts().index('Row 0'):] if _adapt_cell(
					uia_controls.ListViewWrapper(row.element_info).item(
							grid.children()[grid.children_texts().index('Top Row')].children_texts().index(
									condition[0])).legacy_properties()['Value'].strip()) == condition[1]]
	log.debug(f"Grid Accessed: {retval}")
	return retval


# Not one Item Price exists for Item that has
# @overload
def center(x1: int, y1: int, x2: int, y2: int) -> Tuple[int, int]:
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


# def center(x: int, y: int, w: int, h: int) -> Tuple[int, int]:
# 	return x + (w // 2), y + (h // 2)


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


timer = TestTimer()
