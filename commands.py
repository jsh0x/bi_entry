import os
import subprocess

import logging
from typing import Union, Iterable, Dict, Any, Tuple, List
from time import sleep

import win32gui
import win32api
import numpy as np
import pywinauto as pwn
from exceptions import *
from controls import Button
from forms import UnitsForm, ServiceOrderLinesForm, ServiceOrderOperationsForm, SROTransactionsForm
import shelve

# Initial variables
screen_width = win32api.GetSystemMetrics(0)
screen_height = win32api.GetSystemMetrics(1)
log = logging.getLogger('devLog')
pfx_dict = {'11': 'OT', '13': 'LC', '40': 'SL', '21': 'SL', '63': 'BE', '48': 'LCB'}
_form_dict = {'UnitsForm': UnitsForm, 'ServiceOrderLinesForm': ServiceOrderLinesForm,
             'ServiceOrderOperationsForm': ServiceOrderOperationsForm, 'SROTransactionsForm': SROTransactionsForm}
#hwnd = win32gui.GetForegroundWindow()
#win32gui.MoveWindow(hwnd, 0, 0, np.floor_divide(screen_width, 2), np.floor_divide(screen_height, 2), True)

# SQL Connect

file_list = os.listdir(os.getcwd())
if 'dev.key' in file_list:
	dev_mode = True
else:
	dev_mode = False


def move_and_resize(corner: str, total_screens: int=1, spec_screen: int=None):
	hwnd = win32gui.GetForegroundWindow()
	if total_screens > 1:
		pass
	else:
		if corner == 'tl':
			win32gui.MoveWindow(hwnd, 0, 0, np.floor_divide(screen_width, 2), np.floor_divide(screen_height, 2), True)
		elif corner == 'tr':
			win32gui.MoveWindow(hwnd, np.floor_divide(screen_width, 2), 0, np.floor_divide(screen_width, 2), np.floor_divide(screen_height, 2), True)
		elif corner == 'bl':
			win32gui.MoveWindow(hwnd, 0, np.floor_divide(screen_width, 2), np.floor_divide(screen_width, 2), np.floor_divide(screen_height, 2), True)
		elif corner == 'br':
			win32gui.MoveWindow(hwnd, np.floor_divide(screen_width, 2), np.floor_divide(screen_height, 2), np.floor_divide(screen_width, 2), np.floor_divide(screen_height, 2), True)


