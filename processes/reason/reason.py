import datetime
import logging
import sys
from time import sleep
from typing import List
import numpy as np

import pyautogui as pag
import pywinauto.timings
from pywinauto.controls import common_controls, uia_controls, win32_controls

from config import *
from common import *
from common import DataGridNEW
from constants import SYTELINE_WINDOW_TITLE
from exceptions import *
from constants import REASON_STATUS

pag.FAILSAFE = False
log = logging.getLogger('root')


starting_forms = {'Units'}


def get_unitsNEW(*, exclude: List[str] = set()) -> List[Unit]:
	serial_number = mssql.execute("""SELECT TOP 10 [Serial Number] FROM PyComm WHERE Status = %s AND DateTime <= DATEADD(MINUTE, -5, GETDATE()) ORDER BY DateTime ASC""", 'Queued')
	serial_number = mssql.execute("""SELECT TOP 10 [Serial Number] FROM PyComm WHERE Status = %s ORDER BY DateTime ASC""", 'Queued')
	if serial_number:
		for serial in serial_number:
			if serial[0] not in exclude:
				return Unit.from_serial_number(serial_number[0].Serial_Number, TRANSACTION_STATUS)
	else:
		return None

def get_units(serial_number: str) -> List[Unit]:
	ID = mssql.execute("""SELECT [Id] FROM PyComm WHERE Status = %s AND [Serial Number] = %s ORDER BY DateTime ASC""", (REASON_STATUS, serial_number))
	if ID:
		return Unit.from_serial_number(serial_number, REASON_STATUS)
	else:
		return None

# TODO: Rework process

def run(app: Application, units: List[Unit]):
	try:
		_base_process(app, units=units)
	except Exception as ex:
		log.exception("SOMETHING HAPPENED!!!")
		sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
		sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
		for x in units:
			x.skip(ex, batch_amt=len(units))
		if sl_uia.exists(2, 0.09):
			if 'SRO Transactions' in app.forms:
				sl_uia.CancelCloseButton.click()
				dlg = app.get_popup()
				while dlg:
					log.debug(f"Transactions Cancel Close dialog text: '{dlg.Text}'")
					dlg[0].close()
					dlg = app.get_popup()
			if 'Service Order Operations' in app.forms:
				sl_uia.CancelCloseButton.click()
				dlg = app.get_popup()
				while dlg:
					log.debug(f"Operations Cancel Close dialog text: '{dlg.Text}'")
					dlg[0].close()
					dlg = app.get_popup()
			if 'Service Order Lines' in app.forms:
				sl_uia.CancelCloseButton.click()
				dlg = app.get_popup()
				while dlg:
					log.debug(f"Lines Cancel Close dialog text: '{dlg.Text}'")
					dlg[0].close()
					dlg = app.get_popup()
			sl_win.send_keystrokes('{F4}')
			sl_win.send_keystrokes('{F5}')
	else:
		log.info(f"Unit: {units[0].serial_number} completed")
		for x in units:
			x.complete(batch_amt=len(units))

