import datetime


class Warn(Warning):
	def __init__(self, data):
		self.debug_data = data
		self.data = data


class SROClosedWarning(Warn):
	def __init__(self, data):
		super().__init__(data)


class PopupWarning(Warn):
	def __init__(self, data):
		super().__init__(data)


# ----------------------------------------------------

class Error(Exception):
	def __init__(self, data, message):
		self.debug_data = data
		self.message = message
		self.timestamp = datetime.datetime.now()


class UnitClosedError(Error):
	def __init__(self, data, message: str=None):
		super().__init__(data, message)


class InvalidSerialNumberError(Error):
	def __init__(self, data, message: str=None):
		super().__init__(data, message)


class InvalidPartNumberError(Error):
	def __init__(self, data, message: str=None):
		super().__init__(data, message)


class InvalidReasonCodeError(Error):
	def __init__(self, data, message: str=None):
		super().__init__(data, message)


class SyteLineError(Error):
	def __init__(self, data, message):
		super().__init__(data, message)


class SyteLineFormContainerError(SyteLineError):
	def __init__(self, data, message: str=None):
		super().__init__(data, message)



class SyteLineLogInError(SyteLineError):
	def __init__(self, data, message: str=None):
		super().__init__(data, message)