class Application(subprocess.Popen):
	def __init__(self, args: Iterable[Union[bytes, str]]):
		super().__init__(args)
		log.debug("Application initialization started")
		self.app_win32 = pwn.Application(backend='win32').connect(process=self.pid)
		self.app_uia = pwn.Application(backend='uia').connect(process=self.pid)
		self._sign_in = self.app_win32['Sign In']
		self._win2 = self.app_uia.window(title_re='Infor ERP SL (EM)*', auto_id="WinStudioMainWindow", control_type="Window")
		self._win = self.app_win32.window(title_re='Infor ERP SL (EM)*')
		self._all_win = {'win32': self._win, 'uia': self._win2}
		self.popup = self.app_win32['Infor ERP SL']
		self._error = self.app_win32['Error']
		self._forms = []
		self.logged_in = False
		self.log_in = self._log_in
		#self.db = shelve.open('forms')
		log.debug("Application initialization successful")

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		if self.stdout:
			self.stdout.close()
		if self.stderr:
			self.stderr.close()
		try:  # Flushing a BufferedWriter may raise an error
			if self.stdin:
				self.stdin.close()
		finally:
			# self.wait()
			self.kill()

	def _log_in(self, username: str=None, password: str=None):
		log.debug("Attempting log in")
		user_textbox = self._sign_in['Edit3']
		password_textbox = self._sign_in['Edit2']
		ok_button = self._sign_in['&OKButton']
		self._sign_in.set_focus()
		user_textbox.SetEditText(username)
		password_textbox.SetEditText(password)
		ok_button.Click()
		log.debug("Logging in")
		if self._error.exists():
				message = self._error.Static2.texts()[0]
				# Redo in regex
				if ('count limit' in message) and ('exceeded' in message):
					self._error.OKButton.Click()
		while self.popup.exists():
			message2 = self.popup.Static2.texts()[0]
			if (f"session for user '{username}'" in message2) and ('already exists' in message2):
				if dev_mode:
					self.popup['&YesButton'].Click()
				else:
					self.popup['&NoButton'].Click()
					raise SyteLineLogInError("Failed to log in")
			elif ('Exception initializing form' in message2) and ('executable file vbc.exe cannot be found' in message2):
				self.popup.OKButton.Click()
				raise SyteLineFormContainerError("SyteLine window's form container is corrupt/non-existent")
			sleep(2)
		log.debug("Log in successful")
		self.wait('ready')
		self.logged_in = True
		self.open_form = Button(window=self._all_win, criteria={'best_match': 'Open a formButton'}, preinit=False)
		self.save = Button(window=self._all_win, criteria={'best_match': 'SaveButton'}, preinit=False)
		self.cancel_close = Button(window=self._all_win, criteria={'best_match': 'Cancel CloseButton'}, preinit=False)
		self.save_close = Button(window=self._all_win, criteria={'best_match': 'Save CloseButton'}, preinit=False)
		self.apply_filter = Button(window=self._all_win, criteria={'best_match': 'FiPButton'}, preinit=False)
		self.refresh_filter = Button(window=self._all_win, criteria={'best_match': 'RefreshButton'}, preinit=False)
		self.reload_filter = Button(window=self._all_win, criteria={'best_match': 'Refresh currentButton'}, preinit=False)
		self.add_form = self._add_form
		self.remove_form = self._remove_form
		self.log_out = self._log_out
		self.__delattr__('log_in')

	def _log_out(self, force_quit=True):
		if force_quit:
			self._win.SignOut.select()
		else:
			# Close out each individual open form properly
			pass
		self.logged_in = False
		for form in self._forms:
			self.__delattr__(form)
		self._forms.clear()
		self.__delattr__('open_form')
		self.__delattr__('cancel_close')
		self.__delattr__('save_close')
		self.__delattr__('apply_filter')
		self.__delattr__('refresh_filter')
		self.__delattr__('reload_filter')
		self.__delattr__('add_form')
		self.__delattr__('remove_form')
		self.__delattr__('log_out')
		self.log_in = self._log_in

	def _add_form(self, name: str, preinit=False):
		log.debug(f"Attempting to add form '{name}'")
		self.__setattr__(name, _form_dict[name](self._all_win, preinit))

	def _remove_form(self, name: str):
		log.debug(f"Attempting to remove form '{name}'")
		if hasattr(self, name):
			pass
		else:
			log.warning(f"Failed to remove form '{name}', it does not exist")
	"""retval = {}
		try:
			self._forms = self._win.window(class_name_re='.*MDICLIENT*').children()
		except AttributeError:
			raise SyteLineFormContainerError("SyteLine window's form container is corrupt/non-existent")
		else:
			for form in self._forms:
				form_text = (form.texts()[0]).strip(' ')
				if (form_text == 'Units') or (form_text == 'Units (Filter In Place)'):
					retval['Units'] = UnitsForm(self._all_win)
				elif (form.texts()[0] == 'Service Order Lines') or (form.texts()[0] == 'Service Order Lines (Linked)'):
					retval['Service Order Lines'] = ServiceOrderLinesForm(self._all_win)
				elif (form.texts()[0] == 'Service Order Operations') or (form.texts()[0] == 'Service Order Operations (Linked)'):
					retval['Service Order Operations'] = ServiceOrderOperationsForm(self._all_win)
				elif form.texts()[0] == 'SRO Transactions':
					retval['SRO Transactions'] = SROTransactionsForm(self._all_win)
		return retval"""

	def wait(self, _type: str):
		self._win.wait(_type)
		self._win2.wait(_type)

'''class Unit:
	def __init__(self, app: cmd.Application, open_forms: List[str]=None):
		self.app = app
		self.open_forms = open_forms
		if not open_forms:
			self.open_forms = []

	@property
	def current_form(self):
		if self.open_forms:
			return self.open_forms[0]
		else:
			return None

	@property
	def _current_form(self):
		if self.current_form:
			return self.app.forms[self.current_form]
		else:
			return None

	def _open_form(self, name:str):
		try:
			self.app.open_forms(name)
		except Exception as ex:
			print(ex)
		else:
			self.open_forms = [name] + self.open_forms'''
