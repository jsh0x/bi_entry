import sys
import logging
import configparser
import pathlib
import multiprocessing
import datetime
import argparse
from typing import Union, Iterable, Dict, Any, Tuple, List, Iterator
from time import sleep

import numpy as np
from PIL import Image
from matplotlib import pyplot as plt

from __init__ import find_file
from commands import Application, enumerate_screens, screenshot
from _sql import MS_SQL, SQL_Lite
from _crypt import decrypt
from exceptions import *

LabeledDataRow = Dict[str, Any]
SRO_Row = Dict[str, Any]
Date_Dict = Dict[str, datetime.datetime]
pfx_dict = {'11': 'OT', '13': 'LC', '40': 'SL', '21': 'SL', '63': ('BE', 'ACB'), '48': 'LCB'}
log = logging.getLogger('devLog')
config = configparser.ConfigParser()
_assorted_lengths_of_string = ('30803410313510753080335510753245107531353410',
                              '474046203600486038404260432039003960',
                              '63004620S875486038404260S875432039003960',
                              '58803900396063004620360048603840426038404620',
                              '1121327')
_adr_data, _usr_data, _pwd_data, _db_data, _key = _assorted_lengths_of_string
mssql = MS_SQL(address=decrypt(_adr_data, _key), username=decrypt(_usr_data, _key), password=decrypt(_pwd_data, _key), database=decrypt(_db_data, _key))
sqlite = SQL_Lite(database='positional_history.db', detect_types=1)
# transact parts
# quick query
# inputting reason codes

class Part:
	def __init__(self, part_number: str, quantity: int=1):
		self.part_number = part_number
		_data = mssql.query(f"SELECT [Qty],[DispName],[Location],[PartName] FROM Parts WHERE [PartNum] = '{self.part_number}'")
		self.quantity = quantity * int(_data.get('Qty', 1))
		self.display_name = str(_data.get('DispName', None))
		self.part_name = str(_data.get('PartName', None))
		self.location = str(_data.get('Location', None))
		log.debug(f"Part initialization complete for part {self.part_number}")

	def __str__(self):
		return f"{self.display_name}({self.part_number}) x {self.quantity}"


class Unit:
	def __init__(self, **kwargs: LabeledDataRow):
		# for k,v in kwargs.items():
		# 	log.info(f"{k}  {v}")
		self.id = kwargs.get('Id', None)
		self.serial_number = kwargs.get('Serial Number', None)
		# self.serial_number = kwargs.get('SerialNumber', None)
		# self.serial_number_prefix = None
		self._serial_number_prefix = None
		self.esn = kwargs.get('ESN', None)
		self.build = kwargs.get('Build', None)
		self.suffix = kwargs.get('Suffix', None)
		self.operation = kwargs.get('Operation', None)
		self.operator = kwargs.get('Operator', None)
		self.parts = kwargs.get('Parts', None).split(',')
		self.datetime = kwargs.get('DateTime', None)
		self.notes = kwargs.get('Notes', None)
		log.debug("Unit initialization complete")

	@property
	def serial_number_prefix(self) -> Union[str, Tuple[str, str]]:
		try:
			if self._serial_number_prefix is None:
				value = pfx_dict[self.serial_number[:2]]
			else:
				value = self._serial_number_prefix
		except Exception as ex:
			print(ex, self.serial_number)
		except (ValueError, KeyError, IndexError):
			value = None
		finally:
			return value

	@serial_number_prefix.setter
	def serial_number_prefix(self, value: str):
		if type(self.serial_number_prefix) is tuple and value in self.serial_number_prefix:
			self._serial_number_prefix = value
			log.debug(f"Serial Number Prefix set: {value}")
		else:
			self._serial_number_prefix = None

	@property
	def parts(self) -> Iterator[Part]:
		return self._parts

	@parts.setter
	def parts(self, value: Iterable[str]):
		if value and value != ['']:
			self._parts = map(Part, value)
			string = ""
			for p in self._parts:
				string += f"{p}, "
			log.debug("Parts mapped: "+string[:-2])
		else:
			self._parts = None

	@property
	def datetime(self) -> datetime.datetime:
		return self._datetime

	@datetime.setter
	def datetime(self, value: str):
		if type(value) is str:
			self._datetime = datetime.datetime.strptime(value, "%m/%d/%Y %I:%M:%S %p")
			log.debug(f"Datetime set: {self._datetime}")
		else:
			self._datetime = value

