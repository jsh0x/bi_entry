#! python3 -W ignore
# coding=utf-8
import logging
import warnings
from time import sleep
from typing import List

import pyautogui as pag
import pywinauto.timings
from pywinauto import keyboard
from pywinauto.controls import common_controls, uia_controls, win32_controls

from common import *
from common import PuppetMaster, DataGridNEW
from config import *
from constants import DB_TABLE, REGEX_CREDIT_HOLD, REGEX_NEGATIVE_ITEM, SYTELINE_WINDOW_TITLE, TRANSACTION_STATUS, WHITE
from exceptions import *
from utils.sql import SQL
from utils.tools import get_background_color
import numpy as np

log = logging.getLogger('root')
# TODO: Rework process

starting_forms = {'Units'}

def dummy(self: PuppetMaster.Puppet, default_wait: float, units: List[Unit]):
	retval = {}
	# UNITS FORM START - - - - - - - - - - - - - - - - - - - - - - - - -
	app = self.app
	app.verify_form("Units")
	sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
	sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
	unit = units[0]
	timer = Timer.start()  # Timer Start
	sl_win.send_keystrokes('{F4}')
	pywinauto.timings.wait_until_passes(default_wait, 0.1, sl_win.ServiceOrderLinesButton.wait, Exception, 'ready')
	retval['FiP'] = timer.stop()  # Timer Stop

	sl_win.set_focus()
	timer = Timer.start()  # Timer Start
	sl_win.send_keystrokes('%s')  # Actions Menu, (ALT + S)
	pywinauto.timings.wait_until_passes(default_wait, 0.1, sl_win.ActionsMenuItem.wait, Exception, 'ready')
	retval['Actions_Menu'] = timer.stop()  # Timer Stop

	timer = Timer.start()  # Timer Start
	sl_win.send_keystrokes('o')  # Notes For Current, (O)
	pywinauto.timings.wait_until_passes(default_wait, 0.1, sl_win.Notes.wait, Exception, 'ready')
	retval['Current_Notes'] = timer.stop()  # Timer Stop

	sl_uia.CancelCloseButton.click()
	sleep(default_wait)
	sl_win.ServiceOrderLinesButton.wait('ready')
	# SRO LINES FORM START - - - - - - - - - - - - - - - - - - - - - - - -
	sl_win.ServiceOrderLinesButton.click()
	sleep(default_wait)
	sl_win.ServiceOrderOperationsButton.wait('ready')
	app.find_value_in_collection('Service Order Lines', 'SRO (SroNum)', unit.sro)
	sleep(default_wait)
	app.win32.top_window().send_keystrokes('{ESC}')
	sleep(default_wait)
	sl_win.ServiceOrderOperationsButton.wait('ready')
	# SRO OPERATIONS FORM START - - - - - - - - - - - - - - - - - - - - - - - -
	sl_win.ServiceOrderOperationsButton.click()
	sleep(default_wait)
	sl_win.SROLinesButton.wait('ready')
	common_controls.TabControlWrapper(sl_win.TabControl).select('Reasons')
	sleep(default_wait)
	reason_grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info).rectangle()
	pag.click(((reason_grid.right - reason_grid.left) / 2) + reason_grid.left, ((reason_grid.bottom - reason_grid.top) / 2) + reason_grid.top)
	sleep(default_wait)
	pag.press('enter')
	sleep(default_wait)
	pag.press('esc')
	sleep(default_wait)
	sl_uia.CancelCloseButton.click()
	sleep(default_wait)
	sl_win.SROTransactionsButton.wait('ready')
	# SRO TRANSACTIONS FORM START - - - - - - - - - - - - - - - - - - - - - - - -
	# TODO: Write part number and spam enter, then get outta there
	sl_win.SROTransactionsButton.click()
	sleep(default_wait)
	transaction_grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info)
	transaction_rect = transaction_grid.rectangle()
	pag.click((transaction_rect.width() / 2) + transaction_rect.left, (transaction_rect.height() / 2) + transaction_rect.top)
	pag.press('down', 40)

