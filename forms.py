import datetime
import os
import sys
import logging
from collections import defaultdict
import pywinauto as pwn
from controls import *
from matplotlib import pyplot as plt

log = logging.getLogger('root')


def find_file(name, path="C:/"):
	for root, dirs, files in os.walk(path):
		if name in files:
			return str(os.path.join(root, name)).replace('\\', '/')
	else:
		return None


# issubclass(blah.__class__, Control)


class Form:
	def __init__(self, name: str, text: str):
		self.name = name
		self.text = text
		self._visible = False


class UnitsForm(Form):
	def __init__(self, window, preinit=False):
		log.debug("Initializing 'Units' form")
		super().__init__(name='Units (Filter In Place)', text='Units')
		self.window_uia = window['uia']
		self.window_win32 = window['win32']

		# Define Textboxes
		self._unit = Textbox(window=window, criteria={'best_match': "Unit:Edit"}, fmt=('alphabetic', 'numeric', 'upper'), preinit=preinit, control_name='Unit')
		self.description = Textbox(window=window, criteria={'best_match': "Description:Edit"}, preinit=preinit, control_name='Description')
		self.item = Textbox(window=window, criteria={'best_match': "Item:Edit"}, fmt=('alphabetic', 'numeric', 'punctuation', 'upper'), preinit=preinit, control_name='Item')
		# self.customer_item = Textbox(name='Customer Item:Edit', text='Customer Item', window=window)
		# self.unit_status_code = Textbox(name='Unit Status Code:Edit', text='Unit Status Code', window=window)
		esn = {'class': Textbox, 'kwargs': {'window': window, 'criteria': {'best_match': "ESN:Edit"}, 'fmt': ('alphabetic', 'numeric', 'upper'), 'preinit': preinit, 'control_name': 'ESN'}}

		# Define Buttons
		# self.view_serial_master = Button(name='View Serial &MasterButton', text='View Serial Master', window=window)
		# self.change_status = Button(name='Change StatusButton', text='Change Status', window=window)
		# self.contract_lines = Button(name='Contract LinesButton', text='Contract Lines', window=window)
		# self.incidents = Button(name='IncidentsButton', text='Incidents', window=window)
		# self.unit_configuration = Button(window=window, criteria={'auto_id': "??????", 'control_type': 'Button', 'top_level_only': False})
		self.service_order_lines = Button(window=window, criteria={'auto_id': "SROLinesButton", 'control_type': "Button", 'top_level_only': False}, preinit=preinit, control_name='Service Order Lines')
		view = {'class': Button, 'kwargs': {'window': window, 'criteria': {'auto_id': "BtnSROLineView", 'control_type': "Button", 'top_level_only': False}, 'preinit': preinit, 'control_name': 'View'}}

		# Define Checkboxes
		# self.warranty = Checkbox(name='WarrantyButton', text='Warranty', window=window)

		# Define Grid
		owner_history_grid = {'class': GridView, 'kwargs': {'window': window, 'criteria': {'parent': self.window_uia.child_window(best_match='Alt. 6/7 Digit SN:GroupBox'), 'auto_id': "ConsumerHistoryGrid", 'control_type': "Table", 'top_level_only': False}, 'preinit': preinit, 'control_name': 'Owner History'}}
		service_history_grid = {'class': GridView, 'kwargs': {'window': window, 'criteria': {'parent': self.window_uia.child_window(best_match='Resource:GroupBox'), 'auto_id': "fsTmpSROLineViewsGrid", 'control_type': "Table", 'top_level_only': False}, 'preinit': preinit, 'control_name': 'Service History'}}

		# Define Tabs
		self.owner_history_tab = Tab(window=window, criteria={'best_match': "Owner HistoryTabControl"}, name='Owner History', controls={'grid': owner_history_grid}, preinit=preinit, control_name='Owner History')
		self.service_history_tab = Tab(window=window, criteria={'best_match': "Service HistoryTabControl"}, name='Service History', controls={'grid': service_history_grid, 'view': view}, preinit=preinit, control_name='Service History')
		self.unit_data_tab = Tab(window=window, criteria={'best_match': "UNIT DATATabControl"}, name='UNIT DATA', controls={'esn': esn}, preinit=preinit, control_name='Unit Data')

		log.debug("'Units' form initialized")

	@property
	def serial_number(self):
		return self._unit.text()

	@serial_number.setter
	def serial_number(self, value: str):
		value = str(value)
		if 8 < len(value) < 12:
			self._unit.set_text(value)
		else:
			raise ValueError