#ErrorDialog
#OKButton
#Static2


def pre__init__(app: Application):
	log.debug("Pre-initialization process started")
	# app._add_form('Units', preinit=True)
	# app._add_form('SROLines', preinit=True)
	# app._add_form('SROOperations', preinit=True)
	# app._add_form('SROTransactions', preinit=True)
	log.debug("Pre-initialization completed")


def transact(app: Application):
	global_props = {}
	log.debug("Transaction script started")
	# pre__init__(app)
	sfx_dict = {'Direct': 1, 'RTS': 2, 'Demo': 3, 'Refurb': 4, 'Monitoring': 5}
	while True:
		log.debug("Checking queued non-QC transactions")
		queued = mssql.query("SELECT DISTINCT [Suffix] FROM PyComm WHERE [Status] = 'Queued' AND [Operation] <> 'QC'", fetchall=True)
		if not queued:
			log.debug("No queued non-QC transactions found")
			log.debug("Checking queued QC transactions")
			queued = mssql.query("SELECT DISTINCT [Suffix] FROM PyComm WHERE [Status] = 'Queued' AND [Operation] = 'QC'", fetchall=True)
			if not queued:
				log.debug("No queued QC transactions found")
				continue
			else:
				log.debug(f"Queued QC transaction found for suffix type: {queued[0]}")
				mod = '='
		else:
			log.debug(f"Queued non-QC transaction found for suffix type: {queued[0]}")
			mod = '<>'
		queued2 = []
		for q in queued:
			queued2.append(q[0])
		queued = queued2
		sorted_sfx_queue = sorted(queued, key=lambda x: sfx_dict[x])
		log.debug("Receiving unit data")
		unit_data = mssql.query(f"SELECT TOP 1 * FROM PyComm WHERE [Suffix] = '{sorted_sfx_queue[0]}' AND [Status] = 'Queued' AND [Operation] {mod} 'QC' ORDER BY [DateTime] ASC")
		unit = Unit(**unit_data)
		log.info("Unit data found:")
		log.info(f"SN: {unit_data['Serial Number']}, Build: {unit_data['Build']}, Suffix: {unit_data['Suffix']}, Notes: {unit_data['Notes']}")
		log.info(f"DateTime: {unit_data['DateTime']}, Operation: {unit_data['Operation']}, Operator: {unit_data['Operator']}, Parts: {unit_data['Parts']}")
		# Assumes Units form already open
		log.debug("Opening Units form")
		app.add_form('UnitsForm')
		log.debug("Unit form opened")
		Units = app.UnitsForm
		# test('UnitsForm', Units)
		# Opens unit
		if type(unit.serial_number_prefix) is tuple:
			for pfx in unit.serial_number_prefix:
				log.debug(f"Trying prefix '{pfx}'")
				Units.serial_number = pfx + unit.serial_number
				app.apply_filter.click()
				if Units.serial_number == pfx + unit.serial_number:
					log.debug(f"Setting prefix to '{pfx}'")
					unit.serial_number_prefix = pfx
					break
				app.apply_filter.click()
				app.refresh_filter.click()
			else:
				raise ValueError
		else:
			Units.serial_number = unit.serial_number_prefix + unit.serial_number
			app.apply_filter.click()
			if Units.serial_number != unit.serial_number_prefix + unit.serial_number:
				raise ValueError
		log.debug("Unit Started")
		# TOP - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
		im = np.array(screenshot())
		crd = Units.owner_history_tab.coordinates
		img = im[crd.top:crd.bottom, crd.left:crd.right]
		plt.imshow(img)
		plt.show()
		# BTM - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
		log.debug("Opening Owner History Tab")
		Units.owner_history_tab.select()
		log.debug("Checking Owner History Tab grid")
		# TOP - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
		im = np.array(screenshot())
		crd = Units.owner_history_tab.coordinates
		img = im[crd.top:crd.bottom, crd.left:crd.right]
		plt.imshow(img)
		plt.show()
		# BTM - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
		quit()

		Units.owner_history_tab.grid.sort_with_header('Eff Date')
		Units.owner_history_tab.grid.populate_grid('Eff Date', 1)
		Units.owner_history_tab.grid.select_cell('Eff Date', 1)
		min_date = Units.owner_history_tab.grid.cell
		log.debug(f"Received date found: {min_date}")
		# Check SROs
		rows = []
		log.debug("Opening Service History Tab")
		Units.service_history_tab.select()
		max_results = 3
		max_rows = 5
		log.debug("Checking Service History Tab grid")
		if max_rows > Units.service_history_tab.grid.rows:
			max_rows = Units.service_history_tab.grid.rows
		Units.service_history_tab.grid.populate_grid('Close Date', range(1, max_rows+1))
		for i in range(1, max_rows+1):
			Units.service_history_tab.grid.select_cell('Close Date', i)
			if Units.service_history_tab.grid.cell == None:
				rows.append(i)
			if len(rows) >= max_results:
				break
		# Check each SRO making sure it's open
		log.info(f"Of first {max_rows} rows, {len(rows)} open SROs found: {rows}")
		for i,row in enumerate(rows):
			log.debug(f"Trying SRO")
			Units.service_history_tab.grid.select_row(row)
			Units.service_history_tab.view.click(wait_string=None)
			log.debug("Opening Service Order Lines form")
			app.add_form('ServiceOrderLinesForm')
			SRO_Lines = app.ServiceOrderLinesForm
			log.debug("Waiting for Service Order Lines form...")
			SRO_Lines.sro_operations.ready()
			log.debug("Service Order Lines form opened")
			log.debug(f"Status found: {SRO_Lines.status}")
			if SRO_Lines.status != 'Open':  # If Service Order Lines' status isn't open, go back and try next SRO
				app.cancel_close.click()
				continue
			SRO_Lines.sro_operations.click(wait_string='form')
			log.debug("Opening Service Order Operations form")
			app.add_form('ServiceOrderOperationsForm')
			SRO_Operations = app.ServiceOrderOperationsForm
			log.debug("Waiting for Service Order Operations form...")
			SRO_Operations.general_tab.ready()
			log.debug("Service Order Operations form opened")
			log.debug(f"Status found: {SRO_Operations.status}")
			if SRO_Operations.status != 'Open':  # If Service Order Operations' status isn't open, go back and try next SRO
				app.cancel_close.click()
				app.cancel_close.click()
				continue
			if unit.parts:
				log.debug("Opening SRO Transactions form")
				SRO_Operations.sro_transactions.click(wait_string='form')
				app.add_form('SROTransactionsForm')
				SRO_Transactions = app.SROTransactionsForm
				log.debug("Waiting for SRO Transactions form...")
				SRO_Transactions.apply_filter.ready()
				log.debug("SRO Transactions form opened")
				log.debug("Setting Date Range Start")
				SRO_Transactions.date_range_start.set_text(min_date)
				SRO_Transactions.apply_filter.click()
				max_rows = SRO_Transactions.grid.rows-1
				posted = []
				SRO_Transactions.post_batch.ready()
				log.debug("Checking for already-posted items")
				if max_rows > 0:
					SRO_Transactions.grid.populate_grid(('Posted', 'Item'), range(1, max_rows+1), visible_only=True)
					for j in range(1, max_rows + 1):
						SRO_Transactions.grid.select_cell('Posted', j)
						posted_cell = SRO_Transactions.grid.cell
						if posted_cell:
							SRO_Transactions.grid.select_cell('Item', j)
							posted.append(SRO_Transactions.grid.cell)
						else:
							#raise SyteLineError
							continue
					SRO_Transactions.include_posted.click()
					SRO_Transactions.apply_filter.click()
					SRO_Transactions.post_batch.ready()
				if not posted:
					log.debug("No posted items found")
				else:
					for p in posted:
						log.debug(f"Posted item found: {p}")
				count = 1
				new_parts_list = []
				for part in unit.parts:
					log.debug(f"Attempting to transact part {part}")
					if part.part_number in posted:
						log.debug("Item already posted, skipping")
						continue
					SRO_Transactions.grid.select_cell('Item', count)
					SRO_Transactions.grid.click_cell()
					sleep(0.2)
					while app.popup.exists():
						log.debug("Close pop-up")
						app.popup.close_alt_f4()
						sleep(0.2)
					log.debug(f"Entering Part Number: {part.part_number}")
					SRO_Transactions.grid.cell = part.part_number
					SRO_Transactions.grid.select_cell('Quantity', count)
					SRO_Transactions.grid.click_cell()
					while app.popup.exists():
						log.debug("Close pop-up")
						app.popup.close_alt_f4()
						sleep(0.2)
					log.debug(f"Entering Quantity: {part.quantity}")
					SRO_Transactions.grid.cell = part.quantity
					SRO_Transactions.grid.select_cell('Billing Code', count)
					SRO_Transactions.grid.click_cell()
					while app.popup.exists():
						log.debug("Close pop-up")
						app.popup.close_alt_f4()
						sleep(0.2)
					if unit.suffix == 'Direct' or unit.suffix == 'RTS':
						log.debug("Entering Billing Code: Contract")
						SRO_Transactions.grid.cell = 'Contract'
					else:
						log.debug("Entering Billing Code: No Charge")
						SRO_Transactions.grid.cell = 'No Charge'
					count += 1
					new_parts_list.append(part)
				for i,part in zip(range(1, count+1), new_parts_list):
					SRO_Transactions.grid.select_cell('Location', i)
					SRO_Transactions.grid.click_cell()
					while app.popup.exists():
						log.debug("Close pop-up")
						app.popup.close_alt_f4()
						sleep(0.2)
					log.debug(f"Entering Location: {part.location} for part {part.part_number}")
					SRO_Transactions.grid.cell = part.location
				log.debug("Posting batch")
				SRO_Transactions.post_batch.ready()
				########################################
				# app.save.click()
				# SRO_Transactions.post_batch.ready()
				# SRO_Transactions.post_batch.click()
				# app.save_close.click()
				# app.save_close.click()
				########################################
				app.cancel_close.click()  #####
				app.cancel_close.click()  #####
				log.debug("Waiting for Service Order Lines form...")
				SRO_Lines.sro_operations.ready()
				log.debug("Service Order Lines form opened")
				log.debug("Opening Service Order Operations form")
				SRO_Lines.sro_operations.click(wait_string='form')
				app.add_form('ServiceOrderOperationsForm')
				log.debug("Waiting for Service Order Operations form...")
				SRO_Operations.sro_transactions.ready()
				log.debug("Service Order Operations form opened")
			# SRO_Operations.general_tab.select()
			log.debug("Initiating General Tab controls")
			SRO_Operations.general_tab.initiate_controls()
			log.debug("General Tab controls initiated")
			rc_d = SRO_Operations.general_tab.received_date.text()
			if not rc_d:
				log.debug("No Received Date found")
			else:
				log.debug(f"Received Date found: {rc_d}")
			fl_d = SRO_Operations.general_tab.floor_date.text()
			if not fl_d:
				log.debug("No Floor Date found")
			else:
				log.debug(f"Flood Date found: {fl_d}")
			#fa_d = SRO_Operations.general_tab.fa_date.text()
			cp_d = SRO_Operations.general_tab.complete_date.text()
			if not cp_d:
				log.debug("No Complete Date found")
			else:
				log.debug(f"Complete Date found: {cp_d}")
			if not rc_d:
				log.debug(f"Entering Received Date: {min_date}")
				SRO_Operations.general_tab.received_date.set_text(min_date)
			if not fl_d:
				min_date_temp = datetime.datetime.strptime(min_date, '%m/%d/%Y')
				date_string = min_date_temp.strftime("%Y-%m-%d 00:00:00")
				value = mssql.query(f"SELECT TOP 1 [DateTime] FROM Operations WHERE [DateTime] > CONVERT ( DATETIME , '{date_string}' , 102 ) ORDER BY [DateTime] ASC")
				if not value:
					value = unit.datetime.strftime("%m/%d/%Y %I:%M:%S %p")
				else:
					print(value)
					print(value[0])
					value = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
					value = value.strftime("%m/%d/%Y %I:%M:%S %p")
				log.debug(f"Entering Floor Date: {value}")
				SRO_Operations.general_tab.floor_date.set_text(value)
			if unit.operation == 'QC' and not cp_d:
				log.debug(f"Entering Complete Date: {unit.datetime.strftime('%m/%d/%Y %I:%M:%S %p')}")
				SRO_Operations.general_tab.complete_date.set_text(unit.datetime.strftime("%m/%d/%Y %I:%M:%S %p"))
			quit()
			log.debug("Opening Reasons Tab")
			SRO_Operations.reasons_tab.select()
			# Fill out Resolution Notes
			block_text = SRO_Operations.reasons_tab.resolution_notes.texts()
			SRO_Operations.reasons_tab.resolution_notes.set_focus()
			SRO_Operations.reasons_tab.resolution_notes.set_keyboard_focus()
			SRO_Operations.reasons_tab.resolution_notes.send_keystrokes('^{END}')
			if block_text[-1].strip(' ') != '':
				SRO_Operations.reasons_tab.resolution_notes.send_keystrokes('{ENTER}')
			count = 0
			for part in unit.parts:
				if part.part_number in posted:
					continue
				SRO_Operations.reasons_tab.resolution_notes.send_keystrokes(f"{part.part_name}, ")
				count += 1
			if count > 0:
				SRO_Operations.reasons_tab.resolution_notes.send_keystrokes('{BACKSPACE}{BACKSPACE}{ENTER}')
				res = mssql.query(f"SELECT [FirstName],[LastName] FROM Users WHERE [Username] = '{unit.operator}'")
				first,last = res['FirstName'],res['LastName']
				initials = first[0].upper()+last[0].upper()
				SRO_Operations.reasons_tab.resolution_notes.send_keystrokes(f"{initials} {unit.datetime.strftime('%m/%d/%Y')}")
			if unit.operation == 'QC':
				# Fill out Reason Notes
				block_text = SRO_Operations.reasons_tab.reason_notes.texts()
				for line in block_text:
					if 'UDI' in line.upper():
						udi = True
						break
				else:
					udi = False
				SRO_Operations.reasons_tab.reason_notes.set_focus()
				SRO_Operations.reasons_tab.reason_notes.set_keyboard_focus()
				SRO_Operations.reasons_tab.reason_notes.send_keystrokes('^{END}')
				if block_text[-1].strip(' ') != '':
					SRO_Operations.reasons_tab.reason_notes.send_keystrokes('{ENTER}')
				if not udi:
					SRO_Operations.reasons_tab.reason_notes.send_keystrokes('UDI{ENTER}')
				SRO_Operations.reasons_tab.reason_notes.send_keystrokes('PASSED ALL TESTS')
				# Fill out Reasons Grid
				SRO_Operations.reasons_tab.reasons_grid.populate_grid(('General Reason', 'Specific Reason',
																		  'General Resolution', 'Specific Resolution'), 1)
				SRO_Operations.reasons_tab.reasons_grid.select_cell('General Reason', 1)
				if not SRO_Operations.reasons_tab.reasons_grid.cell:  # ???
					raise ValueError
				SRO_Operations.reasons_tab.reasons_grid.select_cell('Specific Reason', 1)
				if not SRO_Operations.reasons_tab.reasons_grid.cell:
					SRO_Operations.reasons_tab.reasons_grid.cell = 20
				SRO_Operations.reasons_tab.reasons_grid.select_cell('General Resolution', 1)
				if not SRO_Operations.reasons_tab.reasons_grid.cell:
					SRO_Operations.reasons_tab.reasons_grid.cell = 10000
				SRO_Operations.reasons_tab.reasons_grid.select_cell('Specific Resolution', 1)
				if not SRO_Operations.reasons_tab.reasons_grid.cell:
					SRO_Operations.reasons_tab.reasons_grid.cell = 100
				SRO_Operations.status = 'Closed'
			########################
			# app.save_close.click()
			# app.save_close.click()
			########################
			app.cancel_close.click()  #####
			app.cancel_close.click()  #####
		log.debug("Unit Completed")
		for k,v in global_props.items():
			try:
				print(k)
				print(v[0])
				plt.imshow(v[1])
				plt.show()
			except Exception:
				pass