'''class UnitObject(Unit):
	def __init__(self, unit_data: LabeledDataRow, app: cmd.Application, open_forms: List[str]=None):
		super().__init__(app, open_forms)
		self.serial_number = unit_data['Serial Number']
		self.build = unit_data['Build']
		self.suffix = unit_data['Suffix']
		self.operation = unit_data['Operation']
		self.operator = unit_data['Operator']
		self.parts = unit_data['Parts']
		self.datetime = unit_data['DateTime']
		self.notes = unit_data['Notes']
		"""self.status = str(unit_data['Status'])"""

	###
	@property
	def serial_number(self):
		return self._serial_number
	@serial_number.setter
	def serial_number(self, value):
		# verify serial number
		self._serial_number = pfx_dict[(str(value)[:2])] + str(value)

	@property
	def build(self):
		return self._build
	@build.setter
	def build(self, value):
		# verify build
		self._build = str(value)

	@property
	def suffix(self):
		return self._suffix
	@suffix.setter
	def suffix(self, value):
		# verify suffix
		self._suffix = str(value)

	@property
	def operation(self):
		return self._operation
	@operation.setter
	def operation(self, value):
		# verify operation
		self._operation = str(value)

	@property
	def operator(self):
		return self._operator
	@operator.setter
	def operator(self, value):
		# verify operator
		self._operator = str(value)

	@property
	def parts(self):
		return self._parts
	@parts.setter
	def parts(self, value):
		# verify parts
		retval = []
		value = str(value)
		check_string = len(value) - 12
		if (check_string == 0) or (np.remainder(check_string, 13) == 0):
			part_list = value.split(',')
			for part in part_list:
				if len(part) == 12:
					retval.append(Part(part))
		if retval:
			self._parts = tuple(retval)
		else:
			self._parts = None

	@property
	def datetime(self):
		return self._datetime
	@datetime.setter
	def datetime(self, value):
		# verify datetime
		if type(value) is datetime.datetime:
			self._datetime = value
		elif type(value) is str:
			fmt = "%m/%d/%Y %I:%M:%S %p"
			self._datetime = datetime.datetime.strptime(value, fmt)


	@property
	def notes(self):
		return self._notes
	@notes.setter
	def notes(self, value):
		# verify notes
		self._notes = str(value)
	###

	def _Units_to_Service_Order_Lines(self):
		if self.current_form == 'Units':
			self.app.forms['Units'].service_order_lines.click(wait_string='form')
			self.open_forms = ['Service Order Lines'] + self.open_forms
			self.app.add_form('Service Order Lines')

	def _Service_Order_Lines_to_Service_Order_Operations(self):
		self.app.forms['Service Order Lines'].sro_operations.click(wait_string='form')
		self.open_forms = ['Service Order Operations'] + self.open_forms
		self.app.add_form('Service Order Operations')

	def _Service_Order_Operations_to_SRO_Transactions(self):
		self.app.forms['Service Order Operations'].sro_transactions.click(wait_string='form')
		self.open_forms = ['SRO Transactions'] + self.open_forms
		self.app.add_form('SRO Transactions')

	def goto(self, start: str, end: str):
		# TODO: Mapping from start form -> end form
		if start == 'Units':
			if end == 'SRO Transactions'\
			or end == 'Service Order Operations' \
			or end == 'Service Order Lines':
				self._Units_to_Service_Order_Lines()
			if end == 'SRO Transactions'\
			or end == 'Service Order Operations':
				self._Service_Order_Lines_to_Service_Order_Operations()
			if end == 'SRO Transactions':
				self._Service_Order_Operations_to_SRO_Transactions()
		elif start == 'Service Order Lines':
			if end == 'SRO Transactions'\
			or end == 'Service Order Operations':
				self._Service_Order_Lines_to_Service_Order_Operations()
			if end == 'SRO Transactions':
				self._Service_Order_Operations_to_SRO_Transactions()
		elif start == 'Service Order Operations':
			if end == 'SRO Transactions':
				self._Service_Order_Operations_to_SRO_Transactions()

	def go_back(self, name: str):
		presses = self.open_forms.index(name)
		self.app.cancel_close.click(presses)

	def open_unit(self):
		self.app.add_form('Units')
		if self.current_form != 'Units':
			self._open_form('Units')
		self.app.forms['Units'].serial_number = self.serial_number
		self.app.apply_filter()

	def transact_parts(self):
		if self.current_form != 'SRO Transactions':
			raise SyteLineError

	def check_SROs(self, column: str, value, max_results: int=3, max_rows: int=None) -> List[int]:
		if self.current_form != 'Units':
			raise SyteLineError
		self.app.forms['Units'].service_history_tab.select()
		rows = []
		if not max_rows:
			max_rows = self.app.forms['Units'].service_history_tab.grid.rows
		self.app.forms['Units'].service_history_tab.grid.populate_grid(columns=column, rows=range(1, max_rows+1))
		for i in range(1, max_rows+1):
			self.app.forms['Units'].service_history_tab.grid.select_cell(column=column, row=i)
			data = self.app.forms['Units'].service_history_tab.grid.cell
			if data == value:
				rows.append(i)
			if len(rows) >= max_results:
				break
		return rows

	def open_SRO(self, sro_row: int):
		self.app.forms['Units'].service_history_tab.select()
		self.app.forms['Units'].service_history_tab.grid.select_row(sro_row)
		self.app.forms['Units'].service_history_tab.view.click(wait_string=None)
		self.app.add_form('Service Order Lines')
		self.open_forms = ['Service Order Lines'] + self.open_forms
		self.app.forms['Service Order Lines'].sro_operations.ready()

	def check_status(self, form: str) -> str:
		#try:
		retval = self.app.forms[form].status
		# except Exception as ex:
		# 	print(ex)
		# else:
		return retval

	def get_dates(self) -> Date_Dict:
		if self.current_form != 'Service Order Operations':
			raise SyteLineError
		self.app.forms['Service Order Operations'].general_tab.select()
		rc_d = self.app.forms['Service Order Operations'].general_tab.received_date.text()
		fl_d = self.app.forms['Service Order Operations'].general_tab.floor_date.text()
		fa_d = self.app.forms['Service Order Operations'].general_tab.fa_date.text()
		cp_d = self.app.forms['Service Order Operations'].general_tab.complete_date.text()
		return {'received': rc_d, 'floor': fl_d, 'f/a': fa_d, 'complete': cp_d}'''
