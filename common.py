from __init__ import __author__
import re
import pathlib
import datetime
import configparser
import logging.config
from sys import exc_info
from random import choice
from string import ascii_lowercase
from collections import defaultdict, namedtuple
from typing import NamedTuple, Union, Tuple, Optional, Iterable, List, Any
from ast import literal_eval

import psutil
import pywinauto as pwn
from pywinauto.controls import uia_controls
import win32gui

from exceptions import *
from sql import MS_SQL
from constants import REGEX_WINDOW_MENU_FORM_NAME, REGEX_BUILD
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


# - - - - - - - - - - - - - - - - - - -  CLASSES  - - - - - - - - - - - - - - - - - - - -
class Part:
	def __init__(self, sql: MS_SQL, part_number: str, quantity: int=1):
		self.part_number = part_number
		_data = sql.execute(f"SELECT [Qty],[DispName],[Location],[PartName] FROM Parts WHERE [PartNum] = '{self.part_number}'")
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
		self.id, self.serial_number, build, self.suffix, self.operation, self.operator, \
		self.parts, self.datetime, self.notes, self._status = args
		log.debug(f"Attribute id={self.id}")
		log.debug(f"Attribute serial_number='{self.serial_number}'")
		log.debug(f"Attribute suffix='{self.suffix}'")
		log.debug(f"Attribute operation='{self.operation}'")
		log.debug(f"Attribute operator='{self.operator}'")
		log.debug(f"Attribute notes='{self.notes}'")
		log.debug(f"Attribute _status='{self._status}'")
		log.debug(f"Property parts='{self.parts}'")
		log.debug(f"Property datetime='{self.datetime}'")
		"""From PyComm p
				Cross apply dbo.Split(p.Parts, ',') b
				Inner join Parts n
				on b.items = n.PartNum
				Where p.[Serial Number] = @SN
		"""
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
			raise UnitClosedError(f"Unit '{self.serial_number}' has no SROs")
		gc, item, loc, whse = build_data
		if gc.upper().startswith('BE'):
			self.serial_number_prefix = 'BE'
		elif gc.upper().startswith('ACB'):
			self.serial_number_prefix = 'ACB'
		log.debug(f"Property serial_number_prefix='{self.serial_number_prefix}'")
		self.update_sl_data()
		log.debug(f"Attribute sro_num='{self.sro_num}'")
		log.debug(f"Attribute sro_line='{self.sro_line}'")
		log.debug(f"Attribute eff_date='{self.eff_date}'")
		log.debug(f"Attribute SRO_Line_status='{self.SRO_Line_status}'")
		log.debug(f"Attribute SRO_Operations_status='{self.SRO_Operations_status}'")
		self._regex_dict = REGEX_BUILD.match(item.upper()).groupdict(default='-')
		self.location = loc
		log.debug(f"Attribute location='{self.location}'")
		self.warehouse = whse
		log.debug(f"Attribute warehouse='{self.warehouse}'")
		self.build = self._regex_dict['build'][:3]
		log.debug(f"Attribute build='{self.build}'")
		self.whole_build = item.upper()
		log.debug(f"Attribute whole_build='{self.whole_build}'")
		carrier_dict = {'V': 'Verizon', 'S': 'Sprint', '-': None}
		self.carrier = carrier_dict[self._regex_dict['carrier']]
		log.debug(f"Attribute carrier='{self.carrier}'")
		if self._status.lower() != 'scrap':  # Because they're done in batches by a single computer, no risk of overlap
			self.start()

	def start(self):
		self._mssql.execute(f"UPDATE PyComm SET [Status] = 'Started({self._status})' WHERE [Id] = {self.id} AND [Serial Number] = '{self.serial_number}'")
		self._life_timer = TestTimer()
		self._life_timer.start()
		self._start_time = datetime.datetime.now().time().strftime("%H:%M:%S.%f")
		self._date = datetime.datetime.now().date().strftime("%Y-%m-%d")

	def complete(self):
		value = self.sro_operations_timer.stop()
		if value is not None:
			self.sro_operations_time += value
		value = self.sro_transactions_timer.stop()
		if value is not None:
			self.sro_transactions_time += value
		value = self.misc_issue_timer.stop()
		if value is not None:
			self.misc_issue_time += value
		value = self._life_timer.stop()
		if value is not None:
			life_time = value.total_seconds()
		else:
			life_time = None
		if len(self.parts_transacted) > 0:
			try:
				t_parts = ', '.join(x.part_number + ' x ' + str(x.quantity) for x in self.parts_transacted)
			except TypeError:
				t_parts = 'None'
		else:
			t_parts = 'None'
		if self._status == 'Queued':
			process = 'Transaction'
		else:
			process = self._status
		self._mssql.execute("INSERT INTO [Statistics]"
		                    "([Serial Number],[Carrier],[Build],[Suffix],[Operator],[Operation],"
		                    "[Part Nums Requested],[Part Nums Transacted],[Parts Requested],[Parts Transacted],[Input DateTime],[Date],"
		                    "[Start Time],[SRO Operations Time],[SRO Transactions Time],[Misc Issue Time],[End Time],"
		                    "[Total Time],[Process],[Results],[Version])"
		                    f"VALUES ('{self.serial_number}','{self._regex_dict['carrier']}','{self._regex_dict['build'][:3]}',"
		                    f"'{self.suffix}','{self.operator}','{self.operation}','{', '.join(x.part_number + ' x ' + str(x.quantity) for x in self.parts)}',"
		                    f"'{t_parts}',{len(self.parts)},{len(self.parts_transacted)},"
		                    f"'{self.datetime.strftime('%m/%d/%Y %H:%M:%S')}','{self._date}','{self._start_time}',"
		                    f"{self.sro_operations_time.total_seconds()},{self.sro_transactions_time.total_seconds()},"
		                    f"{self.misc_issue_time.total_seconds()},'{datetime.datetime.now().time().strftime('%H:%M:%S.%f')}',"
		                    f"{life_time},'{process}','Completed','{self.version}')")
		self._mssql.execute(f"DELETE FROM PyComm WHERE [Id] = {self.id} AND [Serial Number] = '{self.serial_number}'")

	def skip(self, reason: Optional[str]=None):
		value = self.sro_operations_timer.stop()
		if value is not None:
			self.sro_operations_time += value
		value = self.sro_transactions_timer.stop()
		if value is not None:
			self.sro_transactions_time += value
		value = self.misc_issue_timer.stop()
		if value is not None:
			self.misc_issue_time += value
		value = self._life_timer.stop()
		if value is not None:
			life_time = value.total_seconds()
		else:
			life_time = 0
		if reason is None:
			reason = 'Skipped'
		if len(self.parts_transacted) > 0:
			try:
				t_parts = ', '.join(x.part_number + ' x ' + str(x.quantity) for x in self.parts_transacted)
			except TypeError:
				t_parts = 'None'
		else:
			t_parts = 'None'
		if self._status == 'Queued':
			process = 'Transaction'
		else:
			process = self._status
		self._mssql.execute(f"UPDATE PyComm SET [Status] = '{reason}({self._status})' WHERE [Id] = {self.id} AND [Serial Number] = '{self.serial_number}'")
		self._mssql.execute("INSERT INTO [Statistics]"
		                    "([Serial Number],[Carrier],[Build],[Suffix],[Operator],[Operation],"
		                    "[Part Nums Requested],[Part Nums Transacted],[Parts Requested],[Parts Transacted],[Input DateTime],[Date],"
		                    "[Start Time],[SRO Operations Time],[SRO Transactions Time],[Misc Issue Time],[End Time],"
		                    "[Total Time],[Process],[Results],[Reason],[Version])"
		                    f"VALUES ('{self.serial_number}','{self._regex_dict['carrier']}','{self._regex_dict['build'][:3]}',"
		                    f"'{self.suffix}','{self.operator}','{self.operation}','{', '.join(x.part_number + ' x ' + str(x.quantity) for x in self.parts)}',"
		                    f"'{t_parts}',{len(self.parts)},{len(self.parts_transacted)},"
		                    f"'{self.datetime.strftime('%m/%d/%Y %H:%M:%S')}','{self._date}','{self._start_time}',"
		                    f"{self.sro_operations_time.total_seconds()},{self.sro_transactions_time.total_seconds()},"
		                    f"{self.misc_issue_time.total_seconds()},'{datetime.datetime.now().time().strftime('%H:%M:%S.%f')}',"
		                    f"{life_time},'{process}','Skipped','{reason}','{self.version}')")

	def reset(self):
		self._mssql.execute(f"UPDATE PyComm SET [Status] = '{self._status}' WHERE [Id] = {self.id} AND [Serial Number] = '{self.serial_number}'")

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

	@property
	def serial_number_prefix(self) -> str:
		try:
			if self._serial_number_prefix is None:
				value = self._mssql.execute(f"SELECT p.[Prefix] FROM Prefixes p INNER JOIN Prefixes r ON r.[Product]=p.[Product] WHERE r.[Prefix] = '{self.serial_number[:2]}' AND r.[Type] = 'N' AND p.[Type] = 'P'")[0]
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
			value = value.split(',')
			if value != ['']:
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
			first, last = self._mssql.execute(f"SELECT [FirstName],[LastName] FROM Users WHERE [Username] = '{self.operator}'")
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