def _base_process(app: Application, units: List[Unit]):
	unit = units[0]
	pywinauto.timings.Timings.Fast()
	log.info(f"Starting Reason script with unit: {unit.serial_number}")
	sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
	sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
	if not sl_win.exists():
		for x in units:
			x.reset()
		sys.exit(1)
	app.verify_form('Units')
	sleep(0.2)
	sl_win.UnitEdit.set_text(unit.serial_number)  # Input serial number
	sleep(0.2)
	sl_win.send_keystrokes('{F4}')  # Filter in Place
	count = 0
	# or (not sl_uia.UnitEdit.legacy_properties()['IsReadOnly'])
	while (sl_win.UnitEdit.texts()[0].strip() != unit.serial_number) and sl_win.UnitEdit.texts()[0].strip():  # While actual serial number != attempted serial number
		if count >= 30:
			raise SyteLineFilterInPlaceError(unit.serial_number.number)
		sleep(0.4)
		count += 1
	if sl_win.UnitEdit.texts()[0].strip() != unit.serial_number:
		if not sl_win.UnitEdit.texts()[0].strip():
			raise InvalidSerialNumberError(unit.serial_number.number)
		else:
			raise SyteLineFilterInPlaceError(unit.serial_number.number,
			                                 f"Expected input serial number '{unit.serial_number}', "
			                                 f"returned '{sl_win.UnitEdit.texts()[0].strip()}'")
	for x in units:
		x.start()
	if not sl_win.ServiceOrderLinesButton.is_enabled():
		raise NoOpenSROError(serial_number=unit.serial_number.number, sro=unit.sro, msg="Service Order Lines Button is disabled")
	log.debug("Service Order Lines Button clicked")
	sl_win.set_focus()
	sl_win.ServiceOrderLinesButton.click()
	sl_win.ServiceOrderOperationsButton.wait('visible', 10, 0.09)
	sl_win.set_focus()
	app.find_value_in_collection('Service Order Lines', 'SRO (SroNum)', unit.sro)
	dlg = app.get_popup(0.5)
	count = 0
	while dlg:
		log.debug(f"Lines Find SRO dialog text: '{dlg.Text}'")
		dlg[0].close()
		count += 1
		dlg = app.get_popup()
	else:
		if count > 0:
			raise InvalidSROError(serial_number=unit.serial_number.number, sro=unit.sro)
	log.debug("Service Order Operations Button clicked")
	sl_win.set_focus()
	sl_win.ServiceOrderOperationsButton.click()
	sl_win.SROLinesButton.wait('visible', 10, 0.09)
	timer = Timer.start()
	if sl_win.StatusEdit3.texts()[0].strip() == 'Closed':
		status = win32_controls.EditWrapper(sl_win.StatusEdit3.element_info)
		status.set_text('Open')
		status.click_input()
		pag.press('tab')
		# handle_popup(best_match='ResetDatesDialog')
		pag.press('esc')
		save = sl_uia.SaveButton
		save.click()
	sl_win.SROTransactionsButton.wait('enabled', 10, 0.09)
	common_controls.TabControlWrapper(sl_win.TabControl).select('Reasons')  # Open 'Reasons' Tab
	reason_grid = DataGridNEW.default(app, ['General Reason', 'Specific Reason', 'General Resolution', 'Specific Resolution'])
	reason_grid.populate()
	gen_rsn = 1000
	for i, row in enumerate(reason_grid.grid):
		if reason_grid.grid[i, 0]:
			gen_rsn = reason_grid.grid[i, 0]
		if np.count_nonzero(row) < 4:
			break
	for unit in units:
		resolution_pairs = [(gen, spec) for gen, spec in zip(reason_grid.grid[..., 2], reason_grid.grid[..., 3])]
		if (unit.general_resolution, unit.specific_resolution) in resolution_pairs:
			continue
		i += 1
		row = reason_grid.grid[i]
		count = np.count_nonzero(row)
		if count == 1:
			reason_grid.set_cell('Specific Reason', i, 20)
			reason_grid.set_cell('General Resolution', i, unit.general_resolution)
			reason_grid.set_cell('Specific Resolution', i, unit.specific_resolution)
		elif count == 2:
			reason_grid.set_cell('General Resolution', i, unit.general_resolution)
			reason_grid.set_cell('Specific Resolution', i, unit.specific_resolution)
		else:
			reason_grid.set_cell('General Reason', i, gen_rsn)
			reason_grid.set_cell('Specific Reason', i, 20)
			reason_grid.set_cell('General Resolution', i, unit.general_resolution)
			reason_grid.set_cell('Specific Resolution', i, unit.specific_resolution)
		reason_grid.select_cell(reason_grid.get_cell('General Reason', 1))
		sleep(0.5)
		pag.hotkey('ctrl', 's')
		sleep(1)


		if not done:
			if len(reason_rows) >= 6:
				top_row_temp = reason_grid.children()[reason_grid.children_texts().index('Top Row')]
				try:
					open_row_temp = uia_controls.ListViewWrapper(reason_grid.children()[reason_grid.children_texts().index('Top Row') + 7].element_info)
				except IndexError:
					open_row_temp = uia_controls.ListViewWrapper(reason_grid.children()[reason_grid.children_texts().index('Top Row') + 6].element_info)
				gen_resn_temp = uia_controls.ListItemWrapper(open_row_temp.item(top_row_temp.children_texts().index('General Reason')).element_info)
				c_coords = center(gen_resn_temp)
				pag.click(*c_coords)
				log.debug("CLICKED")
				pag.scroll(-(10 * (len(reason_rows) // 6)))
				log.debug("SCROLLED")
				reason_grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info)
				reason_rows = access_grid(reason_grid, ['General Reason', 'Specific Reason', 'General Resolution', 'Specific Resolution'])

			full_row = None
			empty_row_i = len(reason_rows) - 1
			partial = False
			for i, row in enumerate(reason_rows[::-1]):
				if {row.General_Reason, row.Specific_Reason, row.General_Resolution, row.Specific_Resolution} == {None,
				                                                                                                  None,
				                                                                                                  None,
				                                                                                                  None}:
					empty_row_i = len(reason_rows) - (i + 1)
					partial = False
				elif {row.Specific_Reason, row.General_Resolution, row.Specific_Resolution} == {None, None, None}:
					empty_row_i = len(reason_rows) - (i + 1)
					partial = True
					full_row = row
				else:
					if full_row is None:
						full_row = row
					break
			top_row_i = reason_grid.children_texts().index('Top Row')
			top_row = reason_grid.children()[top_row_i]
			open_row = uia_controls.ListViewWrapper(reason_grid.children()[empty_row_i + top_row_i + 1].element_info)

			gen_resn = uia_controls.ListItemWrapper(open_row.item(top_row.children_texts().index('General Reason')).element_info)
			spec_resn = uia_controls.ListItemWrapper(open_row.item(top_row.children_texts().index('Specific Reason')).element_info)
			gen_reso = uia_controls.ListItemWrapper(open_row.item(top_row.children_texts().index('General Resolution')).element_info)
			spec_reso = uia_controls.ListItemWrapper(open_row.item(top_row.children_texts().index('Specific Resolution')).element_info)

			pag.click(*center(gen_resn))
			dlg = app.get_popup()
			while dlg:
				log.debug(f"Operations Reason Grid dialog text: '{dlg.Text}'")
				dlg[0].close()
				dlg = app.get_popup()
			q = []
			if not partial:
				q.append((center(gen_resn), str(full_row.General_Reason)))
			q.append((center(spec_resn), str(unit.specific_reason)))
			q.append((center(gen_reso), str(unit.general_resolution)))
			q.append((center(spec_reso), str(unit.specific_resolution)))
			for coord, num in q:
				pag.click(*coord)
				sleep(0.5)
				pag.typewrite(str(num))
				sleep(0.5)
			pag.hotkey('ctrl', 's')
			pag.press('up', 40)
			if len(reason_rows) >= 6:
				pag.click(*coord)
				pag.scroll(10 * (len(reason_rows) // 6))
			if unit.general_resolution_name == 'Pass':
				if sl_win.ReasonNotesEdit.texts()[0].strip():
					sl_win.ReasonNotesEdit.set_text(sl_win.ReasonNotesEdit.texts()[0].strip() +
					                                "\n[POWER UP OK]\n[ACCEPTED]")
				else:
					sl_win.ReasonNotesEdit.set_text("[POWER UP OK]\n[ACCEPTED]")
			else:
				if sl_win.ReasonNotesEdit.texts()[0].strip():
					sl_win.ReasonNotesEdit.set_text(sl_win.ReasonNotesEdit.texts()[0].strip() +
					                                f"\n[{unit.general_resolution_name}]")
				else:
					sl_win.ReasonNotesEdit.set_text(f"[{unit.general_resolution_name}]")
			sl_win.ReasonNotesEdit.send_keystrokes('^s')

			if sl_win.ResolutionNotesEdit.texts()[0].strip():
				sl_win.ResolutionNotesEdit.set_text(sl_win.ResolutionNotesEdit.texts()[0].strip() +
				                                    f"\n[{unit.operator} {unit.datetime.strftime('%m/%d/%Y')}]")
			else:
				sl_win.ResolutionNotesEdit.set_text(f"[{unit.operator} {unit.datetime.strftime('%m/%d/%Y')}]")
		sl_win.ResolutionNotesEdit.send_keystrokes('^s')
	if not unit.sro_open_status['Operations']:
		common_controls.TabControlWrapper(sl_win.TabControl).select('General')  # Open 'General' Tab
		if not sl_win.CompletedDateEdit.texts()[0].strip():
			sl_win.CompletedDateEdit.set_text(datetime.datetime.now().strftime('%m/%d/%Y %I:%M:%S %p'))
		sl_win.CompletedDateEdit.send_keystrokes('^s')
		status = win32_controls.EditWrapper(sl_win.StatusEdit3.element_info)
		sl_win.set_focus()
		status.set_keyboard_focus()
		status.send_keystrokes('{DOWN}{DOWN}')
		try:
			status.send_keystrokes('^s')
			sleep(1)
		except TimeoutError:
			pass
		finally:
			pag.press('esc')
	sl_win.send_keystrokes('^s')
	sro_operations_time = timer.stop() / len(units)
	for x in units:
		x.sro_operations_time += sro_operations_time
	sl_uia.CancelCloseButton.click()
	sl_uia.CancelCloseButton.click()
	sleep(0.5)
	sl_win.ServiceOrderLinesButton.wait('visible', 2, 0.09)
	sl_win.send_keystrokes('{F4}')
	sl_win.send_keystrokes('{F5}')