'''class UnitRequest(Unit):
	def __init__(self, data: str, _type: str, app: cmd.Application, open_forms: List[str]=None):
		super().__init__(app, open_forms)
		if _type == 'serial number':
			self.serial_number = data
			self.esn = None
		elif _type == 'esn':
			self.serial_number = None
			self.esn = data
		self.item = None
		self.build = None
		self.carrier = None
		self.suffix = None
		self._type = _type

	@property
	def item(self):
		if not self._item:
			self._item = self.app.forms['Units'].item.text()
		return self._item

	@item.setter
	def item(self, value):
		self._item = value

	@property
	def esn(self):
		if not self._esn:
			self._esn = self.app.forms['Units'].unit_data_tab.esn.text()
		return self._esn

	@esn.setter
	def esn(self, value):
		self._esn = value

	@property
	def serial_number(self):
		if not self._serial_number:
			value = self.app.forms['Units'].serial_number
			if value[2] in ascii_letters:
				value = value[3:]
			else:
				value = value[2:]
			self._serial_number = value
		return self._serial_number

	@serial_number.setter
	def serial_number(self, value):
		# verify serial number
		if not value:
			self._serial_number = value
		else:
			self._serial_number = pfx_dict[(str(value)[:2])] + str(value)

	@property
	def build(self):
		if not self._build:
			over = self.item.split('-', 2)
			value = self.item.split('-', 2)[1]
			if value[-1:] == 'V':
				value = value[:-1]
			elif value[-1:] == 'S':
				value = value[:-1]
			if len(over) == 3:
				value = f"{over[0]}-{value}-{over[2]}"
			else:
				value = f"{over[0]}-{value}"
			self._build = value
		return self._build

	@build.setter
	def build(self, value):
		self._build = value

	@property
	def carrier(self):
		if not self._carrier:
			value = self.item.split('-', 2)[1]
			if value.endswith('V'):
				self._carrier = 'Verizon'
			elif value.endswith('S'):
				self._carrier = 'Sprint'
			else:
				self._carrier = 'None'
			return self._carrier

	@carrier.setter
	def carrier(self, value):
		self._carrier = value

	@property
	def suffix(self):
		if not self._suffix:
			if self.item.endswith('-M'):
				self._suffix = 'Monitoring'
			elif self.item.endswith('-DEMO'):
				self._suffix = 'Demo'
			elif self.item.endswith('-R'):
				self._suffix = 'Refurb'
			else:
				self._suffix = 'Direct'
		return self._suffix

	@suffix.setter
	def suffix(self, value):
		self._suffix = value

	def open_unit(self):
		self.app.add_form('Units')
		if self.current_form != 'Units':
			self._open_form('Units')
		self.app.forms['Units'].unit_data_tab.select()
		while True:
			if self._type == 'serial number':
				self.app.forms['Units'].serial_number = self.serial_number
			elif self._type == 'esn':
				self.app.forms['Units'].unit_data_tab.esn.set_text(self.esn)
			self.app.apply_filter()
			if self._type == 'serial number':
				if self.app.forms['Units'].serial_number != self.serial_number:
					self.app.apply_filter()
					self.app.refresh_filter()
				elif self.app.forms['Units'].serial_number == self.serial_number:
					break
			elif self._type == 'esn':
				if self.app.forms['Units'].unit_data_tab.esn.text() != self.esn:
					self.app.apply_filter()
					self.app.refresh_filter()
				elif self.app.forms['Units'].unit_data_tab.esn.text() == self.esn:
					break
# Posted, Item, Location, Quantity, Billing Code
# child_window(auto_id="WinStudioMainWindow", control_type="Window")
# child_window(auto_id="Notebook", control_type="Tab")
# child_window(auto_id="ConsumerHistoryGrid", control_type="Table")
# child_window(title_re="Horizontal*", control_type="ScrollBar")
# child_window(title_re="Horizontal*", control_type="ScrollBar")'''
'''def run(unit: UnitObject):
	unit.open_unit()
	unit.app.forms['Units'].owner_history_tab.select()
	unit.app.forms['Units'].owner_history_tab.grid.sort_with_header('Eff Date')
	unit.app.forms['Units'].owner_history_tab.grid.select_cell('Eff Date', 1)
	unit.app.forms['Units'].owner_history_tab.grid.populate_grid(columns='Eff Date', rows=1)
	min_date = unit.app.forms['Units'].owner_history_tab.grid.cell
	sro_list = unit.check_SROs('Close Date', None, max_rows=3)
	for i,row in enumerate(sro_list):
		if True:
			unit.open_SRO(row)
			log.debug(unit.check_status('Service Order Lines'))
			if unit.check_status('Service Order Lines') == "Closed":
				unit.app.cancel_close.click()
				continue
			unit.goto('Service Order Lines', 'Service Order Operations')
			log.debug(unit.check_status('Service Order Operations'))
			if unit.check_status('Service Order Operations') == "Closed":
				unit.app.cancel_close.click()
				unit.app.cancel_close.click()
				continue
			unit.goto('Service Order Operations', 'SRO Transactions')
			# unit.transact_parts()
			# unit.app.save_close.click(2)
			unit.app.cancel_close.click()
			unit.app.cancel_close.click()
			unit.goto('Service Order Lines', 'Service Order Operations')
			dates = unit.get_dates()
			log.debug(dates)
			for k,v in dates.items():
				if k != 'f/a':
					if v:
						log.debug(f"'{k}' datebox has value.")
					else:
						log.debug(f"'{k}' datebox does not have value")
			if not dates['received']:
				unit.app.forms['Service Order Operations'].general_tab.received_date.set_text(min_date.strftime("%m/%d/%Y %I:%M:%S %p"))
			if not dates['floor']:
				date_string = min_date.strftime("%Y-%m-%d 00:00:00")
				value = sql.query(f"SELECT TOP 1 [DateTime] FROM Operations WHERE [DateTime] > CONVERT ( DATETIME , '{date_string}' , 102 ) ORDER BY [DateTime] ASC")
				if not value:
					value = unit.datetime.strftime("%m/%d/%Y %I:%M:%S %p")
				else:
					value = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
					value = value.strftime("%m/%d/%Y %I:%M:%S %p")
				unit.app.forms['Service Order Operations'].general_tab.floor_date = value
			if not dates['complete']:
				value = unit.datetime.strftime("%m/%d/%Y %I:%M:%S %p")
				unit.app.forms['Service Order Operations'].general_tab.complete_date.set_text(value)
			unit.app.forms['Service Order Operations'].reasons_tab.select()

			for i,line in enumerate(unit.app.forms['Service Order Operations'].reasons_tab.reason_notes.texts()):
				log.debug(f"{i}  {line}")
			for i,line in enumerate(unit.app.forms['Service Order Operations'].reasons_tab.resolution_notes.texts()):
				log.debug(f"{i}  {line}")
			break
		# except NameError as ex:
		# 	print("FAILED")
		# 	unit.app.cancel_close.click()
		# 	sleep(0.5)
		# 	unit.app.cancel_close.click()
		# 	print("BACK")
		# 	unit.app.forms['Units'].service_order_lines.ready()
		# 	print("READY")
		# 	continue
		# else:
		# 	break'''