class Unit2:
	def __init__(self, mssql: MS_SQL, slsql: MS_SQL, args: NamedTuple):
		config.read_file(open('config.ini'))
		self._mssql = mssql
		self._slsql = slsql
		self.version = config.get('DEFAULT', 'version')
		self.id, self.serial_number, build, self.suffix, self.operation, self.operator, \
		self.parts, self.datetime, self.notes, self._status = args
		log.debug(f"Attribute id={self.id}")
		log.debug(f"Attribute serial_number='{self.serial_number}'")
		log.debug(f"Attribute suffix='{self.suffix}'")
		log.debug(f"Attribute operation='{self.operation}'")
		log.debug(f"Attribute operator='{self.operator}'")
		log.debug(f"Attribute notes='{self.notes}'")
		log.debug(f"Attribute _status='{self._status}'")
		log.debug(f"Property parts='{self.parts}'")
		log.debug(f"Property datetime='{self.datetime}'")
		"""From PyComm p
				Cross apply dbo.Split(p.Parts, ',') b
				Inner join Parts n
				on b.items = n.PartNum
				Where p.[Serial Number] = @SN
		"""
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
			raise UnitClosedError(f"Unit '{self.serial_number}' has no SROs")
		gc, item, loc, whse = build_data
		if gc.upper().startswith('BE'):
			self.serial_number_prefix = 'BE'
		elif gc.upper().startswith('ACB'):
			self.serial_number_prefix = 'ACB'
		log.debug(f"Property serial_number_prefix='{self.serial_number_prefix}'")
		self.update_sl_data()
		log.debug(f"Attribute sro_num='{self.sro_num}'")
		log.debug(f"Attribute sro_line='{self.sro_line}'")
		log.debug(f"Attribute eff_date='{self.eff_date}'")
		log.debug(f"Attribute SRO_Line_status='{self.SRO_Line_status}'")
		log.debug(f"Attribute SRO_Operations_status='{self.SRO_Operations_status}'")
		self._regex_dict = REGEX_BUILD.match(item.upper()).groupdict(default='-')
		self.location = loc
		log.debug(f"Attribute location='{self.location}'")
		self.warehouse = whse
		log.debug(f"Attribute warehouse='{self.warehouse}'")
		self.build = self._regex_dict['build'][:3]
		log.debug(f"Attribute build='{self.build}'")
		self.whole_build = item.upper()
		log.debug(f"Attribute whole_build='{self.whole_build}'")
		carrier_dict = {'V': 'Verizon', 'S': 'Sprint', '-': None}
		self.carrier = carrier_dict[self._regex_dict['carrier']]
		log.debug(f"Attribute carrier='{self.carrier}'")
		if self._status.lower() != 'scrap':  # Because they're done in batches by a single computer, no risk of overlap
			self.start()

	def start(self):
		# self._mssql.execute(f"UPDATE PyComm SET [Status] = 'Started({self._status})' WHERE [Id] = {self.id} AND [Serial Number] = '{self.serial_number}'")
		self._mssql.execute(f"UPDATE PyComm SET [Status] = 'Started({self._status})' WHERE [Serial Number] = '{self.serial_number}' AND [Status] = '{self._status}'")
		results = self._mssql.execute(f"SELECT [Id],[Operation],[Parts] PyComm WHERE [Status] = 'Started({self._status})' AND [Serial Number] = '{self.serial_number}'", fetchall=True)
		self.ids, self.operations, partsets = [[x[i] for x in results] for i in range(3)]
		if partsets:
			parts_ = ','.join(ps[0] for ps in partsets)
			log.debug(f"Partsets found: {parts_}")
			parts = list({Part(self._mssql, x) for x in parts_.split(',')})
			qty_parts = len(self.parts)
			if parts != self.parts:
				self._parts = parts
				log.debug(f"Parts list updated from {qty_parts} to {len(parts)}")
		self._life_timer = TestTimer()
		self._life_timer.start()
		self._start_time = datetime.datetime.now().time().strftime("%H:%M:%S.%f")
		self._date = datetime.datetime.now().date().strftime("%Y-%m-%d")

	def complete(self):
		value = self.sro_operations_timer.stop()
		if value is not None:
			self.sro_operations_time += value
		value = self.sro_transactions_timer.stop()
		if value is not None:
			self.sro_transactions_time += value
		value = self.misc_issue_timer.stop()
		if value is not None:
			self.misc_issue_time += value
		value = self._life_timer.stop()
		if value is not None:
			life_time = value.total_seconds()
		else:
			life_time = None
		if self._status == 'Queued':
			process = 'Transaction'
		else:
			process = self._status
		t_parts_ref = {Part(self._mssql, x) for x in self.parts_transacted}
		for ID in self.ids:
			opr, opn, prt, dt = self._mssql.execute(
				f"SELECT [Operator],[Operation],[Parts],[DateTime] PyComm WHERE [Status] = 'Started({self._status})' AND [Serial Number] = '{self.serial_number}' AND [Id] = {ID}")
			if type(dt) is str:
				dt = datetime.datetime.strptime(dt, "%m/%d/%Y %I:%M:%S %p")
			if prt:
				parts = ', '.join(y.part_number + ' x ' + str(y.quantity) for y in {Part(self._mssql, x) for x in prt})
				parts_qty = len({Part(self._mssql, x) for x in prt})
				t_parts = ', '.join(y.part_number + ' x ' + str(y.quantity) for y in {Part(self._mssql, x) for x in prt} if y in t_parts_ref)
				if not t_parts:
					t_parts = 'None'
					t_parts_qty = 0
				else:
					t_parts_qty = len({Part(self._mssql, x) for x in prt if Part(self._mssql, x) in t_parts_ref})
			else:
				parts = 'None'
				t_parts = 'None'
				parts_qty = t_parts_qty = 0
			sro_op_total = self.sro_operations_time.total_seconds()
			sro_tr_total = self.sro_transactions_time.total_seconds()
			sro_op_time = sigfig(sro_op_total, sro_op_total / len(self.ids))
			"SELECT t.[Version] FROM (SELECT s.[Version], COUNT(s.[ID]) AS [Count] FROM [Statistics] s WHERE s.[Results] = 'Completed' GROUP BY s.[Version]) t" \
			"WHERE t.[Count] = (SELECT MAX(p.[Count]) FROM (SELECT s.[Version], COUNT(s.[ID]) AS [Count] FROM [Statistics] s WHERE s.[Results] = 'Completed' GROUP BY s.[Version]) p)"

			"SELECT s.[Version], COUNT(s.ID) AS [Completed Count],  CAST(AVG(s.[Total Time]) AS numeric (18, 3)) AS [Average Time] FROM [Statistics] s WHERE s.[Results] = 'Completed' GROUP BY s.[Version]"
			sro_tr_time = sigfig(sro_tr_total, sro_tr_total / len())
			self.sro_transactions_time.total_seconds()
			self.misc_issue_time.total_seconds()
			datetime.datetime.now().time().strftime('%H:%M:%S.%f')
			life_time
			self._mssql.execute("INSERT INTO [Statistics]"
			                    "([Serial Number],[Carrier],[Build],[Suffix],[Operator],[Operation],"
			                    "[Part Nums Requested],[Part Nums Transacted],[Parts Requested],[Parts Transacted],[Input DateTime],[Date],"
			                    "[Start Time],[SRO Operations Time],[SRO Transactions Time],[Misc Issue Time],[End Time],"
			                    "[Total Time],[Process],[Results],[Version])"
			                    f"VALUES ('{self.serial_number}','{self._regex_dict['carrier']}','{self.build}',"
			                    f"'{self.suffix}','{opr}','{opn}','{parts}','{t_parts}',{parts_qty},{t_parts_qty},"
			                    f"'{dt.strftime('%m/%d/%Y %H:%M:%S')}','{self._date}','{self._start_time}',"
			                    f"{self.sro_operations_time.total_seconds()},{self.sro_transactions_time.total_seconds()},"
			                    f"{self.misc_issue_time.total_seconds()},'{datetime.datetime.now().time().strftime('%H:%M:%S.%f')}',"
			                    f"{life_time},'{process}','Completed','{self.version}')")
		self._mssql.execute(f"DELETE FROM PyComm WHERE [Id] = {self.id} AND [Serial Number] = '{self.serial_number}'")

	def skip(self, reason: Optional[str] = None):
		value = self.sro_operations_timer.stop()
		if value is not None:
			self.sro_operations_time += value
		value = self.sro_transactions_timer.stop()
		if value is not None:
			self.sro_transactions_time += value
		value = self.misc_issue_timer.stop()
		if value is not None:
			self.misc_issue_time += value
		value = self._life_timer.stop()
		if value is not None:
			life_time = value.total_seconds()
		else:
			life_time = 0
		if reason is None:
			reason = 'Skipped'
		if len(self.parts_transacted) > 0:
			try:
				t_parts = ', '.join(x.part_number + ' x ' + str(x.quantity) for x in self.parts_transacted)
			except TypeError:
				t_parts = 'None'
		else:
			t_parts = 'None'
		if self._status == 'Queued':
			process = 'Transaction'
		else:
			process = self._status
		self._mssql.execute(f"UPDATE PyComm SET [Status] = '{reason}({self._status})' WHERE [Id] = {self.id} AND [Serial Number] = '{self.serial_number}'")
		self._mssql.execute("INSERT INTO [Statistics]"
		                    "([Serial Number],[Carrier],[Build],[Suffix],[Operator],[Operation],"
		                    "[Part Nums Requested],[Part Nums Transacted],[Parts Requested],[Parts Transacted],[Input DateTime],[Date],"
		                    "[Start Time],[SRO Operations Time],[SRO Transactions Time],[Misc Issue Time],[End Time],"
		                    "[Total Time],[Process],[Results],[Reason],[Version])"
		                    f"VALUES ('{self.serial_number}','{self._regex_dict['carrier']}','{self._regex_dict['build'][:3]}',"
		                    f"'{self.suffix}','{self.operator}','{self.operation}','{', '.join(x.part_number + ' x ' + str(x.quantity) for x in self.parts)}',"
		                    f"'{t_parts}',{len(self.parts)},{len(self.parts_transacted)},"
		                    f"'{self.datetime.strftime('%m/%d/%Y %H:%M:%S')}','{self._date}','{self._start_time}',"
		                    f"{self.sro_operations_time.total_seconds()},{self.sro_transactions_time.total_seconds()},"
		                    f"{self.misc_issue_time.total_seconds()},'{datetime.datetime.now().time().strftime('%H:%M:%S.%f')}',"
		                    f"{life_time},'{process}','Skipped','{reason}','{self.version}')")

	def reset(self):
		self._mssql.execute(f"UPDATE PyComm SET [Status] = '{self._status}' WHERE [Id] = {self.id} AND [Serial Number] = '{self.serial_number}'")

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

	@property
	def serial_number_prefix(self) -> str:
		try:
			if self._serial_number_prefix is None:
				value = self._mssql.execute(
					f"SELECT p.[Prefix] FROM Prefixes p INNER JOIN Prefixes r ON r.[Product]=p.[Product] WHERE r.[Prefix] = '{self.serial_number[:2]}' AND r.[Type] = 'N' AND p.[Type] = 'P'")[0]
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
			value = value.split(',')
			if value != ['']:
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
			first, last = self._mssql.execute(f"SELECT [FirstName],[LastName] FROM Users WHERE [Username] = '{self.operator}'")
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