class ServiceOrderLinesForm(Form):
	def __init__(self, window, preinit=False):
		log.debug("Initializing 'Service Order Lines' form")
		super().__init__(name='Service Order Lines (Linked)', text='Service Order Lines')

		# Define Textboxes
		# self.unit = Textbox(name='Unit:Edit', text='Unit', window=window)
		# self.line = Textbox(name='Line:Edit1', text='Line', window=window)
		# self.item = Textbox(name='Item:Edit', text='Item', window=window)
		self._status = Textbox(window=window, criteria={'best_match': "Status:Edit2"}, preinit=preinit, control_name='Status')

		# Define Buttons
		self.sro_operations = Button(window=window, criteria={'auto_id': "SROOpersButton", 'control_type': "Button", 'top_level_only': False}, preinit=preinit, control_name='SRO Operations')

		log.debug("'Service Order Lines' form initialized")

	@property
	def status(self):
		return self._status.text()

	@status.setter
	def status(self, value: str):
		if (value != 'Closed') and (value != 'Open'):
			raise ValueError
		elif self.status != value:
			self._status.edit_text = value


class ServiceOrderOperationsForm(Form):
	def __init__(self, window, preinit=False):
		log.debug("Initializing 'Service Order Operations' form")
		super().__init__(name='Service Order Operations (Linked)', text='Service Order Operations')
		self.window_uia = window['uia']
		self.window_win32 = window['win32']

		# Define Textboxes
		self._status = Textbox(window=window, criteria={'best_match': "Status:Edit3"}, preinit=preinit, control_name='Status')

		received_date = {'class': Datebox, 'kwargs': {'window': window, 'criteria': {'best_match': 'Received:Edit'}, 'preinit': preinit, 'control_name': 'Received'}}
		floor_date = {'class': Datebox, 'kwargs': {'window': window, 'criteria': {'best_match': 'Floor:Edit'}, 'preinit': preinit, 'control_name': 'Floor'}}
		fa_date = {'class': Datebox, 'kwargs': {'window': window, 'criteria': {'best_match': 'F/A:Edit'}, 'preinit': preinit, 'control_name': 'F/A'}}
		complete_date = {'class': Datebox, 'kwargs': {'window': window, 'criteria': {'best_match': 'Complete:Edit'}, 'preinit': preinit, 'control_name': 'Complete'}}

		reason_notes = {'class': Textbox, 'kwargs': {'window': window, 'criteria': {'best_match': 'Reason Notes:Edit'}, 'preinit': preinit, 'control_name': 'Reason Notes'}}
		resolution_notes = {'class': Textbox, 'kwargs': {'window': window, 'criteria': {'best_match': 'Resolution Notes:Edit'}, 'preinit': preinit, 'control_name': 'Resolution Notes'}}

		# Define Buttons
		self.sro_transactions = Button(window=window, criteria={'auto_id': "TransactionsButton", 'control_type': "Button", 'top_level_only': False}, preinit=preinit, control_name='SRO Transactions')
		print_repair_statement = {'class': Button, 'kwargs': {'window': window, 'criteria': {'auto_id': "uf_PrintRepairStatement", 'control_type': "Button", 'top_level_only': False}, 'preinit': preinit, 'control_name': 'Print Repair Statement'}}

		# Define Grids
		reasons_grid = {'class': GridView, 'kwargs': {'window': window, 'criteria': {'parent': self.window_uia.child_window(best_match='Tax Code:GroupBox'), 'auto_id': "ReasonsSubGrid", 'control_type': "Table", 'top_level_only': False}, 'preinit': preinit, 'control_name': 'Reasons'}}

		# Define Tabs
		self.general_tab = Tab(window=window, criteria={'parent': self.window_uia.child_window(best_match='GeneralTabControl'), 'best_match': "GeneralTabItemControl", }, name='General', controls={'received_date': received_date,
																									  'floor_date': floor_date,
																									  'fa_date': fa_date,
																									  'complete_date': complete_date}, preinit=preinit, control_name='General')

		self.reasons_tab = Tab(window=window, criteria={'parent': self.window_uia.child_window(best_match='ReasonsTabControl'), 'best_match': "ReasonsTabItemControl"}, name='Reasons', controls={'grid': reasons_grid,
																									  'reason_notes': reason_notes,
																									  'resolution_notes': resolution_notes,
																									  'print_repair_statement': print_repair_statement}, preinit=preinit, control_name='Reasons')

	log.debug("'Service Order Operations' form initialized")

	@property
	def status(self):
		return self._status.text()

	@status.setter
	def status(self, value: str):
		if (value != 'Closed') and (value != 'Open'):
			raise ValueError
		elif self.status != value:
			self._status.edit_text = value


