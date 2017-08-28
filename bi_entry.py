import os
import sys
import logging
import configparser
import pathlib
from string import ascii_letters as letters
from collections import defaultdict, UserDict
import datetime
import argparse
import concurrent.futures as cf
from typing import Union, Iterable, Dict, Any, Tuple, List, Iterator
from time import sleep

import numpy as np
from PIL import Image
from matplotlib import pyplot as plt
import pyautogui as pag
from pywinauto import keyboard as kbd
from pywinauto.timings import always_wait_until_passes
from pywinauto import xml_helpers

from __init__ import find_file
from commands import Application, enumerate_screens, screenshot, moveTo
from _sql import MS_SQL, SQL_Lite
from _crypt import decrypt
from exceptions import *
from computer_vision import CV_Config

pag.FAILSAFE = True

LabeledDataRow = Dict[str, Any]
SRO_Row = Dict[str, Any]
# TODO: LabeledDataRow -> NamedTuple
Date_Dict = Dict[str, datetime.datetime]
pfx_dict = {'11': 'OT', '13': 'LC', '40': 'SL', '21': 'SL', '63': ('BE', 'ACB'), '48': 'LCB'}


log = logging.getLogger('root')
time_log = logging.getLogger('logTimer')

config = configparser.ConfigParser()
_assorted_lengths_of_string = ('30803410313510753080335510753245107531353410',
                              '474046203600486038404260432039003960',
                              '63004620S875486038404260S875432039003960',
                              '58803900396063004620360048603840426038404620',
                              '1121327')
_adr_data, _usr_data, _pwd_data, _db_data, _key = _assorted_lengths_of_string
mssql = MS_SQL(address=decrypt(_adr_data, _key), username=decrypt(_usr_data, _key), password=decrypt(_pwd_data, _key), database=decrypt(_db_data, _key))
# sqlite = SQL_Lite(database='positional_history.db')
# transact parts
# quick query
# inputting reason codes
# pyperclip.copy(u'\t1-61-00377-0\tZSVC-ETONE\t1.000\tNo Charge\t\r\n')

file_list = os.listdir(os.getcwd())
if 'dev.key' in file_list:
	dev_mode = True
else:
	dev_mode = False

gen_rso_codes = {}
spec_rso_codes = {}

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
			print(None)
			return None

	def reset(self):
		self._start_time = None

	def stop(self):
		retval = self.lap()
		self.reset()
		return retval
timer = TestTimer()

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
		self.parts = kwargs.get('Parts', None)
		self.datetime = kwargs.get('DateTime', None)
		self.notes = kwargs.get('Notes', None)
		self._product = None
		self._whole_build = None
		self._operator_initials = None
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
	def parts(self, value):
		if value:
			value = value.split(',')
			if value != ['']:
				self._parts = list(map(Part, value))
				string = ""
				for p in self._parts:
					string += f"{p}, "
				log.debug("Parts mapped: "+string[:-2])
		else:
			log.debug("No parts")
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

	@property
	def whole_build(self):
		if self._whole_build is None:
			data = mssql.query(f"SELECT [ItemNumber],[Carrier],[Suffix] FROM UnitData WHERE [SerialNumber] = '{self.serial_number}'")
			if not data:
				raise ValueError
			item,carrier,sfx = data['ItemNumber'],data['Carrier'],data['Suffix']
			if carrier == 'None':
				build = item
			else:
				if sfx == 'Direct':
					if not (item.endswith('S') or item.endswith('V')):
						build = f"{item}{carrier[0].upper()}"
					else:
						build = item
				else:
					start, end = item.rsplit('-', 1)
					if not (start.endswith('S') or start.endswith('V')):
						build = f"{start}{carrier[0].upper()}-{end}"
					else:
						build = f"{start}-{end}"
			self._whole_build = build
		return self._whole_build

	@whole_build.setter
	def whole_build(self, value):
		self._whole_build = value

	@property
	def operator_initials(self):
		if self._operator_initials is None:
			fullname = mssql.query(f"SELECT [FullName] FROM Users WHERE [Username] = '{self.operator}'")
			first, last = fullname[0].split(' ', 1)
			self._operator_initials = first.strip()[0].upper()+last.strip()[0].upper()
		return self._operator_initials

	@operator_initials.setter
	def operator_initials(self, value):
		self._operator_initials = value

	@property
	def product(self):
		if self._product is None:
			data = mssql.query(f"SELECT [Product] FROM Builds WHERE [Prefix] = '{self.serial_number_prefix}'")
			if not data:
				raise ValueError
			self._product = data[0]
		return self._product

	@product.setter
	def product(self, value):
		self._product = value
#ErrorDialog
#OKButton
#Static2


# or Default_Listionary


def pre__init__(app: Application):
	log.debug("Pre-initialization process started")
	# app._add_form('Units', preinit=True)
	# app._add_form('SROLines', preinit=True)
	# app._add_form('SROOperations', preinit=True)
	# app._add_form('SROTransactions', preinit=True)
	log.debug("Pre-initialization completed")


def _try_unit(unit: Unit, app: Application):
	# Assumes Units form already open
	Units = app.UnitsForm
	if type(unit.serial_number_prefix) is tuple:
		for pfx in unit.serial_number_prefix:
			log.debug(f"Trying prefix '{pfx}'")
			Units.serial_number = pfx + unit.serial_number
			Units._unit.send_keystrokes('{F4}')
			if Units.serial_number == pfx + unit.serial_number:
				log.debug(f"Setting prefix to '{pfx}'")
				unit.serial_number_prefix = pfx
				break
			Units._unit.send_keystrokes('{F4}')
			Units._unit.send_keystrokes('{F5}')
			timer.start()
		else:
			log.error(f"Cannot find correct prefix for serial number: '{unit.serial_number}'")
			raise InvalidSerialNumberError(f"Cannot find correct prefix for serial number: '{unit.serial_number}'")
	else:
		Units.serial_number = unit.serial_number_prefix + unit.serial_number
		app.apply_filter.click()
		if Units.serial_number != unit.serial_number_prefix + unit.serial_number:
			log.error(f"SyteLine had some major issues with serial number: '{unit.serial_number}'")
			raise SyteLineFilterInPlaceError("")
	log.debug("Unit Started")


def _try_serial(unit: Unit, app: Application):
	# Assumes Serial Numbers form already open
	SrlNum = app.SerialNumbersForm
	if type(unit.serial_number_prefix) is tuple:
		for pfx in unit.serial_number_prefix:
			log.debug(f"Trying prefix '{pfx}'")
			SrlNum.serial_number.set_text(pfx + unit.serial_number)
			SrlNum.serial_number.send_keystrokes('{F4}')
			if SrlNum.serial_number.texts() == pfx + unit.serial_number:
				log.debug(f"Setting prefix to '{pfx}'")
				unit.serial_number_prefix = pfx
				break
			SrlNum.serial_number.send_keystrokes('{F4}')
			SrlNum.serial_number.send_keystrokes('{F5}')
			timer.start()
		else:
			log.error(f"Cannot find correct prefix for serial number: '{unit.serial_number}'")
			raise InvalidSerialNumberError(f"Cannot find correct prefix for serial number: '{unit.serial_number}'")
	else:
		SrlNum.serial_number.set_text(unit.serial_number_prefix + unit.serial_number)
		app.apply_filter.click()
		# log.debug(f"{SrlNum.serial_number.text()}")
		# log.debug(f"{unit.serial_number_prefix + unit.serial_number}")

		if SrlNum.serial_number.text() != unit.serial_number_prefix + unit.serial_number:
			log.error(f"SyteLine had some major issues with serial number: '{unit.serial_number}'")
			raise SyteLineFilterInPlaceError("")
	log.info(f"Unit {unit.serial_number_prefix + unit.serial_number} Checked")


def _try_serial2(unit: Unit, app: Application, cv: CV_Config):
	# Assumes Serial Numbers form already open
	SrlNum = app.SerialNumbersForm
	if type(unit.serial_number_prefix) is tuple:
		for pfx in unit.serial_number_prefix:
			log.debug(f"Trying prefix '{pfx}'")
			pag.click(*cv.window_gc.txt_sn.global_center)
			sleep(0.2)
			pag.typewrite(pfx + unit.serial_number)
			sleep(0.2)
			pag.press('f4')
			if SrlNum.serial_number.texts() == pfx + unit.serial_number:
				log.debug(f"Setting prefix to '{pfx}'")
				unit.serial_number_prefix = pfx
				break
			pag.press('f4')
			pag.press('f5')
			timer.start()
		else:
			log.error(f"Cannot find correct prefix for serial number: '{unit.serial_number}'")
			raise InvalidSerialNumberError(f"Cannot find correct prefix for serial number: '{unit.serial_number}'")
	else:
		pag.click(*cv.window_gc.txt_sn.global_center)
		sleep(0.2)
		pag.typewrite(unit.serial_number_prefix + unit.serial_number)
		sleep(0.2)
		pag.press('f4')
		sleep(0.2)
		# log.debug(f"{SrlNum.serial_number.text()}")
		# log.debug(f"{unit.serial_number_prefix + unit.serial_number}")

		if SrlNum.serial_number.text() != unit.serial_number_prefix + unit.serial_number:
			log.error(f"SyteLine had some major issues with serial number: '{unit.serial_number}'")
			raise SyteLineFilterInPlaceError("")
	log.info(f"Unit {unit.serial_number_prefix + unit.serial_number} Checked")


