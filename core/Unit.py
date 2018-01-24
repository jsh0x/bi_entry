#! python3 -W ignore
# coding=utf-8

import datetime
import logging
from collections import UserString, defaultdict
from functools import singledispatch
from typing import Any, Dict, List, Tuple, Union

from _globals import *
from core.Timer import Timer
from exceptions import *
from utils.tools import prepare_string

from constants import REGEX_RESOLUTION, carrier_dict, cellular_builds, part_number_regex, unit_type_dict

log = logging.getLogger('root')
u_log = logging.getLogger('UnitLogger')
completion_dict = {'Queued': 'C1', 'Scrap': 'C2', 'Reason': 'C3'}


class Unit:  # TODO: Special methods __repr__ and __str__
	completion_string = None
	status_string = None
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
		def number(self):
			return self._number

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
			for res in results:
				if slsql.execute("""SELECT ser_num FROM fs_unit ( NOLOCK ) WHERE ser_num = %s""", (res.Prefix + number)):
					raise NewUnitError(serial_number=number)
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
			prefix, core = build.split('-')[:2]
			if core.isnumeric():
				core_base = core[-3:]
				carrier = int(core[0]) if len(core) > 3 else None
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
			self.initials = data[0].FirstName[0].upper() + data[0].LastName[0].upper()
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
				data = mssql.execute("""SELECT ID FROM Processes WHERE Process = %s AND Product = 'All'""", (process,))
				if not data:
					raise ValueError()  # TODO: Specify error
			return cls(data[0].ID)

	def __init__(self, ID: int):  # TODO: Split long __init__ into separate functions
		ex = None
		self.version = version
		self.ID = ID
		log.info(f"Attribute ID={self.ID}")

		data = mssql.execute("""SELECT [Serial Number],Build,Suffix,Operation,Operator,Parts,DateTime,Notes,Status FROM PyComm WHERE Id = %d""", self.ID)
		if not data:
			raise ValueError()  # TODO: Specify error

		try:
			self.serial_number = self.SerialNumber.from_base_number(data[0].Serial_Number)
			serial_number_string = str(self.serial_number.number)
		except Exception as exc:
			self.serial_number = str(data[0].Serial_Number)
			if not self.serial_number:
				self.serial_number = 'Unknown'
			serial_number_string = self.serial_number
			if ex is None:
				ex = exc
		finally:
			log.info(f"Attribute serial_number='{self.serial_number}'")
			u_log.debug(f"{str('SN=' + serial_number_string).ljust(13)}|INFO|ID={self.ID}")

		try:
			self.product = self.serial_number.product
		except Exception as exc:
			self.product = 'Unknown'
			if ex is None:
				ex = exc
		finally:
			log.info(f"Attribute product='{self.product}'")
			u_log.debug(f"{str('SN=' + serial_number_string).ljust(13)}|INFO|Product={self.product}")

		try:
			self.build = self.Build.from_SerialNumber(self.serial_number, data[0].Suffix)
		except Exception as exc:
			self.build = str(data[0].Build)
			if not self.build:
				self.build = 'Unknown'
			if ex is None:
				ex = exc
		finally:
			log.info(f"Attribute build='{self.build}'")
			u_log.debug(f"{str('SN=' + serial_number_string).ljust(13)}|INFO|Build={self.build}")

		try:
			self.parts = self.Part.from_string(data[0].Parts, self.build)
			if self.parts:
				part_string = "('" + "', '".join(str(part) for part in self.parts) + "')"
			else:
				part_string = 'None'
		except Exception as exc:
			self.parts = str(data[0].Parts)
			if not self.parts:
				self.parts = 'Unknown'
			part_string = self.parts
			if ex is None:
				ex = exc
		finally:
			log.info(f"Attribute parts={part_string}")
			u_log.debug(f"{str('SN=' + serial_number_string).ljust(13)}|INFO|Parts={part_string}")

		try:
			self.operation = self.Operation.from_string(data[0].Operation, self.product)
		except Exception as exc:
			self.operation = str(data[0].Operation)
			if not self.operation:
				self.operation = 'Unknown'
			if ex is None:
				ex = exc
		finally:
			log.info(f"Attribute operation='{self.operation}'")
			u_log.debug(f"{str('SN=' + serial_number_string).ljust(13)}|INFO|Operation={self.operation}")

		try:
			self.operator = self.Operator.from_username(data[0].Operator)
			operator_string = str(self.operator.username)
		except Exception as exc:
			self.operator = str(data[0].Operator)
			if not self.operator:
				self.operator = 'Unknown'
			operator_string = self.operator
			if ex is None:
				ex = exc
		finally:
			log.info(f"Attribute operator='{operator_string}'")
			u_log.debug(f"{str('SN=' + serial_number_string).ljust(13)}|INFO|Operator={operator_string}")

		try:
			self.is_cellular = self.build.cellular
		except Exception as exc:
			self.is_cellular = 'Unknown'
			if ex is None:
				ex = exc
		finally:
			log.info(f"Attribute is_cellular={self.is_cellular}")

		try:
			self.datetime = data[0].DateTime
			datetime_str = self.datetime.strftime('%m/%d/%Y %H:%M:%S')
		except Exception as exc:
			self.datetime = datetime.datetime(1900, 1, 1)
			datetime_str = self.datetime.strftime('%m/%d/%Y %H:%M:%S')
			if ex is None:
				ex = exc
		finally:
			log.info(f"Attribute datetime='{datetime_str}'")
			u_log.debug(f"{str('SN=' + serial_number_string).ljust(13)}|INFO|DateTime={datetime_str}")

		try:
			self.notes = data[0].Notes
		except Exception as exc:
			self.notes = 'Unknown'
			if ex is None:
				ex = exc
		finally:
			log.info(f"Attribute notes='{self.notes}'")
			u_log.debug(f"{str('SN=' + serial_number_string).ljust(13)}|INFO|Notes={self.notes}")

		try:
			self.status = data[0].Status
		except Exception as exc:
			self.status = 'Unknown'
			if ex is None:
				ex = exc
		finally:
			log.info(f"Attribute status='{self.status}'")
			u_log.debug(f"{str('SN=' + serial_number_string).ljust(13)}|INFO|Status={self.status}")

		self.parts_transacted = set()

		try:
			self.eff_date = self.get_eff_date(self.serial_number)
			if self.eff_date is None:
				raise NoSROError(serial_number=serial_number_string)
			eff_date_str = self.eff_date.strftime('%m/%d/%Y')
		except Exception as exc:
			self.eff_date = datetime.datetime(1900, 1, 1)
			eff_date_str = self.eff_date.strftime('%m/%d/%Y')
			if ex is None:
				ex = exc
		finally:
			log.info(f"Attribute eff_date={eff_date_str}")
			u_log.debug(f"{str('SN=' + serial_number_string).ljust(13)}|INFO|Eff Date={eff_date_str}")

		try:
			self.sro_open_status = self.get_statuses(self.serial_number)
			if self.sro_open_status is None:
				raise NoSROError(serial_number=serial_number_string)
		except Exception as exc:
			self.sro_open_status = {'Lines': 'Unknown', 'Operations': 'Unknown'}
			if ex is None:
				ex = exc
		finally:
			log.info(f"Attribute sro_open_status={self.sro_open_status}")
			u_log.debug(f"{str('SN=' + serial_number_string).ljust(13)}|INFO|SRO Lines Status Open={self.sro_open_status['Lines']}")
			u_log.debug(f"{str('SN=' + serial_number_string).ljust(13)}|INFO|SRO Operations Status Open={self.sro_open_status['Operations']}")

		# if not self.sro_open_status['Lines']:
		# 	raise NoOpenSROError(serial_number=self.serial_number.number, sro=self.sro)

		try:
			self.location = self.get_location(self.serial_number)
		except Exception as exc:
			self.location = 'Unknown'
			if ex is None:
				ex = exc
		finally:
			log.info(f"Attribute location='{self.location}'")
			u_log.debug(f"{str('SN=' + serial_number_string).ljust(13)}|INFO|Location={self.location}")

		try:
			self.warehouse = self.get_warehouse(self.serial_number)
		except Exception as exc:
			self.warehouse = 'Unknown'
			if ex is None:
				ex = exc
		finally:
			log.info(f"Attribute warehouse='{self.warehouse}'")
			u_log.debug(f"{str('SN=' + serial_number_string).ljust(13)}|INFO|Warehouse={self.warehouse}")

		try:
			self.passed_QC = self.has_passed_qc(self.serial_number)
		except Exception as exc:
			self.passed_QC = 'Unknown'
			if ex is None:
				ex = exc
		finally:
			log.info(f"Attribute passed_QC={self.passed_QC}")

		try:
			self.oldest_datetime = self.get_oldest_datetime(self.serial_number)
		except Exception as exc:
			self.oldest_datetime = datetime.datetime(1900, 1, 1)
			if ex is None:
				ex = exc
		finally:
			log.info(f"Attribute oldest_datetime={self.oldest_datetime}")

		try:
			self.newest_datetime = self.get_newest_datetime(self.serial_number)
		except Exception as exc:
			self.newest_datetime = datetime.datetime(1900, 1, 1)
			if ex is None:
				ex = exc
		finally:
			log.info(f"Attribute newest_datetime={self.newest_datetime}")

		self.batch_amt_default = 1

		self.closed_sros = 0
		self.sro = '?'

		self.sro_operations_time = 0
		self.sro_transactions_time = 0
		self.misc_issue_time = 0
		self.extra_sro_time = 0

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
		# FIXME: Only if no other reason codes have been entered
		# FIXME: AND Clean this up
		m = REGEX_RESOLUTION.fullmatch(str(self.notes))
		# if m:
		# 	self.general_reason = 1000
		# 	self.specific_reason = 20
		# 	self.general_resolution, self.specific_resolution = [int(x) for x in m.groups()]
		# 	if self.general_resolution == 10000 and self.specific_resolution == 100:
		# 		self.general_resolution_name = 'Pass'
		# 	else:
		# 		res = mssql.execute("""SELECT TOP 1 Failure FROM FailuresRepairs WHERE ReasonCodes = %s""", str(self.notes))
		# 		if res:
		# 			self.general_resolution_name = res[0].Failure
		# 			if self.status == 'Scrap':
		# 				self.specific_resolution_name = self.status.upper()
		# 		else:
		# 			raise InvalidReasonCodeError(reason_code=str(self.notes), spec_id=str(self.ID))
		# elif self.status == 'Queued':
		# 	self.general_reason = 1000
		# 	self.specific_reason = 20
		# 	self.general_resolution = 10000
		# 	self.specific_resolution = 100
		# elif not self.notes:  # Because HomeGuard -_-
		# 	self.general_resolution = None
		# 	self.specific_resolution = None
		# 	self.general_resolution_name = None
		# else:
		# 	raise InvalidReasonCodeError(reason_code=str(self.notes), spec_id=str(self.ID))
		if ex:
			raise ex
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

	def __init_subclass__(cls, **kwargs):
		cls.completion_string = kwargs.get('completion_string', None)
		cls.status_string = kwargs.get('status_string', None)
		return cls

	@classmethod
	def from_serial_number(cls, serial_number: Union[str, SerialNumber], status: str=None):
		if not status:
			status = cls.status_string
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
		eff_date1 = slsql.execute("""SELECT TOP 1 c.eff_date AS 'Eff Date'
FROM fs_sro s ( NOLOCK )
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
		if eff_date1:
			eff_date2 = slsql.execute("""SELECT TOP 1 c.eff_date AS 'Eff Date'
			FROM fs_sro s ( NOLOCK )
				INNER JOIN fs_sro_line t ( NOLOCK )
					ON s.sro_num = t.sro_num
				INNER JOIN fs_unit_cons c ( NOLOCK )
					ON t.ser_num = c.ser_num
				INNER JOIN fs_sro_oper o ( NOLOCK )
					ON t.sro_num = o.sro_num AND t.sro_line = o.sro_line
			WHERE c.eff_date < %d AND
			      t.ser_num = %s
			ORDER BY s.open_date DESC""", (self.datetime.date(), serial_number))
			if eff_date2:
				if eff_date2[0].Eff_Date < self.datetime < eff_date1[0].Eff_Date:
					return eff_date2[0].Eff_Date.date()
			return eff_date1[0].Eff_Date.date()
		else:
			return None

	def get_oldest_datetime(self, serial_number: SerialNumber = None) -> datetime.datetime:
		if serial_number is None:
			serial_number = self.serial_number
		eff_date = self.eff_date_backstep(self.eff_date)
		oldest_datetime = mssql.execute("""SELECT MIN(DateTime) AS DateTime FROM PyComm WHERE [Serial Number] = %s AND DateTime >= %d""", (serial_number.number, eff_date))
		if oldest_datetime:
			return oldest_datetime[0].DateTime
		#
		else:
			return None

	def get_newest_datetime(self, serial_number: SerialNumber = None) -> datetime.datetime:
		if serial_number is None:
			serial_number = self.serial_number
		eff_date = self.eff_date_backstep(self.eff_date)
		newest_datetime = mssql.execute("""SELECT MAX(DateTime) AS DateTime FROM PyComm WHERE [Serial Number] = %s AND DateTime >= %d""", (serial_number.number, eff_date))
		if newest_datetime:
			return newest_datetime[0].DateTime
		else:
			return None

	def has_passed_qc(self, serial_number: SerialNumber = None) -> bool:
		if serial_number is None:
			serial_number = self.serial_number
		eff_date = self.eff_date_backstep(self.eff_date)
		operations = mssql.execute("""SELECT DISTINCT Operation AS Operation FROM PyComm WHERE [Serial Number] = %s AND DateTime >= %d""", (serial_number.number, eff_date))
		if operations:
			return any(op.Operation == 'QC' for op in operations)
		else:
			return False

	def get_rogue_sros(self) -> List[Dict[str, Any]]:
		serial_number = self.serial_number
		results = slsql.execute("""SELECT o.sro_num AS sro_num, o.sro_line AS sro_line, o.stat AS status, o.Open_date AS open_date 
FROM fs_sro_oper o ( NOLOCK )
INNER JOIN fs_sro_serial s ( NOLOCK )
ON o.sro_line = s.sro_line AND o.sro_num = s.sro_num
WHERE s.ser_num = %s AND o.stat = 'O'
ORDER BY o.open_date DESC
""", serial_number)
		# Why open_date?
		if results:
			return [{'sro': res.sro_num, 'line': res.sro_line, 'status': res.status, 'open_date': res.open_date} for res in results if (res.sro_num != self.sro) and (res.sro_line != self.sro_line)]
		else:
			return []

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
		life_time = self.life_timer.stop()
		if isinstance(self.parts, str):
			parts_count = self.parts.count(',')
		else:
			parts_count = len(self.parts)
		parts_transacted_count = len(self.parts_transacted)
		if self.parts and not isinstance(self.parts, str):
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
		if isinstance(self.build, str):
			carrier_str = '-'
		else:
			carrier_str = self.build.carrier[0].upper() if self.build.carrier is not None else '-'
		if isinstance(self.serial_number, str):
			serial_number_string = str(self.serial_number)
		else:
			serial_number_string = self.serial_number.number
		if isinstance(self.build, str):
			build_core_string = str(self.build)
			build_type_string = str(self.build)
		else:
			build_core_string = self.build.core
			build_type_string = self.build.type
		if isinstance(self.operator, str):
			operator_string = str(self.operator)
		else:
			operator_string = self.operator.username

		log.debug((serial_number_string, carrier_str, build_core_string, build_type_string, operator_string, str(self.operation), parts_string, parts_transacted_string,
		           parts_count, parts_transacted_count, self.datetime.strftime('%m/%d/%Y %H:%M:%S'), self.start_date, self.start_time, self.sro_operations_time,
		           self.sro_transactions_time, self.misc_issue_time, end_time, life_time, process, results, reason, version))
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
[SROs Closed], 
[Input DateTime], 
Date, 
[Start Time], 
[SRO Operations Time], 
[SRO Transactions Time], 
[Misc Issue Time], 
[Extra SROs Time], 
[End Time], 
[Total Time], 
Process, 
Results, 
Reason,
Version
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %d, %d, %d, %s, %s, %s, %d, %d, %d, %d, %s, %d, %s, %s, %s, %s)""",
		              (serial_number_string, carrier_str, build_core_string, build_type_string, operator_string, str(self.operation), parts_string, parts_transacted_string,
		               parts_count, parts_transacted_count, self.closed_sros, self.datetime.strftime('%m/%d/%Y %H:%M:%S'), self.start_date, self.start_time, self.sro_operations_time,
		               self.sro_transactions_time, self.misc_issue_time, self.extra_sro_time, end_time, life_time, process, results, reason, version))

	def complete(self, *, batch_amt: int = None):
		if self.completion_string:
			completion_string = self.completion_string
		else:
			completion_string = completion_dict[self.status]
		self.end(results='Completed', reason='None', batch_amt=batch_amt)
		mssql.execute("""UPDATE PyComm
SET Status = %s
WHERE Id = %d""", (completion_string, self.ID))

	@singledispatch
	def skip(self, reason=None, *, batch_amt: int = None):
		try:
			reason = reason.status
			if hasattr(reason, 'spec_id'):
				if reason.spec_id != self.ID:
					raise AttributeError
		except AttributeError:
			reason = 'Skipped'
		addon = f"({self.sro})" if reason == 'No Open SRO' else ""
		self.end(results='Skipped', reason=reason, batch_amt=batch_amt)
		status_string = f"{reason}({self.status}){addon}"
		mssql.execute("""UPDATE PyComm SET Status = %s WHERE Id = %d""", (status_string, self.ID))

	@skip.register(str)
	def _(self, reason: str = None, *, batch_amt: int = None):
		reason = 'Skipped' if reason is None else reason
		addon = f"({self.sro})" if reason == 'No Open SRO' else ""
		self.end(results='Skipped', reason=reason, batch_amt=batch_amt)
		status_string = f"{reason}({self.status}){addon}"
		mssql.execute("""UPDATE PyComm SET Status = %s WHERE Id = %d""", (status_string, self.ID))

	@skip.register(BI_EntryError)
	def _(self, reason: BI_EntryError = None, *, batch_amt: int = None):
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

	def eff_date_backstep(self, eff_date: datetime.date = None) -> datetime.date:
		if eff_date is None:
			eff_date = self.eff_date
		eff_date -= datetime.timedelta(1)
		if eff_date.weekday() > 4:
			eff_date -= datetime.timedelta(eff_date.weekday() - 4)
		return eff_date


__all__ = ['Unit']