class SROTransactionsForm(Form):
	def __init__(self, window, preinit=False):
		log.debug("Initializing 'SRO Transactions' form")
		super().__init__(name='SRO Transactions', text='SRO Transactions')
		self.window_uia = window['uia']
		self.window_win32 = window['win32']

		# Define Textboxes
		self.date_range_start = Textbox(window=window, criteria={'best_match': "Date Range:Edit1"}, fmt=datetime.date, preinit=preinit, control_name='Date Range Start')
		self.date_range_end = Textbox(window=window, criteria={'best_match': "Date Range:Edit2"}, fmt=datetime.date, preinit=preinit, control_name='Date Range End')

		# Define Buttons
		self.add_filter = Button(window=window, criteria={'auto_id': "AddlFiltersButton", 'control_type': "Button", 'top_level_only': False}, preinit=preinit, control_name='Add Filter')
		self.apply_filter = Button(window=window, criteria={'auto_id': "BtnFilterRefresh", 'control_type': "Button", 'top_level_only': False}, preinit=preinit, control_name='Apply Filter')
		self.clear_filter = Button(window=window, criteria={'auto_id': "BtnClearFilter", 'control_type': "Button", 'top_level_only': False}, preinit=preinit, control_name='Clear Filter')
		self.post_batch = Button(window=window, criteria={'auto_id': "PostBatchButton", 'control_type': "Button", 'top_level_only': False}, preinit=preinit, control_name='Post Batch')

		# Define Checkboxes
		self.include_posted = Checkbox(window=window, criteria={'auto_id': "FilterPosted", 'top_level_only': False}, preinit=preinit, control_name='Include Posted')
		# self.include_unposted = Checkbox(window=window, criteria={'auto_id': "FilterUnposted", 'control_type': "Button", 'top_level_only': False})

		# Define Grids
		self.grid = GridView(window=window, criteria={'auto_id': "MatlGrid", 'control_type': "Table", 'top_level_only': False}, preinit=preinit, control_name='Transaction')

		log.debug("'SRO Transactions' form intitialized")


