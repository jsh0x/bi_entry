import logging.config
from time import sleep
import sys
from typing import List

import pyautogui as pag
import pywinauto.timings
from pywinauto.controls import uia_controls, win32_controls, common_controls

from exceptions import *
from common import timer, access_grid, Application, Unit, center
from constants import SYTELINE_WINDOW_TITLE


logging.config.fileConfig('config.ini')
log = logging


def Reason(app: Application, units: List[Unit]):
	try:
		unit = units[0]
		pywinauto.timings.Timings.Fast()
		log.info(f"Starting Reason script with unit: {unit.serial_number_prefix+unit.serial_number}")
		sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
		sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
		if not sl_win.exists():
			unit.reset()
			sys.exit(1)
		app.verify_form('Units')
		sleep(0.2)
		sl_win.UnitEdit.set_text(unit.serial_number_prefix + unit.serial_number)  # Input serial number
		sleep(0.2)
		sl_win.send_keystrokes('{F4}')  # Filter in Place
		count = 0
		# or (not sl_uia.UnitEdit.legacy_properties()['IsReadOnly'])
		while (sl_win.UnitEdit.texts()[0].strip() != unit.serial_number_prefix + unit.serial_number) and sl_win.UnitEdit.texts()[0].strip():  # While actual serial number != attempted serial number
			if count >= 30:
				raise SyteLineFilterInPlaceError(unit.serial_number)
			sleep(0.4)
			count += 1
		if sl_win.UnitEdit.texts()[0].strip() != unit.serial_number_prefix + unit.serial_number:
			if not sl_win.UnitEdit.texts()[0].strip():
				raise InvalidSerialNumberError(unit.serial_number)
			else:
				raise SyteLineFilterInPlaceError(unit.serial_number,
				                                 f"Expected input serial number '{unit.serial_number_prefix+unit.serial_number}', "
				                                 f"returned '{sl_win.UnitEdit.texts()[0].strip()}'")
		unit.start()
		if not sl_win.ServiceOrderLinesButton.is_enabled():
			raise NoOpenSROError(serial_number=unit.serial_number, sro=unit.sro_num, msg="Service Order Lines Button is disabled")
		log.debug("Service Order Lines Button clicked")
		sl_win.set_focus()
		timer.start()
		sl_win.ServiceOrderLinesButton.click()
		sl_win.ServiceOrderOperationsButton.wait('visible', 2, 0.09)
		app.find_value_in_collection('Service Order Lines', 'SRO (SroNum)', unit.sro_num)
		dlg = app.get_popup(0.5)
		count = 0
		while dlg:
			log.debug(f"Lines Find SRO dialog text: '{dlg.Text}'")
			dlg[0].close()
			count += 1
			dlg = app.get_popup()
		else:
			if count > 0:
				raise InvalidSROError(serial_number=unit.serial_number, sro=unit.sro_num)
		log.debug("Service Order Operations Button clicked")
		sl_win.set_focus()
		sl_win.ServiceOrderOperationsButton.click()
		sl_win.SROLinesButton.wait('visible', 2, 0.09)
		unit.sro_operations_timer.start()
		if sl_win.StatusEdit3.texts()[0].strip() == 'Closed':
			status = win32_controls.EditWrapper(sl_win.StatusEdit3.element_info)
			status.set_text('Open')
			status.click_input()
			pag.press('tab')
			# handle_popup(best_match='ResetDatesDialog')
			pag.press('esc')
			save = sl_uia.SaveButton
			save.click()
		sl_win.SROTransactionsButton.wait('enabled', 2, 0.09)
		sl_win.SROTransactionsButton.wait('enabled', 2, 0.09)
		common_controls.TabControlWrapper(sl_win.TabControl).select('Reasons')  # Open 'Reasons' Tab
		reason_grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info)
		reason_rows = access_grid(reason_grid, ['General Reason', 'Specific Reason', 'General Resolution', 'Specific Resolution'])
		full_row = None
		empty_row_i = len(reason_rows) - 1
		partial = False
		for i,row in enumerate(reason_rows[::-1]):
			if {row.General_Reason, row.Specific_Reason, row.General_Resolution, row.Specific_Resolution} == {None, None, None, None}:
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
		gen_resn_i = gen_resn.rectangle()
		c_coords = center(x1=gen_resn_i.left, y1=gen_resn_i.top, x2=gen_resn_i.right, y2=gen_resn_i.bottom)

		spec_resn = uia_controls.ListItemWrapper(open_row.item(top_row.children_texts().index('Specific Reason')).element_info)
		spec_resn_i = spec_resn.rectangle()

		gen_reso = uia_controls.ListItemWrapper(open_row.item(top_row.children_texts().index('General Resolution')).element_info)
		gen_reso_i = gen_reso.rectangle()

		spec_reso = uia_controls.ListItemWrapper(open_row.item(top_row.children_texts().index('Specific Resolution')).element_info)
		spec_reso_i = spec_reso.rectangle()

		pag.click(*c_coords)
		dlg = app.get_popup()
		while dlg:
			log.debug(f"Operations Reason Grid dialog text: '{dlg.Text}'")
			dlg[0].close()
			dlg = app.get_popup()
		q = []
		if not partial:
			q.append((c_coords, str(full_row.General_Reason)))
		c_coords = center(x1=spec_resn_i.left, y1=spec_resn_i.top, x2=spec_resn_i.right, y2=spec_resn_i.bottom)
		q.append((c_coords, str(unit.specific_reason)))

		c_coords = center(x1=gen_reso_i.left, y1=gen_reso_i.top, x2=gen_reso_i.right, y2=gen_reso_i.bottom)
		q.append((c_coords, str(unit.general_resolution)))

		c_coords = center(x1=spec_reso_i.left, y1=spec_reso_i.top, x2=spec_reso_i.right, y2=spec_reso_i.bottom)
		q.append((c_coords, str(unit.specific_resolution)))
		for coord, num in q:
			pag.click(*coord)
			sleep(0.5)
			pag.typewrite(str(num))
			sleep(0.5)
		pag.hotkey('ctrl', 's')
		if int(unit.general_resolution) == 10000 and int(unit.specific_resolution) == 100:
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
			                                f"\n[{unit.operator_initials} {unit.datetime.strftime('%m/%d/%Y')}]")
		else:
			sl_win.ResolutionNotesEdit.set_text(f"[{unit.operator_initials} {unit.datetime.strftime('%m/%d/%Y')}]")
		sl_win.ResolutionNotesEdit.send_keystrokes('^s')
		unit.sro_operations_time += unit.sro_operations_timer.stop()
		sl_uia.CancelCloseButton.click()
		sl_uia.CancelCloseButton.click()
		sleep(0.5)
		sl_win.ServiceOrderLinesButton.wait('visible', 2, 0.09)
		sl_win.send_keystrokes('{F4}')
		sl_win.send_keystrokes('{F5}')
	except Exception as ex:
		sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
		sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
		if issubclass(type(ex), NoSROError):
			log.exception("No SRO Error!")
			for x in units:
				x.skip(reason='No SRO', batch_amt=len(units))
		elif issubclass(type(ex), NoOpenSROError):
			log.exception("No Open SRO Error!")
			for x in units:
				x.skip(reason='No Open SRO', batch_amt=len(units))
		elif issubclass(type(ex), SyteLineCreditHoldError):
			log.exception("Credit Hold Error!")
			string = 'Credit Hold'
			# string = f"Credit Hold({ex._cust})"
			for x in units:
				x.skip(reason=string, batch_amt=len(units))
			# pag.press('esc', 40)
		else:
			log.exception("SOMETHING HAPPENED!!!")
			for x in units:
				x.skip(batch_amt=len(units))
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
		log.info(f"Unit: {unit.serial_number_prefix+unit.serial_number} completed")
		for x in units:
			x.complete(batch_amt=len(units))