'''def request(unit: UnitRequest):
	unit.open_unit()
	if not unit.item:
		retval = {'serial number': unit.serial_number, 'esn': "No SL Data", 'build': "No SL Data",
		          'carrier': "No SL Data", 'suffix': "No SL Data"}
	else:
		retval = {'serial number': unit.serial_number, 'esn': unit.esn, 'build': unit.build,
		          'carrier': unit.carrier, 'suffix': unit.suffix}
	if retval['serial number'][0] in ascii_letters:
		if retval['serial number'][2] in ascii_letters:
			sn = retval['serial number'][3:]
		else:
			sn = retval['serial number'][2:]
	retval['serial number'] = sn
	return retval'''
'''def request_multi(app):
	row = sql.query("SELECT TOP 1 [Id],[Serial Number] FROM PyComm WHERE [Status] = 'HOLD' ORDER BY [DateTime]")
	if row:
		ID = row['Id']
		sn = row['Serial Number']
		try:
			sn2 = pfx_dict[str(sn)[:2]] + sn
			_type = 'serial number'
		except (ValueError, KeyError):
			_type = 'esn'
		finally:
			print(_type)
			unit = UnitRequest(data=sn, _type=_type, app=app, open_forms=['Units'])
		results = request(unit)
		if _type == 'serial number':
			row = sql.query(f"SELECT * FROM UnitData WHERE [SerialNumber] = '{results['serial number']}'")
			if row:
				sql.modify(f"UPDATE UnitData SET [ItemNumber] = '{results['build']}',[Carrier] = '{results['carrier']}',[Date] = GETDATE(),[Suffix] = '{results['suffix']}', [ESN] = '{results['esn']}',[SyteLineData] = 1 WHERE [SerialNumber] = '{results['serial number']}'")
			else:
				sql.modify(f"INSERT INTO UnitData ([SerialNumber],[ItemNumber],[Carrier],[Date],[Suffix],[ESN],[SyteLineData]) VALUES ('{results['serial number']}','{results['build']}','{results['carrier']}',GETDATE(),'{results['suffix']}','{results['esn']}',1)")
		elif _type == 'esn':
			row = sql.query(f"SELECT * FROM UnitData WHERE [ESN] = '{results['esn']}'")
			if row:
				sql.modify(f"UPDATE UnitData SET [ItemNumber] = '{results['build']}',[Carrier] = '{results['carrier']}',[Date] = GETDATE(),[Suffix] = '{results['suffix']}', [SerialNumber] = '{results['serial number']}',[SyteLineData] = 1 WHERE [ESN] = '{results['esn']}'")
			else:
				sql.modify(f"INSERT INTO UnitData ([SerialNumber],[ItemNumber],[Carrier],[Date],[Suffix],[ESN],[SyteLineData]) VALUES ('{results['serial number']}','{results['build']}','{results['carrier']}',GETDATE(),'{results['suffix']}','{results['esn']}',1)")
		sql.modify(f"DELETE FROM PyComm WHERE [Status] = 'HOLD' AND [Id] = {ID} AND [Serial Number] = '{results['serial number']}'")
	else:
		pass'''