def _open_first_open_sro(unit: Unit, app: Application):
	# Assumes Units form already open
	Units = app.UnitsForm
	# Check SROs
	rows = []
	log.debug("Opening Service History Tab")
	Units.service_history_tab.select()
	max_results = 3
	max_rows = 5
	log.debug("Checking Service History Tab grid")
	if max_rows > Units.service_history_tab.grid.rows:
		max_rows = Units.service_history_tab.grid.rows
	try:
		Units.service_history_tab.grid.populate('Close Date', range(1, max_rows + 1))
	except Exception:
		raise DataGridError("")
	for i in range(1, max_rows + 1):
		Units.service_history_tab.grid.select_cell('Close Date', i)
		if Units.service_history_tab.grid.cell == None:
			rows.append(i)
		if len(rows) >= max_results:
			break
	# Check each SRO making sure it's open
	log.info(f"Of first {max_rows} rows, {len(rows)} open SROs found: {rows}")
	sro_count = 0
	for i, row in enumerate(rows):
		sro_count += 1
		try:
			log.debug(f"Trying SRO")
			Units.service_history_tab.grid.select_row(row)
			Units.service_history_tab.view.click()
			log.debug("Opening Service Order Lines form")
			app.add_form('ServiceOrderLinesForm')
			# app.__preinit__(2)
			SRO_Lines = app.ServiceOrderLinesForm
			# log.debug("Waiting for Service Order Lines form...")
			# SRO_Lines.sro_operations.ready()
			log.debug("Service Order Lines form opened")
			log.debug(f"Status found: {SRO_Lines.status}")
			if SRO_Lines.status != 'Open':  # If Service Order Lines' status isn't open, go back and try next SRO
				raise SROClosedWarning(data='SRO_Lines')
			xml_helpers.WriteDialogToFile('SROLines.xml', app._win.wrapper_object())
			app.write_data('SROLines')
			SRO_Lines.sro_operations.click()
			log.debug("Opening Service Order Operations form")
			# app.__preinit__(3)
			app.add_form('ServiceOrderOperationsForm')
			SRO_Operations = app.ServiceOrderOperationsForm
			# log.debug("Waiting for Service Order Operations form...")
			# SRO_Operations.general_tab.ready()
			log.debug("Service Order Operations form opened")
			log.debug(f"Status found: {SRO_Operations.status}")
			if SRO_Operations.status != 'Open':  # If Service Order Operations' status isn't open, go back and try next SRO
				raise SROClosedWarning(data='SRO_Operations')
			break
		except SROClosedWarning as warn:
			if warn.data == 'SRO_Operations':
				app.cancel_close.click()
				app.cancel_close.click()
			elif warn.data == 'SRO_Lines':
				app.cancel_close.click()
			continue
	else:
		raise UnitClosedError("Unit has no open SROs")
	return sro_count


def _group_units_by_build(units: List[Unit]) -> Dict[str, List[Unit]]:
	retval = defaultdict(list)
	for unit in units:
		retval[unit.whole_build].append(unit)
	return retval


def transact(app: Application):
	log.debug("Transaction script started")
	log.debug("Opening Units form")
	app.open_form('Units')
	# app.__preinit__(1)
	Units = app.UnitsForm
	log.debug("Unit form opened")
	sfx_dict = {'Direct': 1, 'RTS': 2, 'Demo': 3, 'Refurb': 4, 'Monitoring': 5}
	sleep_counter = 0
	while True:
		log.debug("Checking queued non-QC transactions")
		queued = mssql.query("SELECT DISTINCT [Suffix] FROM PyComm WHERE [Status] = 'Queued' AND [Operation] <> 'QC'", fetchall=True)
		if not queued:
			log.debug("No queued non-QC transactions found")
			log.debug("Checking queued QC transactions")
			queued = mssql.query("SELECT DISTINCT [Suffix] FROM PyComm WHERE [Status] = 'Queued' AND [Operation] = 'QC'", fetchall=True)
			if not queued:
				log.debug("No queued QC transactions found")
				if sleep_counter > 16:
					sleep(60)
				elif sleep_counter > 10:
					sleep(10)
				else:
					sleep(1)
				sleep_counter += 1
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
		sleep_counter = 0
		# Select Top 1 * FROM
		# (Select[Serial Number],
		# 	   [Build],
		# 	   [Suffix],
		# 	   [Operation],
		# 	   SUBSTRING(u.[FirstName], 1, 1) +
		# 	   SUBSTRING(u.[LastName], 1, 1) AS Initials,
		# 	   Parts,
		# 	   [DateTime],
		# 	   [Notes],
		# 	   [Status]
		# 	   From PyComm
		# 	   Inner join Users u
		# on Operator = u.Username
		# Where[Status] = 'Queued' AND Operation <> 'QC' AND Parts != ''
		# UNION
		# Select[Serial Number], [Build], [Suffix], [Operation],
		#        SUBSTRING(u.[FirstName], 1, 1) +
		#        SUBSTRING(u.[LastName], 1, 1) AS Initials,
		# 	   Parts,
		# 	   [DateTime],
		# 	   [Notes],
		# 	   [Status]
		# 	   From PyComm
		# 	   Inner join Users u
		# on Operator = u.Username
		# Where[Status] = 'Queued' AND Operation = 'QC' AND Parts != '') q
		# Order by q.[Suffix] ASC, q.[DateTime] ASC
		# unit_data = mssql.query(f"SELECT TOP 1 * FROM PyComm WHERE [Suffix] = '{sorted_sfx_queue[0]}' AND [Status] = 'Queued' AND [Operation] {mod} 'QC' ORDER BY [DateTime] ASC")
		unit_data = mssql.query(f"SELECT TOP 1 * FROM PyComm WHERE [Suffix] = '{sorted_sfx_queue[0]}' AND [Status] = 'Queued' AND [Operation] {mod} 'QC' ORDER BY [DateTime] DESC")
		unit = Unit(**unit_data)
		if unit.operation == 'QC':
			reason_check = mssql.query(f"SELECT * FROM PyComm WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Reason'")
			if reason_check:
				mssql.modify(f"UPDATE PyComm SET [Status] = 'Paused Queue' WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Queued' AND [Id] = {int(unit.id)}")
				continue
		log.info("Unit data found:")
		log.info(f"SN: {unit_data['Serial Number']}, Build: {unit_data['Build']}, Suffix: {unit_data['Suffix']}, Notes: {unit_data['Notes']}")
		log.info(f"DateTime: {unit_data['DateTime']}, Operation: {unit_data['Operation']}, Operator: {unit_data['Operator']}, Parts: {unit_data['Parts']}")
		if not dev_mode:
			mssql.modify(f"UPDATE PyComm SET [Status] = 'Started' WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Queued' AND [Id] = {int(unit.id)}")
		try:
			app.add_form('UnitsForm')
			Units = app.UnitsForm
			timer.start()
			# Opens unit
			_try_unit(unit, app)
			app.write_data('Units')
			Units.owner_history_tab.select()
			Units.owner_history_tab.grid.sort_with_header('Eff Date')
			Units.owner_history_tab.grid.populate('Eff Date', 1)
			Units.owner_history_tab.grid.select_cell('Eff Date', 1)
			min_date = Units.owner_history_tab.grid.cell
			log.debug(f"Received date found: {min_date}")
			sro_count = _open_first_open_sro(unit, app)
			SRO_Lines = app.ServiceOrderLinesForm
			SRO_Operations = app.ServiceOrderOperationsForm
			app.write_data('SROOperations')
			part_count = 0
			if unit.parts:
				log.debug("Opening SRO Transactions form")
				SRO_Operations.sro_transactions.click()
				app.add_form('SROTransactionsForm')
				# app.__preinit__(4)
				SRO_Transactions = app.SROTransactionsForm
				log.debug("Waiting for SRO Transactions form...")
				# SRO_Transactions.apply_filter.ready()
				log.debug("SRO Transactions form opened")
				log.debug("Setting Date Range Start")
				app.write_data('SROTransactions')
				SRO_Transactions.date_range_start.set_text(min_date)
				SRO_Transactions.apply_filter.click()
				max_rows = SRO_Transactions.grid.rows-1
				posted = []
				SRO_Transactions.post_batch.ready()
				log.debug("Checking for already-posted items")
				if max_rows > 0:
					SRO_Transactions.grid.populate(('Posted', 'Item'), range(1, max_rows+1), visible_only=True)
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
					# SRO_Transactions.post_batch.ready()
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
				app.enter()
				while app.popup.exists():
					log.debug("Close pop-up")
					app.popup.close_alt_f4()
					sleep(0.2)
				for i,part in zip(range(1, count+1), new_parts_list):
					SRO_Transactions.grid.select_cell('Location', i)
					SRO_Transactions.grid.click_cell()
					while app.popup.exists():
						log.debug("Close pop-up")
						app.popup.close_alt_f4()
						sleep(0.2)
					log.debug(f"Entering Location: {part.location} for part {part.part_number}")
					SRO_Transactions.grid.cell = part.location
				app.enter()

				while app.popup.exists():
					log.debug("Close pop-up")
					app.popup.close_alt_f4()
					sleep(0.2)

				if not dev_mode:
					app.save()

				while app.popup.exists():
					log.debug("Close pop-up")
					app.popup.close_alt_f4()
					sleep(0.2)
				app.wait('ready')
				log.debug("Posting batch")
				SRO_Transactions.post_batch.ready()
				if dev_mode:
					app.cancel_close.click()  #####
					app.cancel_close.click()  #####
				else:
					part_count = len(new_parts_list)
					SRO_Transactions.post_batch.ready()
					SRO_Transactions.post_batch.click()
					while app.popup.exists():
						log.debug("Close pop-up")
						app.popup.enter()
						sleep(0.2)
					while app.popup.exists():
						log.debug("Close pop-up")
						app.enter()
						sleep(2)
					app.save_close.click()
					app.save_close.click()
				log.debug("Waiting for Service Order Lines form...")
				SRO_Lines.sro_operations.ready()
				log.debug("Service Order Lines form opened")
				log.debug("Opening Service Order Operations form")
				SRO_Lines.sro_operations.click()
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
					# value = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")  ####???
					value = value[0].strftime("%m/%d/%Y %I:%M:%S %p")
				log.debug(f"Entering Floor Date: {value}")
				SRO_Operations.general_tab.floor_date.set_text(value)
			if unit.operation == 'QC' and not cp_d:
				log.debug(f"Entering Complete Date: {unit.datetime.strftime('%m/%d/%Y %I:%M:%S %p')}")
				SRO_Operations.general_tab.complete_date.set_text(unit.datetime.strftime("%m/%d/%Y %I:%M:%S %p"))
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
				if (part.part_number in posted) or (part.part_name is None) or (part.part_name == 'None'):
					continue
				SRO_Operations.reasons_tab.resolution_notes.send_keystrokes(f"[{part.part_name}], ")
				count += 1
			if count > 0:
				SRO_Operations.reasons_tab.resolution_notes.send_keystrokes('{BACKSPACE}{BACKSPACE}{ENTER}')
			SRO_Operations.reasons_tab.resolution_notes.send_keystrokes(f"[{unit.operator_initials} {unit.datetime.strftime('%m/%d/%Y')}]")
			is_closed_status = 'not '
			if unit.operation == 'QC':
				# Fill out Reasons Grid
				row = SRO_Operations.reasons_tab.grid.rows
				SRO_Operations.reasons_tab.grid.populate(('General Reason', 'Specific Reason', 'General Resolution', 'Specific Resolution'), rows=row - 1)
				SRO_Operations.reasons_tab.grid.select_cell('General Reason', row - 1)
				if not SRO_Operations.reasons_tab.grid.cell:  # ???
					raise ValueError
				SRO_Operations.reasons_tab.grid.select_cell('Specific Reason', row - 1)
				if not SRO_Operations.reasons_tab.grid.cell:
					SRO_Operations.reasons_tab.grid.cell = 20
				SRO_Operations.reasons_tab.grid.select_cell('General Resolution', row - 1)
				if not SRO_Operations.reasons_tab.grid.cell:
					SRO_Operations.reasons_tab.grid.cell = 10000
				SRO_Operations.reasons_tab.grid.select_cell('Specific Resolution', row - 1)
				if not SRO_Operations.reasons_tab.grid.cell:
					SRO_Operations.reasons_tab.grid.cell = 100

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
					SRO_Operations.reasons_tab.reason_notes.send_keystrokes('[UDI]{ENTER}')
				SRO_Operations.reasons_tab.reason_notes.send_keystrokes('[PASSED ALL TESTS]')

				SRO_Operations.status = 'Closed'
				is_closed_status = ''
		except pag.FailSafeException:
			log.error("Failsafe triggered!")
			mssql.modify(f"UPDATE PyComm SET [Status] = 'Queued' WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Started' AND [Id] = {int(unit.id)}")
			app.cancel_close.click()
			app.cancel_close.click()
			app.cancel_close.click()
			app.cancel_close.click()
			quit()
		except UnitClosedError:
			log.error("No open SROs found")
			mssql.modify(f"UPDATE PyComm SET [Status] = 'No Open SRO' WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Started' AND [Id] = {int(unit.id)}")
			app.cancel_close.click()
			app.cancel_close.click()
			app.cancel_close.click()
			app.cancel_close.click()
			app.open_form("Units")
		except Exception:
			log.exception("Something went horribly wrong")
			if not dev_mode:
				mssql.modify(f"UPDATE PyComm SET [Status] = 'Skipped' WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Started' AND [Id] = {int(unit.id)}")
			else:
				quit()
			app.cancel_close.click()
			app.cancel_close.click()
			app.cancel_close.click()
			app.cancel_close.click()
			app.open_form("Units")
		else:
			if dev_mode:
				app.cancel_close.click()
				app.cancel_close.click()
			else:
				app.save_close.click()
				app.save_close.click()
				Units._unit.set_focus()
				Units._unit.set_keyboard_focus()
				Units._unit.send_keystrokes('{F4}')
				Units._unit.send_keystrokes('{F5}')
				mssql.modify(f"DELETE FROM PyComm WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Started' AND [Id] = {int(unit.id)}")
				log.info(f"Unit {unit.serial_number_prefix}{unit.serial_number} completed")
				end_time = timer.stop()
				sro_string = part_string = ""
				if sro_count > 1:
					sro_string = f" {sro_count} SROs tried,"
				if part_count < len(unit.parts):
					part_string = f" {part_count} out of {len(unit.parts)} parts transacted,"
				elif part_count > 0:
					part_string = f" {part_count} parts transacted,"
				time_log.info(f"Unit {unit.serial_number_prefix}{unit.serial_number} completed,{sro_string}{part_string} status {is_closed_status}closed, total time {end_time}")