class Application(psutil.Process):
	def __init__(self, fp: Union[str, pathlib.Path], exclude: Optional[Union[int, Iterable[int]]] = None):
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

	# def log_in(self, usr: str = None, pwd: str = None):
	# 	if pwd is None:
	# 		raise ValueError()
	# 	if usr is None:
	# 		if self._user is not None:
	# 			usr = self._user
	# 		else:
	# 			raise ValueError()
	# 	else:
	# 		self._user = usr
	# 	login_win = self.app_win32['Sign In']
	# 	login_win.set_focus()
	# 	login_win.Edit3.SetEditText(usr)
	# 	login_win.Edit2.SetEditText(pwd)
	# 	login_win.OKButton.Click()
	# 	if self._error.exists():
	# 		message = self._error.Static2.texts()[0]
	# 		if ('count limit' in message) and ('exceeded' in message):
	# 			self._error.OKButton.Click()
	# 	while self._notification.exists():
	# 		try:
	# 			message2 = self._notification.Static2.texts()[0]
	# 			if (f"session for user '{usr}'" in message2) and ('already exists' in message2):
	# 				self._notification['&YesButton'].Click()
	# 			elif ('Exception initializing form' in message2) and ('executable file vbc.exe cannot be found' in message2):
	# 				self._notification.OKButton.Click()
	# 				raise SyteLineFormContainerError("SyteLine window's form container is corrupt/non-existent")
	# 			sleep(1)
	# 		except Exception:
	# 			break
	# 	CV_Config.__init__(self, self._win)
	# 	self.logged_in = True
	#
	# def log_out(self, force_quit=True):
	# 	if force_quit:
	# 		self._win2.child_window(best_match='Sign OutMenuItem').select()
	# 	else:
	# 		# Close out each individual open form properly
	# 		pass
	# 	self.logged_in = False

	def move_and_resize(self, left: int, top: int, right: int, bottom: int):
		self._hwnd = self.win32.handle
		# hwnd = win32gui.GetForegroundWindow()
		# coord = Coordinates(left=left, top=top, right=right, bottom=bottom)
		coord = {'left': left, 'top': top, 'right': right, 'bottom': bottom}
		win32gui.MoveWindow(self._hwnd, int(coord['left']) - 7, coord['top'], coord['right']-coord['left'], coord['bottom']-coord['top'], True)

	def open_form(self, name: str, alias: Optional[str] = None):
		self._win.send_keystrokes('^o')
		# pag.hotkey('ctrl', 'o')
		# win = self._win.child_window(title='Select Form')
		self._win.send_keystrokes('%c')
		# pag.hotkey('alt', 'c')
		# pag.typewrite(name)
		self._win.send_keystrokes(name)
		self._win.send_keystrokes('%f')
		# pag.hotkey('alt', 'f')
		self._win.send_keystrokes('{TAB}')
		self._win.send_keystrokes('{TAB}')
		self._win.send_keystrokes('{TAB}')
		self._win.send_keystrokes('{TAB}')
		self._win.send_keystrokes('{TAB}')
		self._win.send_keystrokes('{TAB}')
		self._win.send_keystrokes('{SPACE}')
		# pag.press('tab', 6)###
		# pag.press('space')###
		lb = self._win.child_window(auto_id='formsListView')
		# lb.click_input()
		# pag.press([name[0], 'up'])
		# selection = lb.get_selection()[0]
		# if selection.name != name:
		# 	start = selection.name
		# 	current = None
		# 	limit = 10
		# 	count = 0
		# 	while current != start and count < limit:
		# 		count += 1
		# 		pag.press('down')
		# 		selection = lb.get_selection()[0]
		# 		if selection.name == name:
		# 			break
		# 		current = selection.name
		# 	else:
		# 		raise ValueError(f"Could not find form '{name}'")
		self._win.send_keystrokes('{DOWN}')
		self._win.send_keystrokes('{ENTER}')
		# pag.press('down')###
		# pag.press('enter')
		if alias:
			name = alias
		self._visible_form = name

	def find_value_in_collection(self, collection: str, property_: str, value, case_sensitive=False):
		sl_win = self.win32.window(title_re='Infor ERP SL (EM)*')
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

	def change_forms(self):
		pass

	@property
	def forms(self):
		sl_uia = self.uia.window(title_re='Infor ERP SL (EM)*')
		return {REGEX_WINDOW_MENU_FORM_NAME.search(item.texts()[0]).group(1): item for item in sl_uia.WindowMenu.items() if (item.texts()[0].lower() != 'cascade') and (item.texts()[0].lower() != 'tile') and (item.texts()[0].lower() != 'close all')}


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
			return None

	def reset(self):
		self._start_time = None

	def stop(self):
		retval = self.lap()
		self.reset()
		return retval