class MiscIssueForm(Form):
	def __init__(self, window):
		self.window = window
		log.debug("Initializing 'Miscellaneous Issue' form")
		super().__init__(name='Miscellaneous Issue', text='Miscellaneous Issue')
		log.debug("'Miscellaneous Issue' form initialized")
		self.window_uia = self.window['uia']
		self.window_win32 = self.window['win32']

		# Define Textboxes
		self.item = Textbox(window=self.window, criteria={'best_match': "Item:Edit"}, fmt=('alphabetic', 'numeric', 'punctuation', 'upper'), preinit=False, control_name='Item')
		location = {'class': Textbox, 'kwargs': {'window': self.window, 'criteria': {'best_match': 'Location:Edit', 'top_level_only': False}, 'preinit': False, 'control_name': 'Location'}}
		quantity = {'class': Textbox, 'kwargs': {'window': self.window, 'criteria': {'best_match': 'Quantity:Edit', 'top_level_only': False}, 'preinit': False, 'control_name': 'Quantity'}}
		reason = {'class': Textbox, 'kwargs': {'window': self.window, 'criteria': {'best_match': 'Reason:Edit', 'top_level_only': False}, 'preinit': False, 'control_name': 'Reason'}}
		document_number = {'class': Textbox, 'kwargs': {'window': self.window, 'criteria': {'best_match': 'Document Number:Edit', 'top_level_only': False}, 'preinit': False, 'control_name': 'Document Number'}}
		generate_qty = {'class': Textbox, 'kwargs': {'window': self.window, 'criteria': {'best_match': 'Generate Qty:Edit', 'top_level_only': False}, 'preinit': False, 'control_name': 'Generate Qty'}}

		# Define Tabs
		self.detail_tab = Tab(window=self.window, criteria={'best_match': "DetailTabControl"}, name='Detail', controls={'location': location, 'quantity': quantity, 'reason': reason, 'document_number': document_number}, preinit=False, control_name='Detail')
		self.serial_numbers_tab = Tab(window=self.window, criteria={'best_match': "Serial NumbersTabControl"}, name='Serial Numbers', controls={'generate_qty': generate_qty}, preinit=False, control_name='Serial Numbers')


class SerialNumbersForm(Form):
	def __init__(self, window):
		self.window = window
		log.debug("Initializing 'Miscellaneous Issue' form")
		super().__init__(name='Miscellaneous Issue', text='Miscellaneous Issue')
		log.debug("'Miscellaneous Issue' form initialized")
		self.window_uia = self.window['uia']
		self.window_win32 = self.window['win32']

		# Define Textboxes
		self.serial_number = Textbox(window=self.window, criteria={'best_match': "Serial Number:Edit"}, fmt=('alphabetic', 'numeric', 'upper'), preinit=False, control_name='Serial Number')
		self.status = Textbox(window=self.window, criteria={'best_match': "Status:Edit"}, preinit=False, control_name='Status')
		self.location = Textbox(window=self.window, criteria={'best_match': 'Location:Edit'}, preinit=False, control_name='Location')


class Form2:
	def __init__(self, name: str, text: str):
		self.__name__ = name
		self.text = text
		self.is_open = False
		self.is_visible = False

	def initialize_controls(self):
		log.debug(f"Initializing '{self.__name__}' controls")
		self._init_controls()
		log.debug(f"'{self.__name__}' controls initialized")

	def __enter__(self):
		# With Form(name) as blah
		pass

	def __exit__(self):
		pass

	def __contains__(self, item):
		# If {Control} in {Form}
		pass

	def __call__(self, *args, **kwargs):
		# Make sure form is focused
		pass


class UnitsForm2(Form2):
	def __init__(self, window):
		self.window = window
		log.debug("Initializing 'Miscellaneous Issue' form")
		super().__init__(name='Miscellaneous Issue', text='Miscellaneous Issue')
		log.debug("'Miscellaneous Issue' form initialized")
		self.window_uia = None
		self.window_win32 = None
		self.serial_number = None
		self.item = None
		self.customer = None

	def _init_controls(self):
		self.window_uia = self.window['uia']
		self.window_win32 = self.window['win32']
		# Define Textboxes
		self.serial_number = Textbox(window=self.window, criteria={'best_match': "Unit:Edit"}, fmt=('alphabetic', 'numeric', 'upper'), control_name='Unit')
		self.item = Textbox(window=self.window, criteria={'best_match': "Item:Edit"}, fmt=('alphabetic', 'numeric', 'punctuation', 'upper'), control_name='Item')
		self.customer = Textbox()

	def _de_init_controls(self):
		self.window_uia = None
		self.window_win32 = None
		# Define Textboxes
		self.serial_number = None
		self.item = None

__all__ = ['UnitsForm', 'ServiceOrderLinesForm', 'ServiceOrderOperationsForm', 'SROTransactionsForm']