def query(app: Application):
	log.debug("Query script started")
	log.debug("Opening Units form")
	app.open_form('Units')
	Units = app.UnitsForm
	log.debug("Unit form opened")
	while True:
		# try:
		log.debug("Checking queued Queries")
		unit_data = mssql.query(f"SELECT TOP 1 * FROM PyComm WHERE [Status] = 'Request' ORDER BY [DateTime] ASC")
		if not unit_data:
			log.debug("No queued Queries found")
			continue
		log.debug(f"Queued Queries found")
		log.debug("Receiving unit data")
		unit = Unit(**unit_data)
		log.info("Unit data found:")
		log.info(f"SN: {unit_data['Serial Number']}, Build: {unit_data['Build']}, Suffix: {unit_data['Suffix']}, Notes: {unit_data['Notes']}")
		log.info(f"DateTime: {unit_data['DateTime']}, Operation: {unit_data['Operation']}, Operator: {unit_data['Operator']}, Parts: {unit_data['Parts']}")
		log.debug("Unit Started")
		try:
			sn = unit.serial_number_prefix + unit.serial_number
		except (ValueError, KeyError):
			mode = 'esn'
			esn = unit.esn = unit.serial_number
			unit.serial_number = None
		else:
			mode = 'item'
		Units.unit_data_tab.select()
		if mode == 'esn':
			Units.unit_data_tab.esn.set_text(unit.esn)
			app.apply_filter()
			item = Units.item.text()
			sn = Units.serial_number
			app.apply_filter()
			app.refresh_filter()
		elif mode == 'item':
			Units.serial_number = sn
			app.apply_filter()
			item = Units.item.text()
			esn = Units.unit_data_tab.esn.test()
			app.apply_filter()
			app.refresh_filter()
		try:
			if sn[2] in letters:
				sn2 = sn[3:]
			else:
				sn2 = sn[2:]
		except IndexError:
			sn2 = 'No SL Data'
			esn = 'No SL Data'
		if item.endswith('M'):
			sfx = 'Monitoring'
		elif item.endswith('DEMO'):
			sfx = 'Demo'
		elif item.endswith('R'):
			sfx = 'Refurb'
		elif len(item) > 0:
			sfx = 'Direct'
		else:
			sfx = 'No SL Data'

		if 'V' in item[3:]:
			carrier = 'Verizon'
		elif 'S' in item[3:]:
			carrier = 'Sprint'
		else:
			carrier = 'None'
		build = (item[:3]+item[3:].replace('S', '').replace('V', '')).strip()
		if not build:
			build = 'No SL Data'

		row = mssql.query(f"SELECT * FROM UnitData WHERE [SerialNumber] = '{sn2}'")
		if row:
			mssql.modify(f"UPDATE UnitData SET [ItemNumber] = '{build}',[Carrier] = '{carrier}',[Date] = GETDATE(),[Suffix] = '{sfx}',[ESN] = '{esn}',[SyteLineData] = 1 WHERE [SerialNumber] = '{sn2}'")
		else:
			mssql.modify(f"INSERT INTO UnitData ([SerialNumber],[ItemNumber],[Carrier],[Date],[Suffix],[ESN],[SyteLineData]) VALUES ('{sn2}','{build}','{carrier}',GETDATE(),'{sfx}','{esn}',1)")
		Units._unit.set_focus()
		Units._unit.set_keyboard_focus()
		Units._unit.send_keystrokes('{F4}')
		Units._unit.send_keystrokes('{F5}')
		mssql.modify(f"DELETE FROM PyComm WHERE [Id] = {unit.id} AND [Status] = 'Request'")