def runOLD(self, units: List[Unit]):
	app = self.app
	pywinauto.timings.Timings.Fast()
	units = units if type(units) is list else [units]
	unit = units[0]
	# log.info(f"Starting Transact script with unit: {unit.serial_number_prefix+unit.serial_number}")
	sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
	sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
	# if not sl_win.exists():
	# for x in units:
	# x.reset()
	# sys.exit(1)
	# log.debug([x.texts()[0] for x in sl_uia.WindowMenu.items()])
	# app.verify_form('Units')
	print(get_background_color(sl_win.UnitEdit))
	sleep(0.2)
	sl_win.UnitEdit.set_text(unit.serial_number.to_string())  # Input serial number
	sleep(0.2)
	print(get_background_color(sl_win.UnitEdit))
	sl_win.send_keystrokes('{F4}')  # Filter in Place
	count = 0
	print(get_background_color(sl_win.UnitEdit))
	quit()
	try:
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
		if not debug:
			for x in units:
				x.start()
		log.debug(sl_win.ServiceOrderLinesButton.get_properties())
		if not sl_win.ServiceOrderLinesButton.is_enabled():
			raise NoOpenSROError(serial_number=unit.serial_number, sro=unit.sro_num,
			                     msg="Service Order Lines Button is disabled")
		log.debug("Service Order Lines Button clicked")
		sl_win.set_focus()
		timer.start()
		sl_win.ServiceOrderLinesButton.click()
		sl_win.ServiceOrderOperationsButton.wait('visible', 2, 0.09)
		# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
		t_temp = timer.stop()
		log.debug(
				f"Time waited for Service Order Lines: {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
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
		timer.start()
		sl_win.ServiceOrderOperationsButton.click()
		sl_win.SROLinesButton.wait('visible', 2, 0.09)
		# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
		t_temp = timer.stop()
		log.debug(
				f"Time waited for Service Order Operations: {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
		unit.sro_operations_timer.start()
		if sl_win.StatusEdit3.texts()[0].strip() == 'Closed':
			status = win32_controls.EditWrapper(sl_win.StatusEdit3.element_info)
			status.set_text('Open')
			status.click_input()
			pag.press('tab')
			# handle_popup(best_match='ResetDatesDialog')
			pag.press('esc')
			save = sl_uia.SaveButton
			if not debug:
				save.click()
		sl_win.SROTransactionsButton.wait('enabled', 2, 0.09)
		sl_win.SROTransactionsButton.wait('enabled', 2, 0.09)
		# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
		print("START Transaction Unit list-comprehension")
		transaction_units = [(y, i) for i, x in enumerate(units) if x.parts for y in x.parts]
		print("END Transaction Unit list-comprehension")
		log.debug(f"Total parts: {', '.join([str(p[0]) for p in transaction_units])}")
		if transaction_units:
			try:
				print("TRANSACTION")
				sroo_time = unit.sro_operations_timer.stop() / len(units)
				for temp in units:
					temp.sro_operations_time += sroo_time
				transactions_timer = TestTimer()
				transactions_timer.start()
				sl_win.set_focus()
				timer.start()
				sl_win.SROTransactionsButton.click()
				log.debug("SRO Transactions Button clicked")
				sl_win.FilterDateRangeEdit.wait('ready', 2, 0.09)
				t_temp = timer.stop()
				log.debug(
						f"Time waited for SRO Transactions: {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
				log.info("Starting transactions")
				print("TRANSACTION 2")
				sl_win.FilterDateRangeEdit.set_text(unit.eff_date.strftime('%m/%d/%Y'))
				timer.start()
				sl_win.ApplyFilterButton.click()
				sl_win.ApplyFilterButton.wait('ready', 2, 0.09)
				print("FILTER SET")
				t_temp = timer.stop()
				print("TIMER STOP?")
				log.debug(
						f"Time waited for first Application of Filter: {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
				print("DEBUG?")
				transaction_grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info)
				print("TRANSACTION GRID")
				log.debug(transaction_grid.get_properties())
				posted_parts = access_grid(transaction_grid,
				                           ['Posted', 'Item', 'Location', 'Quantity', 'Billing Code', 'Trans Date'],
				                           condition=('Posted', True), requirement='Item')
				print("POSTED PARTS")
				log.debug(f"Posted parts: {posted_parts}")
				posted_part_numbers = {p.Item for p in posted_parts}
				sl_win.IncludePostedButton.click()
				timer.start()
				sl_win.ApplyFilterButton.click()
				sl_win.ApplyFilterButton.wait('ready', 2, 0.09)
				t_temp = timer.stop()
				log.debug(
						f"Time waited for second Application of Filter: {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
				unposted_parts = access_grid(transaction_grid,
				                             ['Posted', 'Item', 'Location', 'Quantity', 'Billing Code', 'Trans Date'],
				                             requirement='Item')
				log.debug(f"Unposted parts: {unposted_parts}")
				unposted_part_numbers = {p.Item for p in unposted_parts}
				print("UNPOSTED PARTS")
				row_i = None
				top_row = transaction_grid.children()[transaction_grid.children_texts().index('Top Row')]
				log.debug(F"Columns: {top_row.children_texts()[1:10]}")
				loc_rec_list = []
				qty_rec_list = []
				bc_rec_list = []
				if unit.suffix == 'Direct' or unit.suffix == 'RTS':
					bc = 'Contract'
				else:
					bc = 'No Charge'
				all_transacted_parts = []
				for part, i in transaction_units:
					# pag._failSafeCheck()
					unit = units[i]
					if (part.part_number in posted_part_numbers) or (part.part_number in unposted_part_numbers):
						continue
					unit.sro_transactions_timer.start()
					if row_i is None:
						if unposted_parts:
							row_i = -1
						else:
							row_i = -2
					else:
						row_i = -1
					log.debug(f"Attempting to transact part {part}")
					last_row = uia_controls.ListViewWrapper(transaction_grid.children()[row_i].element_info)
					item = uia_controls.ListItemWrapper(
							last_row.item(top_row.children_texts().index('Item')).element_info)
					r_i = item.rectangle()
					# sl_win.set_focus()
					c_coords = center(x1=r_i.left, y1=r_i.top, x2=r_i.right, y2=r_i.bottom)
					pag.click(*c_coords)
					last_row = uia_controls.ListViewWrapper(transaction_grid.children()[-2].element_info)
					location = uia_controls.ListItemWrapper(
							last_row.item(top_row.children_texts().index('Location')).element_info)
					quantity = uia_controls.ListItemWrapper(
							last_row.item(top_row.children_texts().index('Quantity')).element_info)
					billcode = uia_controls.ListItemWrapper(
							last_row.item(top_row.children_texts().index('Billing Code')).element_info)
					r_loc = location.rectangle()
					r_qty = quantity.rectangle()
					r_bill = billcode.rectangle()
					loc_rec_list.append(
							(center(x1=r_loc.left, y1=r_loc.top, x2=r_loc.right, y2=r_loc.bottom), str(part.location), i))
					if part.quantity > 1:
						qty_rec_list.append((center(x1=r_qty.left, y1=r_qty.top, x2=r_qty.right, y2=r_qty.bottom),
						                     str(part.quantity), i))
					bc_rec_list.append(
							(center(x1=r_bill.left, y1=r_bill.top, x2=r_bill.right, y2=r_bill.bottom), bc, i))
					pag.typewrite(str(part.part_number))
					sleep(0.5)
					pag.press('enter', 10, interval=0.05)
					pag.click(*c_coords)
					unit.parts_transacted.append(part)
					all_transacted_parts.append(part)
					unit.sro_transactions_time += unit.sro_transactions_timer.stop()
				for coord, qty, i in qty_rec_list:
					unit = units[i]
					unit.sro_transactions_timer.start()
					pag.click(*coord)
					sleep(0.2)
					pag.press('backspace', 20)
					pag.press('delete', 20)
					sleep(0.2)
					pag.typewrite(qty)
					sleep(0.2)
					pag.press('enter')
					sleep(0.5)
					unit.sro_transactions_time += unit.sro_transactions_timer.stop()
				for coord, loc, i in loc_rec_list:
					unit = units[i]
					unit.sro_transactions_timer.start()
					pag.click(*coord)
					sleep(0.2)
					pag.press('backspace', 20)
					pag.press('delete', 20)
					sleep(0.2)
					pag.typewrite(loc)
					sleep(0.2)
					pag.press('enter')
					sleep(0.5)
					unit.sro_transactions_time += unit.sro_transactions_timer.stop()
				for coord, bc, i in bc_rec_list:
					unit = units[i]
					unit.sro_transactions_timer.start()
					pag.click(*coord)
					sleep(0.2)
					pag.press('backspace', 20)
					pag.press('delete', 20)
					sleep(0.2)
					pag.typewrite(bc)
					sleep(0.2)
					pag.press('enter')
					sleep(0.5)
					unit.sro_transactions_time += unit.sro_transactions_timer.stop()
			except Exception as ex:  # Placeholder
				raise ex
			else:
				if (len(all_transacted_parts) + len(unposted_part_numbers)) > 0:
					save = sl_uia.SaveButton
					total_parts = (len(all_transacted_parts) + len(unposted_part_numbers))
					# TODO: Work on slimming down unneeded transaction time
					if total_parts < 4:
						wait_seconds = 4
					elif total_parts < 8:
						wait_seconds = 6
					else:
						wait_seconds = 8
					sl_win.set_focus()
					if not debug:
						save.click()
						dlg = app.get_popup()
						while dlg:
							log.debug(f"Transaction Save dialog text: '{dlg.Text}'")
							dlg[0].close()
							dlg = app.get_popup()
						log.debug("Saved")
					sl_win.set_focus()
					if not debug:
						sl_win.PostBatchButton.click()
						dlg = app.get_popup(6)
						error = None
						while dlg:
							log.debug(f"Transaction Post Batch dialog text: '{dlg.Text}'")
							m1 = REGEX_CREDIT_HOLD.match(dlg.Text)
							m2 = REGEX_NEGATIVE_ITEM.match(dlg.Text)
							if m1 is not None:
								pag.press('enter')
								error = SyteLineCreditHoldError(cust=m1.group('customer'), msg="Cannot transact parts")
								dlg = app.get_popup(2)
							elif m2 is not None:
								pag.press('enter')
								warnings.warn(NegativeQuantityWarning(part=m2.group('item'), qty=m2.group('quantity'),
								                                      loc=m2.group('location')))
								log.warning("Negative Quantity!")
								dlg = app.get_popup(4)
							else:
								dlg = app.get_popup()
								pag.press('enter')
						else:
							if error is not None:
								raise error
					sl_win.PostBatchButton.wait('ready', 2, 0.09)
					log.debug("Batch posted")
					sl_win.set_focus()
					if not debug:
						save.click()
					sleep(1)
			dlg = app.get_popup(3)
			while dlg:
				log.debug(f"Transaction 2nd Save dialog text: '{dlg.Text}'")
				dlg[0].close()
				dlg = app.get_popup()
			sl_win.set_focus()
			for presses in range(2):
				sl_uia.CancelCloseButton.click()
			sl_win.ServiceOrderOperationsButton.wait('visible', 2, 0.09)
			sl_win.set_focus()
			timer.start()
			sl_win.ServiceOrderOperationsButton.click()
			sl_win.SROLinesButton.wait('visible', 2, 0.09)
			t_temp = timer.stop()
			log.debug(
					f"Time waited for Service Order Lines(part 2): {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
			i2 = [i for i, x in enumerate(units) if x.parts]
			srot_time = unit.sro_transactions_timer.stop() / len(i2)
			for i in i2:
				unit = units[i]
				unit.sro_transactions_time += srot_time
			unit = units[0]
			unit.sro_operations_timer.start()
		# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
		log.debug(f"Recieved date: {sl_win.ReceivedDateEdit.texts()[0].strip()}")
		log.debug(f"Floor date: {sl_win.FloorDateEdit.texts()[0].strip()}")
		log.debug(f"Completed date: {sl_win.CompletedDateEdit.texts()[0].strip()}")
		i2 = {x.datetime: i for i, x in enumerate(units)}
		newest_unit = units[i2[max(list(i2.keys()))]]
		oldest_unit = units[i2[min(list(i2.keys()))]]
		if not debug:
			if not sl_win.ReceivedDateEdit.texts()[0].strip():
				sl_win.ReceivedDateEdit.set_text(unit.eff_date.strftime('%m/%d/%Y %I:%M:%S %p'))
				sl_win.ReceivedDateEdit.send_keystrokes('^s')
			if not sl_win.FloorDateEdit.texts()[0].strip():
				sl_win.FloorDateEdit.set_text(oldest_unit.datetime.strftime('%m/%d/%Y %I:%M:%S %p'))
				sl_win.FloorDateEdit.send_keystrokes('^s')
			if not sl_win.CompletedDateEdit.texts()[0].strip() and has_qc:
				sl_win.CompletedDateEdit.set_text(newest_unit.datetime.strftime('%m/%d/%Y %I:%M:%S %p'))
			sl_win.CompletedDateEdit.send_keystrokes('^s')
			sleep(0.5)
			log.debug(f"Recieved date: {sl_win.ReceivedDateEdit.texts()[0].strip()}")
			log.debug(f"Floor date: {sl_win.FloorDateEdit.texts()[0].strip()}")
			log.debug(f"Completed date: {sl_win.CompletedDateEdit.texts()[0].strip()}")
			if not sl_win.CompletedDateEdit.texts()[0].strip() and has_qc:
				sl_win.CompletedDateEdit.set_text(newest_unit.datetime.strftime('%m/%d/%Y %I:%M:%S %p'))
				sl_win.CompletedDateEdit.send_keystrokes('^s')
				sleep(2)
			log.debug(f"Recieved date: {sl_win.ReceivedDateEdit.texts()[0].strip()}")
			log.debug(f"Floor date: {sl_win.FloorDateEdit.texts()[0].strip()}")
			log.debug(f"Completed date: {sl_win.CompletedDateEdit.texts()[0].strip()}")
		# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
		common_controls.TabControlWrapper(sl_win.TabControl).select('Reasons')  # Open 'Reasons' Tab
		if has_qc:
			reason_grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info)
			reason_rows = access_grid(reason_grid, ['General Reason', 'Specific Reason', 'General Resolution',
			                                        'Specific Resolution'])
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
			if not debug:
				pag.hotkey('ctrl', 's')
			resn_notes = sl_win.ReasonNotesEdit
			resn_notes.click_input()
			pag.press('end', 30)
			if resn_notes.texts()[0].strip():
				pag.press('enter')
			pag.typewrite("[UDI]")
			pag.press('enter')
			pag.typewrite("[PASSED ALL TESTS]")
		reso_notes = sl_win.ResolutionNotesEdit
		if transaction_units:
			all_part_units = [i for i, x in enumerate(units) if x.parts]
			reso_notes.click_input()
			pag.press('end', 30)
			if reso_notes.texts()[0].strip():
				pag.press('enter')
			for i in all_part_units:
				unit = units[i]
				reso_string = ", ".join([p.display_name for p in unit.parts])
				pag.typewrite(f"[{reso_string}]")
				pag.press('enter')
				pag.typewrite(f"[{unit.operator_initials} {unit.datetime.strftime('%m/%d/%Y')}]")
				if len(units) > 1:
					pag.press('enter')
			else:
				if len(units) > 1:
					pag.press('backspace')
		if not debug:
			pag.hotkey('ctrl', 's')
			status = win32_controls.EditWrapper(sl_win.StatusEdit3.element_info)
			status.send_keystrokes('^s')
			status.wait_for_idle()
		if has_qc or units[0].SRO_Operations_status == 'Closed':
			status = win32_controls.EditWrapper(sl_win.StatusEdit3.element_info)
			sl_win.set_focus()
			status.set_keyboard_focus()
			status.send_keystrokes('{DOWN}{DOWN}')
			try:
				if not debug:
					status.send_keystrokes('^s')
				sleep(1)
			except TimeoutError:
				pass
			finally:
				keyboard.SendKeys('{ESC}')
		unit = units[0]
		sroo_time = unit.sro_operations_timer.stop() / len(units)
		for temp in units:
			temp.sro_operations_time += sroo_time
		for presses in range(2):
			sl_uia.CancelCloseButton.click()
		sl_win.UnitEdit.wait('visible', 2, 0.09)
		sleep(0.2)
		sl_win.send_keystrokes('{F4}')  # Clear Filter
		sleep(0.2)
		sl_win.send_keystrokes('{F5}')  # Clear Filter
		sleep(0.2)
		if debug:
			quit()
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

def count_units(sql: SQL, table: str = DB_TABLE, group_serial: bool = False):
	return _check_units(sql=sql, status=TRANSACTION_STATUS, table=table, group_serial=group_serial)

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
	ID = mssql.execute("""SELECT [Id] FROM PyComm WHERE Status = %s AND [Serial Number] = %s ORDER BY DateTime ASC""", (TRANSACTION_STATUS, serial_number))
	if ID:
		return Unit.from_serial_number(serial_number, TRANSACTION_STATUS)
	else:
		return None

def runNEW(self: PuppetMaster.Puppet, units: List[Unit]):
	try:
		_base_process(True, self, units=units)
	except Exception as ex:
		log.exception("SOMETHING HAPPENED!!!")
		app = self.app
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
			# x.complete(batch_amt=len(units))
			x.reset()

def run(app: Application, units: List[Unit]):
	try:
		_base_process(False, app, units=units)
	except Exception as ex:
		log.exception("SOMETHING HAPPENED!!!")
		sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
		sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
		for x in units:
			# x.reset()
			x.skip(ex, batch_amt=len(units))
		# quit()
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

def dummy2(self: PuppetMaster.Puppet, default_wait: float, units: List[Unit]):
	try:
		_base_process(True, self, default_wait=default_wait, units=units)
	except Exception as ex:
		app = self.app
		sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
		sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
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
			return False
	else:
		log.info(f"Unit: {units[0].serial_number} completed")
		for x in units:
			x.complete(batch_amt=len(units))
		return True

"""def _base_process(debug_mode: bool, self: PuppetMaster.Puppet, *, units: List[Unit]=None):
	app = self.app"""
def _base_process(debug_mode: bool, app: Application, *, units: List[Unit]=None):
	pywinauto.timings.Timings.Fast()
	unit = units[0]
	sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
	sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
	sleep(0.2)
	sl_win.UnitEdit.set_text(unit.serial_number)
	sleep(0.2)
	sl_win.send_keystrokes('{F4}')
	while get_background_color(sl_win.UnitEdit) == WHITE:
		if sl_win.UnitEdit.texts()[0].strip() != unit.serial_number:
			if not sl_win.UnitEdit.texts()[0].strip():
				raise InvalidSerialNumberError(unit.serial_number)
			else:
				raise SyteLineFilterInPlaceError(unit.serial_number, f"Expected input serial number '{unit.serial_number}', returned '{sl_win.UnitEdit.texts()[0].strip()}'")
	if not debug_mode:
		for x in units:
			x.start()
	if not sl_win.ServiceOrderLinesButton.is_enabled():
		raise NoOpenSROError(serial_number=unit.serial_number.number, sro=unit.sro, msg="Service Order Lines Button is disabled")
	sl_win.set_focus()
	sl_win.ServiceOrderLinesButton.click()
	sl_win.ServiceOrderOperationsButton.wait('visible', 10, 0.09)
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
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
	sl_win.set_focus()
	sl_win.ServiceOrderOperationsButton.click()
	sl_win.SROLinesButton.wait('visible', 10, 0.09)
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	timer = Timer.start()
	if sl_win.StatusEdit3.texts()[0].strip() == 'Closed':
		status = win32_controls.EditWrapper(sl_win.StatusEdit3.element_info)
		status.set_text('Open')
		status.click_input()
		pag.press('tab')
		# handle_popup(best_match='ResetDatesDialog')
		pag.press('esc')
		save = sl_uia.SaveButton
		if not debug_mode:
			save.click()
	sro_operations_time = timer.stop() / len(units)
	for x in units:
		x.sro_operations_time += sro_operations_time
	sl_win.SROTransactionsButton.wait('enabled', 10, 0.09)
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	if any(len(x.parts) > 0 for x in units) or debug_mode:
		sl_win.set_focus()
		sl_win.SROTransactionsButton.click()

		sleep(10)
		transaction_grid = DataGridNEW.from_AutomationId(app, 'MatlGrid', ['Posted', 'Item', 'Location', 'Quantity', 'Billing Code', 'Trans Date'])
		transaction_grid.populate()
		log.info("Starting transactions")

		posted_parts = [row[1] for row in transaction_grid.grid if row[1] and (row[5] >= unit.eff_date) and row[0]]
		log.debug(f"Posted parts: {posted_parts}")

		unposted_parts = [row[1] for row in transaction_grid.grid if row[1] and (row[5] >= unit.eff_date) and not row[0]]
		log.debug(f"Unposted parts: {unposted_parts}")

		if unit.build.suffix == 'Direct' or unit.build.suffix == 'RTS':
			bc = 'Contract'
		else:
			bc = 'No Charge'

		for i, row in enumerate(transaction_grid.grid):
			if not np.count_nonzero(row):
				empty_row_index = i
				break

		for unit in units:
			part_list = []
			timer = Timer.start()
			for part in unit.parts:
				if (part.part_number in posted_parts) or (part.part_number in unposted_parts):
					continue
				i += 1
				log.debug(f"Attempting to transact part {part}")
				transaction_grid.set_cell('Item', i, part.part_number, specific=1)
				part_list.append((part, i))
				transaction_grid.set_cell('Location', i, part.location)
				if part.quantity > 1:
					transaction_grid.set_cell('Quantity', i, part.quantity)
				transaction_grid.set_cell('Billing Code', i, bc)
				# transaction_grid.select_cell(transaction_grid.get_cell('Item', i))
				# pag.press('enter', 10, interval=0.05)
				unit.parts_transacted.add(part)

			# for part, row_num in part_list:
			# 	transaction_grid.set_cell('Location', row_num, part.location)
			# 	if part.quantity > 1:
			# 		transaction_grid.set_cell('Quantity', row_num, part.quantity)
			# 	transaction_grid.set_cell('Billing Code', row_num, bc)

			transaction_grid.select_cell(transaction_grid.get_cell('Location', 1))

			print(transaction_grid.grid)

			if len(unit.parts_transacted) > 0:  # TODO: Work on slimming down unneeded transaction time
				if not debug_mode:
					save = sl_uia.SaveButton
					sl_win.set_focus()
					save.click()
					pag.press('esc', 4)
					dlg = app.get_popup()
					while dlg:
						log.debug(f"Transaction Save dialog text: '{dlg.Text}'")
						dlg[0].close()
						dlg = app.get_popup()
					pag.press('esc', 4)
					sl_win.set_focus()
					sl_win.PostBatchButton.click()
					pag.press('esc', 4)
					# dlg = app.get_popup(4)
					error = None
					while dlg:  # TODO: Refine this
						log.debug(f"Transaction Post Batch dialog text: '{dlg.Text}'")
						m1 = REGEX_CREDIT_HOLD.match(dlg.Text)
						m2 = REGEX_NEGATIVE_ITEM.match(dlg.Text)
						if m1 is not None:
							pag.press('enter')
							error = SyteLineCreditHoldError(cust=m1.group('customer'), msg="Cannot transact parts")
							dlg = app.get_popup(2)
						elif m2 is not None:
							pag.press('enter')
							warnings.warn(NegativeQuantityWarning(part=m2.group('item'), qty=m2.group('quantity'),
							                                      loc=m2.group('location')))
							log.warning("Negative Quantity!")
							dlg = app.get_popup(4)
						else:
							dlg = app.get_popup()
							pag.press('enter')
					else:
						if error is not None:
							raise error
					sl_win.PostBatchButton.wait('ready', 10, 0.09)
					log.debug("Batch posted")
					sl_win.set_focus()
					save.click()
			sro_transactions_time = timer.stop()
			unit.sro_transactions_time += sro_transactions_time
		# dlg = app.get_popup(2)
		# while dlg:
		# 	log.debug(f"Transaction 2nd Save dialog text: '{dlg.Text}'")
		# 	dlg[0].close()
		# 	dlg = app.get_popup()
		sl_win.set_focus()
		for presses in range(2):
			sl_uia.CancelCloseButton.click()
		sl_win.ServiceOrderOperationsButton.wait('visible', 10, 0.09)
		sl_win.set_focus()
		sl_win.ServiceOrderOperationsButton.click()
		sl_win.SROLinesButton.wait('visible', 10, 0.09)
	unit = units[0]
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	timer = Timer.start()
	log.debug(f"Recieved date: {sl_win.ReceivedDateEdit.texts()[0].strip()}")
	log.debug(f"Floor date: {sl_win.FloorDateEdit.texts()[0].strip()}")
	log.debug(f"Completed date: {sl_win.CompletedDateEdit.texts()[0].strip()}")
	if not sl_win.ReceivedDateEdit.texts()[0].strip():
		sl_win.ReceivedDateEdit.set_text(unit.eff_date.strftime('%m/%d/%Y %I:%M:%S %p'))
		if not debug_mode:
			sl_win.ReceivedDateEdit.send_keystrokes('^s')
	if not sl_win.FloorDateEdit.texts()[0].strip():
		sl_win.FloorDateEdit.set_text(unit.oldest_datetime.strftime('%m/%d/%Y %I:%M:%S %p'))
		if not debug_mode:
			sl_win.FloorDateEdit.send_keystrokes('^s')
	if not sl_win.CompletedDateEdit.texts()[0].strip() and unit.passed_QC:
		sl_win.CompletedDateEdit.set_text(unit.newest_datetime.strftime('%m/%d/%Y %I:%M:%S %p'))
		if not debug_mode:
			sl_win.CompletedDateEdit.send_keystrokes('^s')
		sleep(0.5)
		log.debug(f"Recieved date: {sl_win.ReceivedDateEdit.texts()[0].strip()}")
		log.debug(f"Floor date: {sl_win.FloorDateEdit.texts()[0].strip()}")
		log.debug(f"Completed date: {sl_win.CompletedDateEdit.texts()[0].strip()}")
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	common_controls.TabControlWrapper(sl_win.TabControl).select('Reasons')  # Open 'Reasons' Tab

	if unit.passed_QC:
		reason_grid = DataGridNEW.default(app, ['General Reason', 'Specific Reason', 'General Resolution', 'Specific Resolution'])
		reason_grid.populate()
		if sum(np.count_nonzero(row) // 4 for row in reason_grid.grid) > 0:
			pass
		else:
			gen_rsn = 1000
			for i, row in enumerate(reason_grid.grid):
				if reason_grid.grid[i, 0]:
					gen_rsn = reason_grid.grid[i, 0]
				if np.count_nonzero(row) < 4:
					break
			i += 1
			count = np.count_nonzero(row)
			if count == 1:
				reason_grid.set_cell('Specific Reason', i, 20)
				reason_grid.set_cell('General Resolution', i, 10000)
				reason_grid.set_cell('Specific Resolution', i, 100)
			elif count == 2:
				reason_grid.set_cell('General Resolution', i, 10000)
				reason_grid.set_cell('Specific Resolution', i, 100)
			else:
				reason_grid.set_cell('General Reason', i, gen_rsn)
				reason_grid.set_cell('Specific Reason', i, 20)
				reason_grid.set_cell('General Resolution', i, 10000)
				reason_grid.set_cell('Specific Resolution', i, 100)
			reason_grid.select_cell(reason_grid.get_cell('General Reason', 1))
			sleep(0.5)
			pag.hotkey('ctrl', 's')
			sleep(1)

		reason_notes = sl_win.ReasonNotesEdit
		reason_notes_text = reason_notes.texts()[0].strip()
		if '[UDI]\n[PASSED ALL TESTS]' not in reason_notes_text:
			if reason_notes_text:
				reason_notes_text += '\n'
			reason_notes_text += '[UDI]\n[PASSED ALL TESTS]'
			reason_notes.set_text(reason_notes_text.strip())
			sleep(0.5)
			pag.hotkey('ctrl', 's')
			sleep(1)

	if any(len(x.parts) > 0 for x in units):
		resolution_notes = sl_win.ResolutionNotesEdit
		resolution_notes_text = resolution_notes.texts()[0].strip()
		if resolution_notes_text:
			resolution_notes_text += '\n'
		for unit in units:
			additional_text = "[" + ", ".join([p.display_name for p in unit.parts]) + f"]\n[{unit.operator} {unit.datetime.strftime('%m/%d/%Y')}]\n"
			if additional_text not in resolution_notes_text:
				resolution_notes_text += additional_text
		resolution_notes.set_text(resolution_notes_text.strip())
		sleep(0.5)
		pag.hotkey('ctrl', 's')
		sleep(1)

	if not debug_mode:
		pag.hotkey('ctrl', 's')
		status = win32_controls.EditWrapper(sl_win.StatusEdit3.element_info)
		status.send_keystrokes('^s')
		status.wait_for_idle()
		if unit.passed_QC or not unit.sro_open_status['Operations']:
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
				keyboard.SendKeys('{ESC}')
	sro_operations_time = timer.stop() / len(units)
	for x in units:
		x.sro_operations_time += sro_operations_time
	sl_uia.CancelCloseButton.click()
	if unit.passed_QC:
		r_sros = unit.get_rogue_sros()
		while r_sros:
			sl_win.ServiceOrderOperationsButton.wait('visible', 5, 0.09)
			sleep(2)
			app.find_value_in_collection('Service Order Lines', 'SRO (SroNum)', r_sros[0]['sro'])
			dlg = app.get_popup(0.5)
			count = 0
			while dlg:
				log.debug(f"Lines Find SRO dialog text: '{dlg.Text}'")
				dlg[0].close()
				count += 1
				dlg = app.get_popup()
			sl_win.set_focus()
			sl_win.ServiceOrderOperationsButton.click()
			sl_win.SROLinesButton.wait('visible', 5, 0.09)
			timer = Timer.start()
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
				keyboard.SendKeys('{ESC}')
			sro_operations_time = timer.stop() / len(units)
			sl_uia.CancelCloseButton.click()
			sl_win.ServiceOrderOperationsButton.wait('visible', 5, 0.09)
			sleep(2)
			r_sros = unit.get_rogue_sros()
		# else:
		# 	sl_uia.CancelCloseButton.click()
	sl_uia.CancelCloseButton.click()
	sl_win.UnitEdit.wait('visible', 2, 0.09)
	sleep(0.2)
	sl_win.send_keystrokes('{F4}')  # Clear Filter
	sleep(0.2)
	sl_win.send_keystrokes('{F5}')  # Clear Filter
	sleep(0.2)
	return True