'''def main():
	log.debug("Attempting to read 'config.ini'")
	config.read_file(open('config.ini'))
	usr = 'jredding'
	pwd = 'JRJul17!'
	options = None
	filepath = None
	log.debug("Checking for command arguments")
	if len(sys.argv) > 1:
		log.debug(f"{len(sys.argv[1:])} command arguments found")
		usr = sys.argv[1]
		log.debug(f"Found argument for username: '{usr}'")
		pwd = sys.argv[2]
		log.debug(f"Found argument for password: '{pwd}'")
		for arg in sys.argv[3:]:
			k,v = arg.split('=')
			if k == '/fp':
				filepath = v
				log.debug(f"Found argument for filepath: '{filepath}'")
	if filepath and pathlib.Path(filepath).exists():
		if config.has_section('Paths') and config.has_option('Paths', 'sl_exe'):
			filepath = config.set('Paths', 'sl_exe', filepath)
	else:
		log.debug("No command arguments found")
		filepath = None
	if not filepath:
		log.debug("No 'WinStudio.exe' filepath supplied, defaulting to config")
		if config.has_section('Paths') and config.has_option('Paths', 'sl_exe'):
			filepath = config.get('Paths', 'sl_exe')
			if not pathlib.Path(filepath).exists():
				log.debug(f"Config filepath '{filepath}' does not exist")
				log.debug(f"Checking entire root directory for a 'WinStudio.exe', this may take a while...")
				filepath = find_file('WinStudio.exe')
				if not filepath:
					log.debug("'WinStudio.exe' could not be found")
					raise FileNotFoundError
				else:
					log.debug(f"'WinStudio.exe' found at '{filepath}', setting config to new filepath")
					config.set('Paths', 'sl_exe', filepath)
			else:
				log.debug(f"Filepath set to '{filepath}' base on config")
	with Program(rf"{filepath}") as prog:  # Starts SyteLine
		log.debug('SyteLine started')
		app = cmd.Application(prog.pid)  # Connects to the process
		log.debug('SyteLine application connected')
		if not app.logged_in:  # Logs in
			try:
				app.log_in(usr, pwd)
			except SyteLineLogInError:
				log.exception("Failed to sign in")
				quit()
		# Start-up complete

		while True:
			#try:
			if True:
				#app.close_forms()  # Closes any open forms
				# Hierarchy of units based on suffix. Order: Direct, RTS, Demo, Refurb, Monitoring
				sfx_dict = {'Direct': 1, 'RTS': 2, 'Demo': 3, 'Refurb': 4, 'Monitoring': 5}
				queued = sql.query("SELECT DISTINCT [Suffix] FROM PyComm WHERE [Status] = 'Queued' AND [Operation] <> 'QC'", fetchall=True)
				if not queued:
					queued = sql.query("SELECT DISTINCT [Suffix] FROM PyComm WHERE [Status] = 'Queued' AND [Operation] = 'QC'", fetchall=True)
					if not queued:
						continue
					else:
						queued2 = []
						for q in queued:
							queued2.append(q[0])
						queued = queued2
						sorted_sfx_queue = sorted(queued, key=lambda x: sfx_dict[x])
						unit_data = sql.query(f"SELECT TOP 1 * FROM PyComm WHERE [Suffix] = '{sorted_sfx_queue[0]}' AND [Status] = 'Queued' ORDER BY [DateTime] ASC")
						# QC
						pass
				else:
					queued2 = []
					for q in queued:
						queued2.append(q[0])
					queued = queued2
					sorted_sfx_queue = sorted(queued, key=lambda x: sfx_dict[x])
					unit_data = sql.query(f"SELECT TOP 1 * FROM PyComm WHERE [Suffix] = '{sorted_sfx_queue[0]}' AND [Status] = 'Queued' ORDER BY [DateTime] ASC")
				log.info(f"Unit data found: {unit_data}")
				unit_obj = UnitObject(unit_data, app, ['Units'])
				run(unit_obj)
				sleep(7200)
			"""except Exception as ex:
				log.exception("???")
			else:
				pass
			finally:
				pass"""


__all__ = ['Program', 'UnitObject']'''