def reason(app: Application):
	log.debug("Reason Code script started")
	log.debug("Opening Units form")
	app.open_form('Units')
	log.debug("Unit form opened")
	sleep_counter = 0
	# 32923,705
	while True:
		Units = app.UnitsForm
		# try:
		log.debug("Checking queued Reason Codes")
	# Select TOP 1 p.[Serial Number],
	# 	p.Suffix, p.Operation,
	# 	p.[Datetime], p.Notes,
	# 	f.Failure,
	# 	SUBSTRING(u.[FirstName], 1, 1) +
	# 	SUBSTRING(u.[LastName], 1, 1) AS Initials
	# 	from PyComm p
	# Inner join FailuresRepairs f
	# on p.Notes = f.ReasonCodes
	# Inner Join Users u
	# on p.Operator = u.Username
	# Where p.[Status] = 'Reason'
	# Order by[DateTime] ASC

		# unit_data = mssql.query("Select TOP 1 p.*, f.Failure from PyComm p Inner join FailuresRepairs f on p.Notes = f.ReasonCodes Where p.[Status] = 'Reason' Order by[DateTime] ASC")
		unit_data = mssql.query(f"SELECT TOP 1 * FROM PyComm WHERE [Status] = 'Reason' ORDER BY [DateTime] ASC")
		if not unit_data:
			log.debug("No queued Reason Codes found")
			if sleep_counter > 16:
				sleep(60)
			elif sleep_counter > 10:
				sleep(10)
			else:
				sleep(1)
			sleep_counter += 1
			continue
		log.debug(f"Queued Reason Codes found")
		log.debug("Receiving unit data")
		sleep_counter = 0
		unit = Unit(**unit_data)
		log.info("Unit data found:")
		log.info(f"SN: {unit_data['Serial Number']}, Build: {unit_data['Build']}, Suffix: {unit_data['Suffix']}, Notes: {unit_data['Notes']}")
		log.info(f"DateTime: {unit_data['DateTime']}, Operation: {unit_data['Operation']}, Operator: {unit_data['Operator']}, Parts: {unit_data['Parts']}")
		if not dev_mode:
			mssql.modify(f"UPDATE PyComm SET [Status] = 'Started' WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Reason' AND [Id] = {int(unit.id)}")
		try:
			app.add_form('UnitsForm')
			Units = app.UnitsForm
			log.debug("Unit Started")
			_try_unit(unit, app)
			xml_helpers.WriteDialogToFile('Units.xml', app._win.wrapper_object())
			_open_first_open_sro(unit, app)
			xml_helpers.WriteDialogToFile('SROOperations.xml', app._win.wrapper_object())
			SRO_Operations = app.ServiceOrderOperationsForm
			if 'Initial' in unit.operation:
				SRO_Operations.general_tab.initiate_controls()
				rc_d = SRO_Operations.general_tab.received_date
				if not rc_d.text():
					log.debug("No Received Date found")
					now = datetime.datetime.now()
					rc_d.set_text(now.strftime("%m/%d/%Y 12:00:00 AM"))
				else:
					log.debug(f"Received Date found: {rc_d}")
				fl_d = SRO_Operations.general_tab.floor_date
				if not fl_d.text():
					log.debug("No Floor Date found")
					fl_d.set_text(unit.datetime.strftime("%m/%d/%Y %I:%M:%S %p"))
					fa_d = SRO_Operations.general_tab.fa_date
					if not fa_d.text():
						fa_d.set_text(unit.datetime.strftime("%m/%d/%Y %I:%M:%S %p"))
				else:
					log.debug(f"Flood Date found: {fl_d.text()}")
				if dev_mode:
					app.cancel_close.click()
				else:
					app.save_close.click()
				app.add_form('ServiceOrderLinesForm')
				SRO_Lines = app.ServiceOrderLinesForm
				log.debug("Waiting for Service Order Lines form...")
				SRO_Lines.sro_operations.ready()
				log.debug("Service Order Lines form opened")
				log.debug("Opening Service Order Operations form")
				SRO_Lines.sro_operations.click()
				app.add_form('ServiceOrderOperationsForm')
				log.debug("Waiting for Service Order Operations form...")
				SRO_Operations.general_tab.ready()
				log.debug("Service Order Operations form opened")
			SRO_Operations.reasons_tab.select()
			row = SRO_Operations.reasons_tab.grid.rows
			SRO_Operations.reasons_tab.grid.populate(('General Reason', 'Specific Reason', 'General Resolution'), row-1)
			SRO_Operations.reasons_tab.grid.select_cell('General Reason', row-1)
			gen_rsn = SRO_Operations.reasons_tab.grid.cell
			gen_rso, spec_rso = unit.notes.split(',')
			SRO_Operations.reasons_tab.grid.select_cell('General Resolution', row-1)
			if SRO_Operations.reasons_tab.grid.cell:  # If last row filled, append new row
				# gen_rsn, spec_rsn, gen_rso, spec_rso = unit.notes.split(',')
				gen_rsn = str(gen_rsn).strip(' ')
				spec_rsn = '20'
				# spec_rsn = spec_rsn.strip(' ')
				gen_rso = gen_rso.strip(' ')
				spec_rso = spec_rso.strip(' ')
				SRO_Operations.reasons_tab.grid.select_cell('General Reason', row)
				SRO_Operations.reasons_tab.grid.cell = gen_rsn
				SRO_Operations.reasons_tab.grid.select_cell('Specific Reason', row)
				SRO_Operations.reasons_tab.grid.cell = spec_rsn
				SRO_Operations.reasons_tab.grid.select_cell('General Resolution', row)
				SRO_Operations.reasons_tab.grid.cell = gen_rso
				SRO_Operations.reasons_tab.grid.select_cell('Specific Resolution', row)
				SRO_Operations.reasons_tab.grid.cell = spec_rso
			else:  # Else, fill last row
				SRO_Operations.reasons_tab.grid.select_cell('Specific Reason', row-1)
				if not SRO_Operations.reasons_tab.grid.cell:
					spec_rsn = '20'
					SRO_Operations.reasons_tab.grid.cell = spec_rsn
				SRO_Operations.reasons_tab.grid.select_cell('General Resolution', row-1)
				SRO_Operations.reasons_tab.grid.cell = gen_rso
				SRO_Operations.reasons_tab.grid.select_cell('Specific Resolution', row-1)
				SRO_Operations.reasons_tab.grid.cell = spec_rso

			SRO_Operations.reasons_tab.reason_notes.set_focus()
			SRO_Operations.reasons_tab.reason_notes.set_keyboard_focus()
			SRO_Operations.reasons_tab.reason_notes.send_keystrokes("^{END}")
			if int(gen_rso) == 10000 and int(spec_rso) == 100:
				SRO_Operations.reasons_tab.reason_notes.send_keystrokes("[POWER UP OK]")
				SRO_Operations.reasons_tab.reason_notes.send_keystrokes("{ENTER}")
				SRO_Operations.reasons_tab.reason_notes.send_keystrokes("[ACCEPTED]")
			else:
				failure = mssql.query(f"SELECT TOP 1 [Failure] FROM FailuresRepairs WHERE [Product] = '{unit.product}' AND [ReasonCodes] = '{unit.notes}'")[0]
				SRO_Operations.reasons_tab.reason_notes.send_keystrokes(f"[{failure}]")
			SRO_Operations.reasons_tab.resolution_notes.set_focus()
			SRO_Operations.reasons_tab.resolution_notes.set_keyboard_focus()
			SRO_Operations.reasons_tab.resolution_notes.send_keystrokes("^{END}")
			SRO_Operations.reasons_tab.resolution_notes.send_keystrokes(f"[{unit.operator_initials} {unit.datetime.strftime('%m/%d/%Y')}]")
		except pag.FailSafeException:
			log.error("Failsafe triggered!")
			mssql.modify(f"UPDATE PyComm SET [Status] = 'Reason' WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Started' AND [Id] = {int(unit.id)}")
			app.cancel_close.click()
			app.cancel_close.click()
			app.cancel_close.click()
			app.cancel_close.click()
			quit()
		except UnitClosedError:
			log.error("No open SROs found")
			mssql.modify(f"UPDATE PyComm SET [Status] = 'No Open SRO(Reason)' WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Started' AND [Id] = {int(unit.id)}")
			app.cancel_close.click()
			app.cancel_close.click()
			app.cancel_close.click()
			app.cancel_close.click()
			app.open_form("Units")
		except Exception:
			log.exception("Something went horribly wrong")
			if not dev_mode:
				mssql.modify(f"UPDATE PyComm SET [Status] = 'Skipped(Reason)' WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Started' AND [Id] = {int(unit.id)}")
			else:
				mssql.modify(f"UPDATE PyComm SET [Status] = 'Started(Reason)' WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Started' AND [Id] = {int(unit.id)}")
				quit()
			app.cancel_close.click()
			app.cancel_close.click()
			app.cancel_close.click()
			app.cancel_close.click()
			app.open_form("Units")
		else:
			if dev_mode:
				app.cancel_close.click()
				app.cancel_close.click()
			else:
				app.save_close.click()
				app.save_close.click()
				Units._unit.set_focus()
				Units._unit.set_keyboard_focus()
				Units._unit.send_keystrokes('{F4}')
				Units._unit.send_keystrokes('{F5}')
				mssql.modify(f"UPDATE PyComm SET [Status] = 'Queued' WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Paused Queue'")
				mssql.modify(f"DELETE FROM PyComm WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Started' AND [Id] = {int(unit.id)}")
				log.info(f"Unit {unit.serial_number_prefix}{unit.serial_number} completed")