def query():
	pass


def reason():
	pass


# '75268094752664615822V209t1437070'


def main(argv):
	"""parser = argparse.ArgumentParser()
	parser.add_argument('cmd', type=str)
	parser.parse_args('username', type=str)
	parser.add_argument('-d', '--directory', help='directory of SyteLine executable')"""
	if len(argv) < 4:
		raise ValueError
	usage_string = f"usage: {argv[0]} cmd username password [OPTIONS]..."
	cmd_all = {'transact': transact, 'query': query, 'reason': reason}
	opt_all = ('-fp', '-w', '-k', '-p')
	long_opt_all = ('--filepath', '--workers', '--key', '--preference')
	cmd,usr,pwd = argv[1:4]
	# def_key = '6170319'
	if len(argv) > 5:
		opt = dict(zip(argv[4::2], argv[5::2]))
		for o in opt.keys():
			if o not in opt_all:
				raise ValueError
	else:
		opt = {}
	if cmd not in cmd_all.keys():
		raise ValueError(f"command {cmd} is not valid")

	log.debug("Attempting to read 'config.ini'")
	config.read_file(open('config.ini'))
	filepath = opt.get('-fp', None)
	if filepath and pathlib.Path(filepath).exists():
		if config.has_section('Paths') and config.has_option('Paths', 'sl_exe'):
			filepath = config.set('Paths', 'sl_exe', filepath)
	else:
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
	'''instances = int(opt.get('-w', 1))
	pref = opt.get('-p', None)
	screens = enumerate_screens()
	# pref[0]: -----------------------------------
	# l = last
	# m = middle (if 3+ screens, but WHY though???)
	# f = first
	# a = all

	# pref[1]: -----------------------------------
	# f = full
	# h = half (horizontal, top-half/bottom-half)
	# v = half (vertical, left-half/right-half)
	# q = quarter
	# p = partial
	cpu_count = multiprocessing.cpu_count()
	if instances > cpu_count:
		raise ValueError(f"Number of instances requested ({instances}) exceeds number of available processors ({cpu_count})")
	if np.floor_divide(instances, len(screens.keys())) > 4:
		raise ValueError(f"Number of instances requested ({instances}) exceeds limit of 4 instances per screen")
	if not pref:
		if instances == 1:
			pref = 'lf'
		elif instances == 2:
			pref = 'lh'
		elif instances >= 3:
			pref = 'lq'
	elif pref[1] == 'q' and instances > len(screens.keys())*4:
			raise ValueError(f"Number of instances requested ({instances}) exceeds limit of 4 instances per screen")
	elif pref[1] == 'h' and instances > len(screens.keys())*2:
			raise ValueError(f"Number of instances requested ({instances}) exceeds limit of 4 instances per screen")
	elif pref[1] == 'f' and instances > len(screens.keys()):
			raise ValueError(f"Number of instances requested ({instances}) exceeds limit of 4 instances per screen")
	data = []

	for window in range(instances):
		if pref[1] == 'f':
			j = 1
			k = 1
			if pref[0] == 'l':
				i = len(screens.keys()) - window
			elif pref[0] == 'f':
				i = 1 + window
		elif pref[1] == 'h':
			j = np.floor_divide(window, 2)
			k = 2
			if pref[0] == 'l':
				i = len(screens.keys()) - j
			elif pref[0] == 'f':
				i = 1 + j
		elif pref[1] == 'q':
			j = np.floor_divide(window, 4)
			k = 4
			if pref[0] == 'l':
				i = len(screens.keys()) - j
			elif pref[0] == 'f':
				i = 1 + j
		else:
			j = 1
			k = 1
			if pref[0] == 'l':
				i = len(screens.keys()) - window
			elif pref[0] == 'f':
				i = 1 + window
		scrn = screens[i]
		subwindow = np.remainder(window, k)
		left = scrn.left
		top = scrn.top
		right = scrn.right
		bottom = scrn.bottom
		if pref[1] == 'f':
			pass
		elif pref[1] == 'h':
			if subwindow == 0:
				bottom -= np.floor_divide(scrn.height, 2)
			elif subwindow == 1:
				top += np.floor_divide(scrn.height, 2)
		elif pref[1] == 'q':
			if subwindow == 0:
				right -= np.floor_divide(scrn.width, 2)
				bottom -= np.floor_divide(scrn.height, 2)
			elif subwindow == 1:
				left += np.floor_divide(scrn.width, 2)
				bottom -= np.floor_divide(scrn.height, 2)
			elif subwindow == 2:
				top += np.floor_divide(scrn.height, 2)
				right -= np.floor_divide(scrn.width, 2)
			elif subwindow == 3:
				left += np.floor_divide(scrn.width, 2)
		data = (filepath, opt, usr, pwd, cmd_all, cmd, left, top, right, bottom)
		p = multiprocessing.Process(target=_subprocess, args=data)'''
	with Application(filepath) as app:
		# app.move_and_resize(left=left, top=top, right=right, bottom=bottom)
		log.debug('SyteLine application started')
		try:
			# crypt_key = opt.get('-k', def_key)
			crypt_key = opt.get('-k', None)
			if crypt_key:
				log.debug("Crypt key provided")
				pwd = decrypt(pwd, key=crypt_key)
			app.log_in(usr, pwd)
		except SyteLineLogInError:
			log.exception("Failed to sign in")
			quit()
		log.info(f"Successfully logged in as '{usr}'")
		cmd_all[cmd](app)


if __name__ == '__main__':
	main(sys.argv)