class BI_EntryWarning(Warning):
	"""Base warning class. All other warnings inherit
	from this one.
	"""

	def __init__(self, msg=""):
		Warning.__init__(self, msg)
		self.msg = msg

	def __repr__(self):
		ret = "%s.%s %s" % (self.__class__.__module__,
		                    self.__class__.__name__, self.msg)
		return ret.strip()

	__str__ = __repr__


class BI_EntryError(Exception):
	"""Base exception class. All other exceptions inherit
	from this one.
	"""

	def __init__(self, msg=""):
		Exception.__init__(self, msg)
		self.msg = msg

	def __repr__(self):
		ret = "%s.%s %s" % (self.__class__.__module__,
		                    self.__class__.__name__, self.msg)
		return ret.strip()

	__str__ = __repr__


# General/Input-caused error - - - - - - - - - - - - - -
class NoSROError(BI_EntryError):
	def __init__(self, serial_number: str, msg=""):
		msg2 = f"No SROs exist for unit '{serial_number}'"
		super().__init__("%s\n%s" % (msg2, msg))
		self.serial_number = serial_number


class NoOpenSROError(BI_EntryError):
	def __init__(self, serial_number: str, sro: str, msg=""):
		msg2 = f"No SROs are open at the Line-level for unit '{serial_number}'"
		super().__init__("%s\n%s" % (msg2, msg))
		self.serial_number = serial_number
		self.sro = sro


class InvalidSerialNumberError(BI_EntryError, ValueError):
	def __init__(self, serial_number: str, msg=""):
		msg2 = f"'{serial_number}' is not a valid serial number"
		ValueError.__init__(self, "%s\n%s" % (msg2, msg))
		self.serial_number = serial_number


class InvalidSROError(BI_EntryError, ValueError):
	def __init__(self, serial_number: str, sro: str, msg=""):
		msg2 = f"'{sro}' is not a valid SRO for unit '{serial_number}'"
		ValueError.__init__(self, "%s\n%s" % (msg2, msg))
		self.sro = sro


class InvalidPartNumberError(BI_EntryError, ValueError):
	def __init__(self, part_number: str, msg=""):
		msg2 = f"'{part_number}' is not a valid part number"
		ValueError.__init__(self, "%s\n%s" % (msg2, msg))
		self.part_number = part_number


class InvalidReasonCodeError(BI_EntryError, ValueError):
	def __init__(self, reason_code: str, spec_id: str, msg=""):
		msg2 = f"'{reason_code}' is not a valid reason code"
		ValueError.__init__(self, "%s\n%s" % (msg2, msg))
		self.reason_code = reason_code
		self.spec_id = spec_id


# - - - - - - - - - - - - - - - - - - - - - - - -


# SQL-caused error  - - - - - - - - - - - - - - -
class SQLError(BI_EntryError):
	def __init__(self, msg=""):
		msg2 = ""
		super().__init__("%s\n%s" % (msg2, msg))


class SQLConnectionError(SQLError, ConnectionError):
	def __init__(self, msg=""):
		msg2 = f"Connection to SQL server failed"
		ConnectionError.__init__(self, "%s\n%s" % (msg2, msg))


class SQLSyntaxError(SQLError, SyntaxError):
	def __init__(self, cmd: str, msg=""):
		msg2 = f"Invalid SQL command syntax for command '{cmd}'"
		ConnectionError.__init__(self, "%s\n%s" % (msg2, msg))


class SQLValueError(SQLError, ValueError):
	def __init__(self, value, cmd: str, msg=""):
		msg2 = f"'{value}' is not a valid value for SQL command '{cmd}'"
		ValueError.__init__(self, "%s\n%s" % (msg2, msg))


class SQLResultError(SQLError, ValueError):
	def __init__(self, cmd: str, msg=""):
		msg2 = f"Invalid response from query '{cmd}'"
		ValueError.__init__(self, "%s\n%s" % (msg2, msg))


# - - - - - - - - - - - - - - - - - - - - - - - -


# SyteLine-caused error - - - - - - - - - - - - -
class SyteLineError(BI_EntryError):
	def __init__(self, msg=""):
		msg2 = ""
		super().__init__("%s\n%s" % (msg2, msg))


class SyteLineFilterInPlaceError(SyteLineError):
	def __init__(self, value, msg=""):
		msg2 = f"'Filter In Place' failed for value '{value}'"
		super().__init__("%s\n%s" % (msg2, msg))


class SyteLineFormError(SyteLineError):
	def __init__(self, form: str, msg=""):
		msg2 = f"Form '{form}' not responding"
		super().__init__("%s\n%s" % (msg2, msg))
		self.form = form


class SyteLineLogInError(SyteLineError):
	def __init__(self, usr: str, msg=""):
		msg2 = f"Login failed for user '{usr}'"
		super().__init__("%s\n%s" % (msg2, msg))


class SyteLineCreditHoldError(SyteLineError):
	def __init__(self, cust: str, msg=""):
		msg2 = f"Customer '{cust}' on credit hold"
		# self._cust = cust
		super().__init__("%s\n%s" % (msg2, msg))


class NegativeQuantityWarning(BI_EntryWarning):
	def __init__(self, part: str, qty: int, loc: str, msg=""):
		msg2 = f"Quantity for part '{part}' = -{qty}.000 in location '{loc}'"
		super().__init__("%s\n%s" % (msg2, msg))

# - - - - - - - - - - - - - - - - - - - - - - - -
