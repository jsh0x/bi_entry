import logging.config
import sys
import warnings
from time import sleep
from typing import List

import pyautogui as pag
from pywinauto import timings
from pywinauto import keyboard
from pywinauto.controls import common_controls, uia_controls, win32_controls

from common import Application, TestTimer, Unit, access_grid, center, timer
from constants import REGEX_CREDIT_HOLD, REGEX_NEGATIVE_ITEM, SYTELINE_WINDOW_TITLE
from exceptions import *

logging.config.fileConfig('config.ini')
log = logging


def Transact(app: Application, units: List[Unit]):
	try:
		timings.Timings.Fast()
		units = units if type(units) is list else [units]
		unit = units[0]
		has_qc = True if [x for x in units if x.operation == 'QC'] else False
		log.info(f"Starting Transact script with unit: {unit.serial_number_prefix+unit.serial_number}")
		sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
		sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
		if not sl_win.exists():
			for x in units:
				x.reset()
			sys.exit(1)
		log.debug([x.texts()[0] for x in sl_uia.WindowMenu.items()])
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
			save.click()
		sl_win.SROTransactionsButton.wait('enabled', 2, 0.09)
		sl_win.SROTransactionsButton.wait('enabled', 2, 0.09)
		# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
		transaction_units = [(y, i) for i, x in enumerate(units) if x.parts for y in x.parts]
		log.debug(f"Total parts: {', '.join([str(p[0]) for p in transaction_units])}")
		if transaction_units:
			try:
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
				sl_win.FilterDateRangeEdit.set_text(unit.eff_date.strftime('%m/%d/%Y'))
				timer.start()
				sl_win.ApplyFilterButton.click()
				sl_win.ApplyFilterButton.wait('ready', 2, 0.09)
				t_temp = timer.stop()
				log.debug(
						f"Time waited for first Application of Filter: {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
				transaction_grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info)
				log.debug(transaction_grid.get_properties())
				posted_parts = access_grid(transaction_grid,
				                           ['Posted', 'Item', 'Location', 'Quantity', 'Billing Code', 'Trans Date'],
				                           condition=('Posted', True), requirement='Item')
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
				pag.press('up', 10, interval=0.05)
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
					save.click()
					# dlg = app.get_popup(2)
					dlg = app.get_popup()
					while dlg:
						log.debug(f"Transaction Save dialog text: '{dlg.Text}'")
						dlg[0].close()
						dlg = app.get_popup()
					log.debug("Saved")
					sl_win.set_focus()
					sl_win.PostBatchButton.click()
					sleep(2)
					new_count = 0
					error = None
					dlg = app.uia.window(class_name="#32770")
					while new_count < 4 and dlg.exists(2, 0.09):
						new_count += 1
						text = ''.join(text.replace('\r\n\r\n', '\r\n').strip() for cls in dlg.children() if
						               cls.friendly_class_name() == 'Static' for text in cls.texts())
						log.debug(f"Transaction Post Batch dialog text: '{text}'")
						m1 = REGEX_CREDIT_HOLD.match(text)
						m2 = REGEX_NEGATIVE_ITEM.match(text)
						dlg_obj = dlg.wrapper_object()
						dlg_obj.send_keystrokes('{ESC}')
						if m1 is not None:
							error = SyteLineCreditHoldError(cust=m1.group('customer'), msg="Cannot transact parts")
							new_count = 0
						elif m2 is not None:
							warnings.warn(NegativeQuantityWarning(part=m2.group('item'), qty=m2.group('quantity'),
							                                      loc=m2.group('location')))
							log.warning("Negative Quantity!")
							new_count = 0
						dlg = app.uia.window(class_name="#32770")
					if error:
						while dlg.exists(1, 0.09):
							dlg_obj = dlg.wrapper_object()
							dlg_obj.send_keystrokes('{ESC}')
							dlg = app.uia.window(class_name="#32770")
						raise error
					sl_win.PostBatchButton.wait('ready', 2, 0.09)
					log.debug("Batch posted")
					sl_win.set_focus()
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


"""Select m.Item, m.matl_qty from fs_sro_matl m(nolock)
Inner join fs_sro_line l(nolock)
on m.sro_num = l.sro_num and l.sro_line = m.sro_line
left join fs_sro_line l2(nolock)
on l.ser_num = l2.ser_num and l.recorddate < l2.recorddate
where l2.RecordDate is null and l.ser_num = 'OT1154319'"""