def scrap(app: Application):
	log.debug("Scrap script started")

	log.debug("Opening Miscellaneous Issue form")
	app.open_form('Miscellaneous Issue')
	MiscIssue = app.MiscellaneousIssueForm
	log.debug("Miscellaneous Issue form opened")
	sleep(0.5)
	log.debug("Opening Units form")
	app.open_form('Units')
	Units = app.UnitsForm
	log.debug("Unit form opened")

	log.debug("Opening Serial Numbers form")
	app.open_form('Serial Numbers')
	SrlNum = app.SerialNumbersForm
	log.debug("Serial Numbers form opened")
	for item in app.window_menu.items():
		text = item.texts()[0]
		if 'Units' in text:
			UnitsFormFocus = item
		elif 'Miscellaneous Issue' in text:
			MiscIssueFormFocus = item
		elif 'Serial Numbers' in text:
			SrlNumFormFocus = item
	# NotesFormFocus = None
	while True:
		log.debug("Checking queued scrap units")
		all_unit_data = mssql.query("SELECT * FROM PyComm WHERE [Status] = 'Scrap'", fetchall=True)
		if not all_unit_data:
			continue
		log.debug("Receiving unit data")
		all_units = set(map(lambda x: Unit(**x), all_unit_data))
		log.info(f"Units data found: {len(all_units)}")
		if not dev_mode:
			for unit in all_units:
				mssql.modify(f"UPDATE PyComm SET [Status] = 'Started' WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Scrap' AND [Id] = {int(unit.id)}")
		try:
			timer.start()
			all_units_grouped = _group_units_by_build(all_units)
			log.debug(f"Units split into {len(all_units_grouped.keys())} group(s)")
			sorted_keys = sorted(all_units_grouped.keys(), key=lambda x: len(all_units_grouped[x]), reverse=True)
			sorted_unit_groups = dict(zip(sorted_keys, map(lambda x: all_units_grouped[x], sorted_keys)))  # Sorts unit groups by quantity in descending order
			log.debug("Units sorted by quantity in descending order")
			for i,(key,group) in enumerate(sorted_unit_groups.items()):
				log.debug(f"Group {i+1}: {key} build, {len(group)} unit(s)")
			# skipped_units = Default_Lictionary(list)
			for build,units in sorted_unit_groups.items():
				if build in cellular_unit_builds:
					phone = True
				else:
					phone = False
				unit_locations = defaultdict(list)
				SrlNumFormFocus.select()
				app.add_form('SerialNumbersForm')
				SrlNum = app.SerialNumbersForm
				for unit in units:
					_try_serial(unit, app)
					status = SrlNum.status.texts()[0]
					log.debug(f"Unit location status '{status}' found for unit {unit.serial_number_prefix + unit.serial_number}")
					if status != 'Out of Inventory':  # OR   status == 'In Inventory' ???
						location = SrlNum.location.text()
						unit_locations[location].append(unit)
						log.debug(f"Unit location '{location}' found for unit {unit.serial_number_prefix + unit.serial_number}")
					sleep(0.1)
					SrlNum.serial_number.send_keystrokes('{F4}')
					SrlNum.serial_number.send_keystrokes('{F5}')
					sleep(0.1)
				MiscIssueFormFocus.select()
				app.add_form('MiscellaneousIssueForm')
				MiscIssue = app.MiscellaneousIssueForm
				MiscIssue.item.set_text(build)
				for location,units in unit_locations.items():
					MiscIssue.detail_tab.select()
					MiscIssue.detail_tab.location.set_text(location)
					MiscIssue.detail_tab.quantity.set_text(float(len(units)))
					sleep(0.5)
					kbd.SendKeys('{TAB}')
					sleep(0.5)
					if build.count('-') < 2:  # If direct units
						reason = "24"
					else:
						reason = "22"
					MiscIssue.detail_tab.reason.set_text(reason)
					MiscIssue.detail_tab.document_number.set_text(f"SCRAP {units[0].operator_initials}")
					sleep(0.5)
					MiscIssue.serial_numbers_tab.select()
					sleep(0.5)
					MiscIssue.serial_numbers_tab.generate_qty.set_text("9999999")
					kbd.SendKeys("%g")  # Generate button, (ALT + G)
					kbd.SendKeys("{RIGHT}")
					for unit in sorted(units, key=lambda x: int(x.serial_number)):  # Sorts units by serial number in descending order
						app.find_value_in_collection(collection='SLSerials', property='S/N (SerNum)', value=unit.serial_number)
						if app.popup.exists(1, 2):
							# skipped_units[build].append(unit)
							app.enter()
							log.debug(f"Added unit {unit.serial_number_prefix + unit.serial_number} to skipped list")
							continue
						sleep(0.2)
						kbd.SendKeys("{LEFT}")
						sleep(0.2)
						kbd.SendKeys("{SPACE}")
						sleep(0.2)
						kbd.SendKeys("{RIGHT}")
						sleep(0.2)
					if dev_mode:
						app.cancel_close.click()
						app.open_form('Miscellaneous Issue')
						MiscIssue = app.MiscellaneousIssueForm
					else:
						pag.hotkey('alt', 'r')
						pag.press('enter')
						# kbd.SendKeys("%r")  # Process button, (ALT + R)
				pag.keyUp('ctrlleft')
				pag.keyUp('ctrlright')
				pag.keyUp('ctrl')
				log.debug("Step 2 Complete")
				UnitsFormFocus.select()
				app.add_form('UnitsForm')
				Units = app.UnitsForm
				log.debug("Step 3 Started")
				for unit in all_units:
					try:
						log.debug(f"Running Step 3 on unit {unit.serial_number_prefix + unit.serial_number}")
						# if unit in skipped_units:
						# 	log.debug(f"Skipping Step 3 on unit {unit.serial_number_prefix + unit.serial_number}, it's in the skipped list")
							# continue
						Units._unit.set_focus()
						Units._unit.set_keyboard_focus()
						Units._unit.send_keystrokes(unit.serial_number_prefix+unit.serial_number)
						log.debug(f"Serial number {unit.serial_number_prefix+unit.serial_number} entered")
						kbd.SendKeys("{F4}")
						app.add_form('UnitsForm')
						Units = app.UnitsForm
						Units.custmer.set_text('302')
						log.debug("Customer set to 302")
						moveTo(*Units.change_status.coordinates.center)
						pag.click()
						log.debug("Change status clicked")
						sleep(0.5)
						kbd.SendKeys("%y")  # Yes button, (ALT + Y)
						log.debug("4")
						if phone:
							scrap_code = 'SCRAPPED1'
						else:
							scrap_code = 'SCRAPPED'
						Units.unit_status_code.set_text(scrap_code)
						log.debug(f"Unit Status Code set to {scrap_code}")
						if phone:
							ship_num = "2"
						else:
							ship_num = "1"
						Units.ship_to.set_text(ship_num)
						log.debug(f"Ship To set to {ship_num}")
						if not dev_mode:
							kbd.SendKeys("^s")
						pag.keyUp('ctrlleft')
						pag.keyUp('ctrlright')
						pag.keyUp('ctrl')
						sleep(1)
						sro_count = _open_first_open_sro(unit, app)
						SRO_Operations = app.ServiceOrderOperationsForm
						SRO_Operations.reasons_tab.select()
						row = SRO_Operations.reasons_tab.grid.rows
						SRO_Operations.reasons_tab.grid.populate(('General Reason', 'Specific Reason', 'General Resolution'), row - 1)
						SRO_Operations.reasons_tab.grid.select_cell('General Reason', row - 1)
						gen_rsn = SRO_Operations.reasons_tab.grid.cell
						gen_rso, spec_rso = unit.notes.split(',')
						SRO_Operations.reasons_tab.grid.select_cell('General Resolution', row - 1)
						if SRO_Operations.reasons_tab.grid.cell:  # If last row filled, append new row
							# gen_rsn, spec_rsn, gen_rso, spec_rso = unit.notes.split(',')
							gen_rsn = str(gen_rsn).strip(' ')
							spec_rsn = '20'
							# spec_rsn = spec_rsn.strip(' ')
							gen_rso = gen_rso.strip(' ')
							spec_rso = spec_rso.strip(' ')
							SRO_Operations.reasons_tab.grid.select_cell('General Reason', row)
							SRO_Operations.reasons_tab.grid.cell = gen_rsn
							sleep(10)
							SRO_Operations.reasons_tab.grid.select_cell('Specific Reason', row)
							SRO_Operations.reasons_tab.grid.cell = spec_rsn
							SRO_Operations.reasons_tab.grid.select_cell('General Resolution', row)
							SRO_Operations.reasons_tab.grid.cell = gen_rso
							SRO_Operations.reasons_tab.grid.select_cell('Specific Resolution', row)
							SRO_Operations.reasons_tab.grid.cell = spec_rso
						else:  # Else, fill last row
							SRO_Operations.reasons_tab.grid.select_cell('Specific Reason', row - 1)
							if not SRO_Operations.reasons_tab.grid.cell:
								spec_rsn = '20'
								SRO_Operations.reasons_tab.grid.cell = spec_rsn
							SRO_Operations.reasons_tab.grid.select_cell('General Resolution', row - 1)
							SRO_Operations.reasons_tab.grid.cell = gen_rso
							SRO_Operations.reasons_tab.grid.select_cell('Specific Resolution', row - 1)
							SRO_Operations.reasons_tab.grid.cell = spec_rso
						spec_rso_name = spec_rso_codes.get(spec_rso, 'SCRAP')
						gen_rso_name = mssql.query(f"SELECT TOP 1 [Failure] FROM FailuresRepairs WHERE [Product] = '{unit.product}' AND [ReasonCodes] = '{unit.notes}'")[0]
						SRO_Operations.reasons_tab.reason_notes.set_focus()
						SRO_Operations.reasons_tab.reason_notes.set_keyboard_focus()
						SRO_Operations.reasons_tab.reason_notes.send_keystrokes("^{END}")
						if SRO_Operations.reasons_tab.reason_notes.texts()[-1] != '':
							SRO_Operations.reasons_tab.reason_notes.send_keystrokes("{ENTER}")
						SRO_Operations.reasons_tab.reason_notes.send_keystrokes(f"[{spec_rso_name.upper()} {gen_rso_name.upper()}]")
						SRO_Operations.reasons_tab.reason_notes.send_keystrokes("{ENTER}")
						SRO_Operations.reasons_tab.reason_notes.send_keystrokes(f"[{unit.operator_initials} {unit.datetime.strftime('%m/%d/%Y')}]")
						SRO_Operations.status = 'Closed'
						is_closed_status = ''
						if dev_mode:
							app.cancel_close.click()
							app.cancel_close.click()
						else:
							app.save_close.click()
							app.save_close.click()
						# if NotesButton is None:
						# 	for item in app.actions_menu.items():
						# 		text = item.text()[0]
						# 		if 'Notes for Current' in text:
						# 			NotesButton = item
						# NotesFormFocus.select()
						sleep(0.5)
						kbd.SendKeys('%s')  # Actions Menu, (ALT + S)
						sleep(0.2)
						kbd.SendKeys('o')  # Notes For Current, (O)
						sleep(0.5)
						app.find_value_in_collection(collection='Object Notes', property='Subject (DerDesc)', value='NOTES', case_sensitive=True)
						while app.popup.exists():
							app.popup.close_alt_f4()
							app.find_value_in_collection(collection='Object Notes', property='Subject (DerDesc)', value='')
							kbd.SendKeys('NOTES')
						note_txt = app._win2.child_window(auto_id='DerContentEdit')
						note_txt.set_focus()
						note_txt.click_input()
						note_txt.type_keys('^{END}')
						text = fr"{note_txt.legacy_properties()['Value'].strip(' ')}"
						if not ((text.endswith(r'\n') or text.endswith(r'\r')) or (text == '')):
							note_txt.type_keys('{ENTER}')
						note_txt.type_keys(f"[{spec_rso_name}")
						note_txt.type_keys("[{SPACE}]")
						note_txt.type_keys(f"{gen_rso_name}]")
						note_txt.type_keys("{ENTER}")
						note_txt.type_keys(f"[{unit.operator_initials}")
						note_txt.type_keys("[{SPACE}]")
						note_txt.type_keys(f"{unit.datetime.strftime('%m/%d/%Y')}]")
						if dev_mode:
							app.cancel_close.click()
						else:
							app.save_close.click()
						kbd.SendKeys("{F4}")
						kbd.SendKeys("{F5}")
					except UnitClosedError:
						log.exception("No open SROs")
						if not dev_mode:
							continue
							# mssql.modify(f"UPDATE PyComm SET [Status] = 'Skipped(Scrap)' WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Started' AND [Id] = {int(unit.id)}")
						continue
						kbd.SendKeys("{F4}")
						kbd.SendKeys("{F5}")
						kbd.SendKeys("%y")
					else:
						if not dev_mode:
							mssql.modify(f"UPDATE ScrapLog SET [SL8_Status] = 'Closed' WHERE [SL8_Status] = 'Open' AND [SerialNumber] = '{unit.serial_number}'")
							mssql.modify(f"DELETE FROM PyComm WHERE [Id] = {unit.id} AND [Serial Number] = '{unit.serial_number}' AND [Status] = 'Started'")
		except Exception:
			log.exception(f"Something went horribly wrong!")
			if not dev_mode:
				for unit in all_units:
					mssql.modify(f"UPDATE PyComm SET [Status] = 'Skipped(Scrap)' WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Started' AND [Id] = {int(unit.id)}")
			quit()
		else:
			end_time = timer.stop()

			if len(unit_locations.keys()) > 0:
				total = 0
				for u in unit_locations.values():
					total += len(u)
				begin_string = f"{total} unit(s) processed through Miscellaneous Issue, "
				if len(all_units_grouped.keys()) > 1:
					begin_string += f"seperated into {len(all_units_grouped.keys())} different groups by build, "
				if len(unit_locations.keys()) > 1:
					begin_string += f"from {len(unit_locations.keys())} different locations, "
				begin_string += f"and {len(all_units)} units fully scrapped through the Units form."
			else:
				begin_string = f"{len(all_units)} units fully scrapped through the Units form."
			time_log.info(f"{begin_string} Total time {end_time}")

	# If Out of Inventory then: ???
	# Open Miscellaneous Issue Form
	# For each group:

	#   Input Build ('LC-800V-M', etc) into Item textbox
	#           Click Generate button(also: alt+g)
	#           For each serial number, in ascending order:
	#               Find Value In Collection menu item(also: alt+e, v)
	#               In Find window:
	#                   If popup, unit doesn't exist
	#       Click Process button(also: alt+r)
	#       Any popups???

	# Open Units Form
	# For each serial number:
	#   Input serial number into Unit textbox
	#   Press 'F4'
	#   Input "302" into Customer textbox
	#   Input "1" for non-phone or "2" for phone into Ship To textbox

	#   Click Change Status button
	#   In Popup titled "hh4q0kfi":     ("Are you sure you want to change the unit status?" text)
	#       Click Yes button (Alt + Y)
	#   Input "SCRAPPED" for non-phone or "SCRAPPED1" for phone into Unit Status Code textbox
	#   Save
	#   In Service History Tab:
	#       Find first open SRO
	#       If there are none open: ???
	#       Click View button
	#       In Service Order Lines Form:
	#           Click Service Order Operations button
	#           In Service Order Operations Form:
	#               In Reasons tab:
	#                   Input General Resolution and Specific Resolution???
	#                   Name1 = General Resolution Fault Code Name
	#                   Name2 = Specific Resolution Fault Code Name(Usually "SCRAP")
	#                   Input "{Name2} {Name1}\n{Initials} {datetime.date}"
	#               Close Unit
	#               Save Close Form
	#   Click Notes button

	#   In Notes Form:
	#       Find Value In Collection menu item(also: alt+e, v)
	#       In Find window:
	#           Input "NOTES" into Find textbox
	#           Input "Object Notes" into In Collection textbox
	#           Input "Subject (DerDesc)" into In Property textbox
	#           Click Case Sensitive checkbox to toggle from unchecked -> checked
	#           Click OK button
	#       If popup happens(NOTES doesn't exist):
	#           Find Value In Collection menu item(also: alt+e, v)
	#           In Find window:
	#               Input "" into Find textbox
	#               Input "Object Notes" into In Collection textbox
	#               Input "Subject (DerDesc)" into In Property textbox
	#               Click OK button
	#           Typewrite "NOTES"
	#       Input(append) "{Name2} {Name1}\n{Initials} {datetime.date}" into Note("A&ttach  File...Edit") textbox
	#       Save Close Form
	# TODO: Scrap report