# - - - - - - - - - - - - - - - - - - - FUNCTIONS - - - - - - - - - - - - - - - - - - - -
def process_pid(filename: str, exclude: Optional[Union[int, Iterable[int]]]=None) -> int:
	for proc in psutil.process_iter():
		try:
			if exclude is not None and ((isinstance(exclude, int) and proc.pid == exclude) or proc.pid in exclude):
				continue
			if proc.exe().lower() == filename.lower():
				return proc.pid
		except psutil.NoSuchProcess:
			pass
	return None


def is_running(filename: str, exclude: Optional[Union[int, Iterable[int]]]=None) -> bool:
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
	elif x.rsplit('.', 1)[0].isnumeric():
		return int(x.rsplit('.', 1)[0].isnumeric())
	else:
		return x


def access_grid(grid: uia_controls.ListViewWrapper, columns: Union[str, Iterable[str]], condition: Optional[Tuple[str, Any]]=None, requirement: str=None) -> List[NamedTuple]:
	if type(columns) is str:
		columns = [columns]
	# TODO: regex datetime
	# TODO: better condition handling (exec string?)
	DataRow = namedtuple('DataRow', field_names=[col.replace(' ', '_') for col in columns])
	if requirement is not None:
		if condition is None:
			return [DataRow(**{
				col.replace(' ', '_'): _adapt_cell(
					uia_controls.ListViewWrapper(row.element_info).item(grid.children()[grid.children_texts().index('Top Row')].children_texts().index(col)).legacy_properties()['Value'].strip())
				for col in columns}) for row in grid.children()[grid.children_texts().index('Row 0'):] if _adapt_cell(uia_controls.ListViewWrapper(row.element_info).item(grid.children()[grid.children_texts().index('Top Row')].children_texts().index(requirement)).legacy_properties()['Value'].strip()) != None]
		else:
			return [DataRow(**{
				col.replace(' ', '_'): _adapt_cell(
					uia_controls.ListViewWrapper(row.element_info).item(grid.children()[grid.children_texts().index('Top Row')].children_texts().index(col)).legacy_properties()['Value'].strip())
				for col in columns}) for row in grid.children()[grid.children_texts().index('Row 0'):] if _adapt_cell(
				uia_controls.ListViewWrapper(row.element_info).item(grid.children()[grid.children_texts().index('Top Row')].children_texts().index(condition[0])).legacy_properties()[
					'Value'].strip()) == condition[1] and _adapt_cell(uia_controls.ListViewWrapper(row.element_info).item(grid.children()[grid.children_texts().index('Top Row')].children_texts().index(requirement)).legacy_properties()['Value'].strip()) != None]
	else:
		if condition is None:
			return [DataRow(**{col.replace(' ', '_'): _adapt_cell(uia_controls.ListViewWrapper(row.element_info).item(grid.children()[grid.children_texts().index('Top Row')].children_texts().index(col)).legacy_properties()['Value'].strip())
			                   for col in columns}) for row in grid.children()[grid.children_texts().index('Row 0'):]]
		else:
			return [DataRow(**{
			col.replace(' ', '_'): _adapt_cell(uia_controls.ListViewWrapper(row.element_info).item(grid.children()[grid.children_texts().index('Top Row')].children_texts().index(col)).legacy_properties()['Value'].strip())
				for col in columns}) for row in grid.children()[grid.children_texts().index('Row 0'):] if _adapt_cell(uia_controls.ListViewWrapper(row.element_info).item(grid.children()[grid.children_texts().index('Top Row')].children_texts().index(condition[0])).legacy_properties()['Value'].strip()) == condition[1]]

# Not one Item Price exists for Item that has
# @overload
def center(x1: int, y1: int, x2: int, y2: int) -> Tuple[int, int]:
	assert 0 < x1 < x2
	assert 0 < y1 < y2
	x2 -= x1
	y2 -= y1
	return x1 + (x2 // 2), y1 + (y2 // 2)


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
timer = TestTimer()

