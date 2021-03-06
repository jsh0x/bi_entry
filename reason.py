import datetime
import logging.config
import sys
from time import sleep
from typing import List

import pyautogui as pag
import pywinauto.timings
from pywinauto.controls import common_controls, uia_controls, win32_controls

from common import Application, Unit, access_grid, center
from constants import SYTELINE_WINDOW_TITLE
from exceptions import *

pag.FAILSAFE = False

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
			for x in units:
				x.reset()
			sys.exit(1)
		app.verify_form('Units')
		sleep(0.2)
		sl_win.UnitEdit.set_text(unit.serial_number_prefix + unit.serial_number)  # Input serial number
		sleep(0.2)
		sl_win.send_keystrokes('{F4}')  # Filter in Place
		count = 0
		# or (not sl_uia.UnitEdit.legacy_properties()['IsReadOnly'])
		while (sl_win.UnitEdit.texts()[0].strip() != unit.serial_number_prefix + unit.serial_number) and \
				sl_win.UnitEdit.texts()[0].strip():  # While actual serial number != attempted serial number
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
		for x in units:
			x.start()
		if not sl_win.ServiceOrderLinesButton.is_enabled():
			raise NoOpenSROError(serial_number=unit.serial_number, sro=unit.sro_num,
			                     msg="Service Order Lines Button is disabled")
		log.debug("Service Order Lines Button clicked")
		sl_win.set_focus()
		sl_win.ServiceOrderLinesButton.click()
		sl_win.ServiceOrderOperationsButton.wait('visible', 2, 0.09)
		sl_win.set_focus()
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
		for sub_unit in units:
			reason_grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info)
			reason_rows = access_grid(reason_grid, ['General Reason', 'Specific Reason', 'General Resolution',
			                                        'Specific Resolution'])
			done = False
			for row in reason_rows:
				if str(row.General_Resolution).strip() == str(sub_unit.general_resolution).strip() and \
								str(row.Specific_Resolution).strip() == str(sub_unit.specific_resolution).strip():
					done = True
					break
			if not done:
				if len(reason_rows) >= 6:
					top_row_temp = reason_grid.children()[reason_grid.children_texts().index('Top Row')]
					try:
						open_row_temp = uia_controls.ListViewWrapper(
								reason_grid.children()[reason_grid.children_texts().index('Top Row') + 7].element_info)
					except IndexError:
						open_row_temp = uia_controls.ListViewWrapper(
								reason_grid.children()[reason_grid.children_texts().index('Top Row') + 6].element_info)
					gen_resn_temp = uia_controls.ListItemWrapper(
							open_row_temp.item(top_row_temp.children_texts().index('General Reason')).element_info)
					gen_resn_temp_i = gen_resn_temp.rectangle()
					c_coords = center(x1=gen_resn_temp_i.left, y1=gen_resn_temp_i.top, x2=gen_resn_temp_i.right,
					                  y2=gen_resn_temp_i.bottom)
					pag.click(*c_coords)
					log.debug("CLICKED")
					pag.scroll(-(10 * (len(reason_rows) // 6)))
					log.debug("SCROLLED")
					reason_grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info)
					reason_rows = access_grid(reason_grid, ['General Reason', 'Specific Reason', 'General Resolution',
					                                        'Specific Resolution'])

				full_row = None
				empty_row_i = len(reason_rows) - 1
				partial = False
				for i, row in enumerate(reason_rows[::-1]):
					if {row.General_Reason, row.Specific_Reason, row.General_Resolution, row.Specific_Resolution} == {
						None, None, None, None}:
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
				open_row = uia_controls.ListViewWrapper(
						reason_grid.children()[empty_row_i + top_row_i + 1].element_info)

				gen_resn = uia_controls.ListItemWrapper(
						open_row.item(top_row.children_texts().index('General Reason')).element_info)
				gen_resn_i = gen_resn.rectangle()
				c_coords = center(x1=gen_resn_i.left, y1=gen_resn_i.top, x2=gen_resn_i.right, y2=gen_resn_i.bottom)

				spec_resn = uia_controls.ListItemWrapper(
						open_row.item(top_row.children_texts().index('Specific Reason')).element_info)
				spec_resn_i = spec_resn.rectangle()

				gen_reso = uia_controls.ListItemWrapper(
						open_row.item(top_row.children_texts().index('General Resolution')).element_info)
				gen_reso_i = gen_reso.rectangle()

				spec_reso = uia_controls.ListItemWrapper(
						open_row.item(top_row.children_texts().index('Specific Resolution')).element_info)
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
				q.append((c_coords, str(sub_unit.specific_reason)))

				c_coords = center(x1=gen_reso_i.left, y1=gen_reso_i.top, x2=gen_reso_i.right, y2=gen_reso_i.bottom)
				q.append((c_coords, str(sub_unit.general_resolution)))

				c_coords = center(x1=spec_reso_i.left, y1=spec_reso_i.top, x2=spec_reso_i.right, y2=spec_reso_i.bottom)
				q.append((c_coords, str(sub_unit.specific_resolution)))
				for coord, num in q:
					pag.click(*coord)
					sleep(0.5)
					pag.typewrite(str(num))
					sleep(0.5)
				pag.hotkey('ctrl', 's')
				pag.press('up', 40)
				if int(sub_unit.general_resolution) == 10000 and int(sub_unit.specific_resolution) == 100:
					if sl_win.ReasonNotesEdit.texts()[0].strip():
						sl_win.ReasonNotesEdit.set_text(sl_win.ReasonNotesEdit.texts()[0].strip() +
						                                "\n[POWER UP OK]\n[ACCEPTED]")
					else:
						sl_win.ReasonNotesEdit.set_text("[POWER UP OK]\n[ACCEPTED]")
				else:
					if sl_win.ReasonNotesEdit.texts()[0].strip():
						sl_win.ReasonNotesEdit.set_text(sl_win.ReasonNotesEdit.texts()[0].strip() +
						                                f"\n[{sub_unit.general_resolution_name}]")
					else:
						sl_win.ReasonNotesEdit.set_text(f"[{sub_unit.general_resolution_name}]")
				sl_win.ReasonNotesEdit.send_keystrokes('^s')

				if sl_win.ResolutionNotesEdit.texts()[0].strip():
					sl_win.ResolutionNotesEdit.set_text(sl_win.ResolutionNotesEdit.texts()[0].strip() +
					                                    f"\n[{sub_unit.operator_initials} {sub_unit.datetime.strftime('%m/%d/%Y')}]")
				else:
					sl_win.ResolutionNotesEdit.set_text(
							f"[{sub_unit.operator_initials} {sub_unit.datetime.strftime('%m/%d/%Y')}]")
			sl_win.ResolutionNotesEdit.send_keystrokes('^s')
		if units[0].SRO_Operations_status == 'Closed':
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
		sroo_time = unit.sro_operations_timer.stop() / len(units)
		for temp in units:
			temp.sro_operations_time += sroo_time
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