cellular_unit_builds = ['EX-600-M', 'EX-625S-M', 'EX-600-T', 'EX-600', 'EX-625-M', 'EX-600-DEMO', 'EX-600S', 'EX-600S-DEMO', 'EX-600V-M',
						'EX-600V', 'EX-680V-M', 'EX-600V-DEMO', 'EX-680V', 'EX-680S', 'EX-680V-DEMO', 'EX-600V-R', 'EX-680S-M', 'HG-2200-M',
						'CL-4206-DEMO', 'CL-3206-T', 'CL-3206', 'CL-4206', 'CL-4206', 'CL-3206-DEMO', 'CL-4206-M', 'CL-3206-M', 'HB-110',
						'HB-110-DEMO', 'HB-110-M', 'HB-110S-DEMO', 'HB-110S-M', 'HB-110S', 'LC-800V-M', 'LC-800S-M', 'LC-825S-M', 'LC-800V-DEMO',
						'LC-825V-M', 'LC-825V-DEMO', 'LC-825V', 'LC-825S', 'LC-825S-DEMO', 'LC-800S-DEMO']
# Select s.items
# from PyComm
# Cross apply dbo.Split(Parts, ',') as s
# where [Serial Number] = '1234567'
# and [Status] = 'Reason'


def scrap2(app: Application):
	cv = CV_Config(window=app._win)
	log.debug("Scrap script started")

	log.debug("Opening Miscellaneous Issue form")
	app.open_form('Miscellaneous Issue')
	MiscIssue = app.MiscellaneousIssueForm
	log.debug("Miscellaneous Issue form opened")
	sleep(0.5)
	log.debug("Opening Units form")
	app.open_form('Units')
	Units = app.UnitsForm
	log.debug("Unit form opened")

	log.debug("Opening Serial Numbers form")
	app.open_form('Serial Numbers')
	SrlNum = app.SerialNumbersForm
	log.debug("Serial Numbers form opened")
	for item in app.window_menu.items():
		text = item.texts()[0]
		if 'Units' in text:
			UnitsFormFocus = item
		elif 'Miscellaneous Issue' in text:
			MiscIssueFormFocus = item
		elif 'Serial Numbers' in text:
			SrlNumFormFocus = item
	# NotesFormFocus = None
	while True:
		log.debug("Checking queued scrap units")
		all_unit_data = mssql.query("SELECT * FROM PyComm WHERE [Status] = 'Scrap'", fetchall=True)
		if not all_unit_data:
			continue
		log.debug("Receiving unit data")
		all_units = set(map(lambda x: Unit(**x), all_unit_data))
		log.info(f"Units data found: {len(all_units)}")
		if not dev_mode:
			for unit in all_units:
				mssql.modify(f"UPDATE PyComm SET [Status] = 'Started' WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Scrap' AND [Id] = {int(unit.id)}")
		try:
			timer.start()
			count1 = 0
			count2 = 0
			count3 = 0
			all_units_grouped = _group_units_by_build(all_units)
			log.debug(f"Units split into {len(all_units_grouped.keys())} group(s)")
			sorted_keys = sorted(all_units_grouped.keys(), key=lambda x: len(all_units_grouped[x]), reverse=True)
			sorted_unit_groups = dict(zip(sorted_keys, map(lambda x: all_units_grouped[x], sorted_keys)))  # Sorts unit groups by quantity in descending order
			log.debug("Units sorted by quantity in descending order")
			for i,(key,group) in enumerate(sorted_unit_groups.items()):
				log.debug(f"Group {i+1}: {key} build, {len(group)} unit(s)")
			for build,units in sorted_unit_groups.items():
				if build in cellular_unit_builds:
					phone = True
				else:
					phone = False
				unit_locations = defaultdict(list)
				SrlNumFormFocus.select()

				cv.load_previous_configuration('frm_SerNums')
				for unit in units:
					count1 += 1
					_try_serial2(unit, app, cv)

					status = SrlNum.status.texts()[0]
					log.debug(f"Unit location status '{status}' found for unit {unit.serial_number_prefix + unit.serial_number}")
					if status != 'Out of Inventory':  # OR   status == 'In Inventory' ???
						location = SrlNum.location.text()
						unit_locations[location].append(unit)
						log.debug(f"Unit location '{location}' found for unit {unit.serial_number_prefix + unit.serial_number}")
					sleep(0.1)
					pag.press('f4')
					pag.press('f5')
					sleep(0.1)
				MiscIssueFormFocus.select()
				app.add_form('MiscellaneousIssueForm')
				MiscIssue = app.MiscellaneousIssueForm
				cv.load_previous_configuration('frm_MiscIssue')
				pag.click(*cv.window_gc.txt_item.global_center)
				sleep(0.2)
				pag.hotkey('ctrl', 'end')
				pag.press('backspace', 20)
				pag.typewrite(build)
				sleep(1)
				for location,units in unit_locations.items():
					pag.click(*cv.window_gc.tab_dtl.global_center)
					sleep(0.2)
					pag.click(*cv.window_gc.txt_loc.global_center)
					sleep(0.2)
					pag.hotkey('ctrl', 'end')
					pag.press('backspace', 20)
					pag.typewrite(location)
					sleep(0.2)
					pag.click(*cv.window_gc.txt_qty.global_center)
					sleep(0.2)
					pag.hotkey('ctrl', 'end')
					pag.press('backspace', 20)
					pag.typewrite(str(float(len(units))))
					sleep(0.5)
					pag.press('tab')
					sleep(0.5)
					if build.count('-') < 2:  # If direct units
						reason = "24"
					else:
						reason = "22"
					pag.click(*cv.window_gc.txt_rsn.global_center)
					sleep(0.2)
					pag.hotkey('ctrl', 'end')
					pag.press('backspace', 20)
					pag.typewrite(reason)
					sleep(0.2)
					pag.click(*cv.window_gc.txt_doc_num.global_center)
					sleep(0.2)
					pag.hotkey('ctrl', 'end')
					pag.press('backspace', 20)
					pag.typewrite(f"SCRAP {units[0].operator_initials}")
					sleep(0.5)
					pag.click(*cv.window_gc.tab_srl_num.global_center)
					sleep(2)
					pag.click(*cv.window_gc.txt_gen_qty.global_center)
					sleep(1)
					pag.hotkey('ctrl', 'end')
					pag.press('backspace', 20)
					pag.typewrite("9999999")
					sleep(1)
					pag.hotkey('alt', 'g')
					sleep(1)
					pag.press('right')
					sleep(1)
					for unit in sorted(units, key=lambda x: int(x.serial_number)):  # Sorts units by serial number in descending order
						count2 += 1
						app.find_value_in_collection(collection='SLSerials', property='S/N (SerNum)', value=unit.serial_number)
						if app.popup.exists(1, 2):
							# skipped_units[build].append(unit)
							pag.press('enter')
							sleep(0.2)
							log.debug(f"Added unit {unit.serial_number_prefix + unit.serial_number} to skipped list")
							continue
						sleep(0.2)
						pag.press('left')
						sleep(0.2)
						pag.press('space')
						sleep(0.2)
						pag.press('right')
						sleep(0.2)
					if dev_mode:
						app.cancel_close.click()
						app.open_form('Miscellaneous Issue')
						MiscIssue = app.MiscellaneousIssueForm
					else:
						pag.click(*cv.window_gc.btn_proc.global_center)
						pag.press('enter')
						sleep(5)
						pag.press('esc')
						sleep(0.5)
				pag.keyUp('ctrlleft')
				pag.keyUp('ctrlright')
				pag.keyUp('ctrl')
				log.debug("Step 2 Complete")
			end_time = timer.stop()

			begin_string = ""
			if count1 > 0:
				begin_string += f"{count1} unit(s) checked through Serial Numbers"
			if count1 > 0 and count2 > 0:
				begin_string += " and "
			if count2 > 0:
				begin_string += f"{count2} unit(s) processed through Miscellaneous Issue"
			begin_string += ", "
			time_log.info(f"{begin_string} Total time {end_time}")
			UnitsFormFocus.select()
			app.add_form('UnitsForm')
			Units = app.UnitsForm
			log.debug("Step 3 Started")
			timer.start()
			for unit in all_units:
				try:
					cv.load_previous_configuration('frm_Units')
					build = unit.whole_build
					if build in cellular_unit_builds:
						phone = True
					else:
						phone = False
					log.debug(f"Running Step 3 on unit {unit.serial_number_prefix + unit.serial_number}")
					# if unit in skipped_units:
					# 	log.debug(f"Skipping Step 3 on unit {unit.serial_number_prefix + unit.serial_number}, it's in the skipped list")
						# continue
					pag.click(*cv.window_gc.txt_unit.global_center)
					sleep(0.2)
					pag.typewrite(unit.serial_number_prefix+unit.serial_number)
					sleep(0.2)
					log.debug(f"Serial number {unit.serial_number_prefix+unit.serial_number} entered")
					pag.press('f4')
					sleep(0.2)
					app.add_form('UnitsForm')
					Units = app.UnitsForm
					pag.click(*cv.window_gc.txt_cust.global_center)
					sleep(0.2)
					pag.hotkey('ctrl', 'end')
					pag.press('backspace', 20)
					pag.typewrite('302')
					sleep(0.2)
					log.debug("Customer set to 302")
					if phone:
						scrap_code = 'SCRAPPED1'
					else:
						scrap_code = 'SCRAPPED'
					moveTo(*Units.change_status.coordinates.center)
					pag.click(*cv.window_gc.btn_change_status.global_center)
					log.debug("Change status clicked")
					sleep(0.5)
					pag.hotkey('alt', 'y')  # Yes button, (ALT + Y)
					pag.click(*cv.window_gc.txt_unit_status_code.global_center)
					sleep(0.2)
					pag.hotkey('ctrl', 'end')
					pag.press('backspace', 20)
					pag.typewrite(scrap_code)
					sleep(0.2)
					log.debug(f"Unit Status Code set to {scrap_code}")
					if phone:
						ship_num = "2"
					else:
						ship_num = "1"
					pag.click(*cv.window_gc.txt_ship_to.global_center)
					sleep(0.2)
					pag.hotkey('ctrl', 'end')
					pag.press('backspace', 20)
					pag.typewrite(ship_num)
					sleep(0.2)
					log.debug(f"Ship To set to {ship_num}")
					if not dev_mode:
						pag.hotkey('ctrl', 's')
					pag.keyUp('ctrlleft')
					pag.keyUp('ctrlright')
					pag.keyUp('ctrl')
					sleep(1)
					sro_count = _open_first_open_sro(unit, app)
					SRO_Operations = app.ServiceOrderOperationsForm
					SRO_Operations.reasons_tab.select()
					row = SRO_Operations.reasons_tab.grid.rows
					SRO_Operations.reasons_tab.grid.populate(('General Reason', 'Specific Reason', 'General Resolution'), row - 1)
					SRO_Operations.reasons_tab.grid.select_cell('General Reason', row - 1)
					gen_rsn = SRO_Operations.reasons_tab.grid.cell
					gen_rso, spec_rso = unit.notes.split(',')
					SRO_Operations.reasons_tab.grid.select_cell('General Resolution', row - 1)
					if SRO_Operations.reasons_tab.grid.cell:  # If last row filled, append new row
						# gen_rsn, spec_rsn, gen_rso, spec_rso = unit.notes.split(',')
						gen_rsn = str(gen_rsn).strip(' ')
						spec_rsn = '20'
						# spec_rsn = spec_rsn.strip(' ')
						gen_rso = gen_rso.strip(' ')
						spec_rso = spec_rso.strip(' ')
						SRO_Operations.reasons_tab.grid.select_cell('General Reason', row)
						SRO_Operations.reasons_tab.grid.cell = gen_rsn
						sleep(10)
						SRO_Operations.reasons_tab.grid.select_cell('Specific Reason', row)
						SRO_Operations.reasons_tab.grid.cell = spec_rsn
						SRO_Operations.reasons_tab.grid.select_cell('General Resolution', row)
						SRO_Operations.reasons_tab.grid.cell = gen_rso
						SRO_Operations.reasons_tab.grid.select_cell('Specific Resolution', row)
						SRO_Operations.reasons_tab.grid.cell = spec_rso
					else:  # Else, fill last row
						SRO_Operations.reasons_tab.grid.select_cell('Specific Reason', row - 1)
						if not SRO_Operations.reasons_tab.grid.cell:
							spec_rsn = '20'
							SRO_Operations.reasons_tab.grid.cell = spec_rsn
						SRO_Operations.reasons_tab.grid.select_cell('General Resolution', row - 1)
						SRO_Operations.reasons_tab.grid.cell = gen_rso
						SRO_Operations.reasons_tab.grid.select_cell('Specific Resolution', row - 1)
						SRO_Operations.reasons_tab.grid.cell = spec_rso
					spec_rso_name = spec_rso_codes.get(spec_rso, 'SCRAP')
					gen_rso_name = mssql.query(f"SELECT TOP 1 [Failure] FROM FailuresRepairs WHERE [Product] = '{unit.product}' AND [ReasonCodes] = '{unit.notes}'")
					if gen_rso_name is not None:
						gen_rso_name = gen_rso_name[0]
					else:
						gen_rso_name = mssql.query(f"SELECT TOP 1 [Failure] FROM FailuresRepairs WHERE [ReasonCodes] = '{unit.notes}'")[0]
					SRO_Operations.reasons_tab.reason_notes.set_focus()
					SRO_Operations.reasons_tab.reason_notes.set_keyboard_focus()
					SRO_Operations.reasons_tab.reason_notes.send_keystrokes("^{END}")
					if SRO_Operations.reasons_tab.reason_notes.texts()[-1] != '':
						SRO_Operations.reasons_tab.reason_notes.send_keystrokes("{ENTER}")
					SRO_Operations.reasons_tab.reason_notes.send_keystrokes(f"[{spec_rso_name.upper()} {gen_rso_name.upper()}]")
					SRO_Operations.reasons_tab.reason_notes.send_keystrokes("{ENTER}")
					SRO_Operations.reasons_tab.reason_notes.send_keystrokes(f"[{unit.operator_initials} {unit.datetime.strftime('%m/%d/%Y')}]")
					sleep(1)
					cv.load_previous_configuration('frm_SRO_Operations')
					pag.click(*cv.window_gc.txt_status.global_center)
					sleep(0.2)
					pag.hotkey('ctrl', 'end')
					pag.press('backspace', 20)
					pag.press('down', 4)
					sleep(0.5)
					is_closed_status = ''
					if dev_mode:
						app.cancel_close.click()
						app.cancel_close.click()
					else:
						pag.hotkey('ctrl', 's')
						sleep(1)
						pag.press('esc')
						sleep(1)
						app.save_close.click()
						app.save_close.click()
					# if NotesButton is None:
					# 	for item in app.actions_menu.items():
					# 		text = item.text()[0]
					# 		if 'Notes for Current' in text:
					# 			NotesButton = item
					# NotesFormFocus.select()
					sleep(0.5)
					kbd.SendKeys('%s')  # Actions Menu, (ALT + S)
					sleep(0.2)
					kbd.SendKeys('o')  # Notes For Current, (O)
					sleep(0.5)
					app.find_value_in_collection(collection='Object Notes', property='Subject (DerDesc)', value='NOTES', case_sensitive=True)
					while app.popup.exists():
						app.popup.close_alt_f4()
						pag.press('f8', 10)
						pag.typewrite('NOTES')
					note_txt = app._win2.child_window(auto_id='DerContentEdit')
					note_txt.set_focus()
					note_txt.click_input()
					note_txt.type_keys('^{END}')

					text = fr"{note_txt.legacy_properties()['Value'].strip(' ')}"
					if f"[{spec_rso_name} {gen_rso_name}]\n[{unit.operator_initials} {unit.datetime.strftime('%m/%d/%Y')}]" not in text:
						if not ((text.endswith(r'\n') or text.endswith(r'\r')) or (text == '')):
							note_txt.type_keys('{ENTER}')
						note_txt.type_keys(f"[{spec_rso_name}")
						note_txt.type_keys("{SPACE}")
						note_txt.type_keys(f"{gen_rso_name}]")
						note_txt.type_keys("{ENTER}")
						note_txt.type_keys(f"[{unit.operator_initials}")
						note_txt.type_keys("{SPACE}")
						note_txt.type_keys(f"{unit.datetime.strftime('%m/%d/%Y')}]")
					if dev_mode:
						app.cancel_close.click()
					else:
						app.save_close.click()
					sleep(1)
					pag.press('f4')
					pag.press('f5')
					sleep(0.5)
				except UnitClosedError:
					log.exception("No open SROs")
					if not dev_mode:
						pag.press('f4')
						pag.press('f5')
						pag.hotkey('alt', 'y')
						mssql.modify(f"UPDATE PyComm SET [Status] = 'No Open SRO(Scrap)' WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Started' AND [Id] = {int(unit.id)}")
						continue
					continue
					pag.press('f4')
					pag.press('f5')
					pag.hotkey('alt', 'y')
				else:
					if not dev_mode:
						count3 += 1
						mssql.modify(f"UPDATE ScrapLog SET [SL8_Status] = 'Closed' WHERE [SL8_Status] = 'Open' AND [SerialNumber] = '{unit.serial_number}'")
						mssql.modify(f"DELETE FROM PyComm WHERE [Id] = {unit.id} AND [Serial Number] = '{unit.serial_number}' AND [Status] = 'Started'")
		except Exception:
			log.exception(f"Something went horribly wrong!")
			if not dev_mode:
				for unit in all_units:
					mssql.modify(f"UPDATE PyComm SET [Status] = 'Skipped(Scrap)' WHERE [Serial Number] = '{unit.serial_number}' AND [Status] = 'Started' AND [Id] = {int(unit.id)}")
			if count3 > 0:
				end_time = timer.stop()
				begin_string = f"{count3} units fully scrapped through the Units form."
				time_log.info(f"{begin_string} Total time {end_time}")
			quit()
		else:
			end_time = timer.stop()
			begin_string = f"{count3} units fully scrapped through the Units form."
			time_log.info(f"{begin_string} Total time {end_time}")
			# if len(unit_locations.keys()) > 0:
			# 	total = 0
			# 	for u in unit_locations.values():
			# 		total += len(u)
			# 	begin_string = f"{total} unit(s) processed through Miscellaneous Issue, "
			# 	if len(all_units_grouped.keys()) > 1:
			# 		begin_string += f"seperated into {len(all_units_grouped.keys())} different groups by build, "
			# 	if len(unit_locations.keys()) > 1:
			# 		begin_string += f"from {len(unit_locations.keys())} different locations, "
			# 	begin_string += f"and {len(all_units)} units fully scrapped through the Units form."
			# else:
			# 	begin_string = f"{len(all_units)} units fully scrapped through the Units form."
			# time_log.info(f"{begin_string} Total time {end_time}")

	# If Out of Inventory then: ???
	# Open Miscellaneous Issue Form
	# For each group:

	#   Input Build ('LC-800V-M', etc) into Item textbox
	#           Click Generate button(also: alt+g)
	#           For each serial number, in ascending order:
	#               Find Value In Collection menu item(also: alt+e, v)
	#               In Find window:
	#                   If popup, unit doesn't exist
	#       Click Process button(also: alt+r)
	#       Any popups???

	# Open Units Form
	# For each serial number:
	#   Input serial number into Unit textbox
	#   Press 'F4'
	#   Input "302" into Customer textbox
	#   Input "1" for non-phone or "2" for phone into Ship To textbox

	#   Click Change Status button
	#   In Popup titled "hh4q0kfi":     ("Are you sure you want to change the unit status?" text)
	#       Click Yes button (Alt + Y)
	#   Input "SCRAPPED" for non-phone or "SCRAPPED1" for phone into Unit Status Code textbox
	#   Save
	#   In Service History Tab:
	#       Find first open SRO
	#       If there are none open: ???
	#       Click View button
	#       In Service Order Lines Form:
	#           Click Service Order Operations button
	#           In Service Order Operations Form:
	#               In Reasons tab:
	#                   Input General Resolution and Specific Resolution???
	#                   Name1 = General Resolution Fault Code Name
	#                   Name2 = Specific Resolution Fault Code Name(Usually "SCRAP")
	#                   Input "{Name2} {Name1}\n{Initials} {datetime.date}"
	#               Close Unit
	#               Save Close Form
	#   Click Notes button

	#   In Notes Form:
	#       Find Value In Collection menu item(also: alt+e, v)
	#       In Find window:
	#           Input "NOTES" into Find textbox
	#           Input "Object Notes" into In Collection textbox
	#           Input "Subject (DerDesc)" into In Property textbox
	#           Click Case Sensitive checkbox to toggle from unchecked -> checked
	#           Click OK button
	#       If popup happens(NOTES doesn't exist):
	#           Find Value In Collection menu item(also: alt+e, v)
	#           In Find window:
	#               Input "" into Find textbox
	#               Input "Object Notes" into In Collection textbox
	#               Input "Subject (DerDesc)" into In Property textbox
	#               Click OK button
	#           Typewrite "NOTES"
	#       Input(append) "{Name2} {Name1}\n{Initials} {datetime.date}" into Note("A&ttach  File...Edit") textbox
	#       Save Close Form
	# TODO: Scrap report


def main(argv):
	"""parser = argparse.ArgumentParser()
	parser.add_argument('cmd', type=str)
	parser.parse_args('username', type=str)
	parser.add_argument('-d', '--directory', help='directory of SyteLine executable')"""
	log.debug("Attempting to read 'config.ini'")
	config.read_file(open('config.ini'))
	# if len(argv) < 4:
	# 	log.error(f"Expected >4 cmd arguments, got {len(argv)}")
	# 	raise ValueError(f"Expected >4 cmd arguments, got {len(argv)}")
	usage_string = f"usage: {argv[0]} cmd username password [OPTIONS]..."
	cmd_all = {'transact': transact, 'query': query, 'reason': reason, 'scrap': scrap2}
	opt_all = ('-fp', '-w', '-k', '-p', '-o')
	long_opt_all = ('--filepath', '--workers', '--key', '--preference', '--override')
	if len(argv) > 2:
		cmd,usr,pwd = argv[1:4]
	else:
		cmd = argv[1]
		usr = config.get('Login', 'username')
		pwd = config.get('Login', 'password')
	# def_key = '6170319'
	if len(argv) > 5:
		opt = dict(zip(argv[4::2], argv[5::2]))
		for o in opt.keys():
			if o not in opt_all:
				log.error(f"Invalid cmd argument: '{o}'")
				raise ValueError(f"Invalid cmd argument: '{o}'")
	else:
		opt = {}
	if cmd not in cmd_all.keys():
		log.error(f"Invalid command: '{cmd}'")
		raise ValueError(f"Invalid command: '{cmd}'")

	if opt.get('-o', False):
		global dev_mode
		dev_mode = False

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
					log.error("'WinStudio.exe' could not be found")
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
# TODO: Check if other requests for same sn exist, if so, do as well
# TODO: Pause-able commands? (Possibility/demand needs looking into)
