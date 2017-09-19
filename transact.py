from sys import exc_info
import logging.config
from time import sleep
import sys
from traceback import TracebackException

from common import Application, Unit, REGEX_ROW_NUMBER as row_number_regex, center, REGEX_NEGATIVE_ITEM as negative_item_regex
from exceptions import *

from common import timer, access_grid
# import pyautogui as pag
import pywinauto as pwn
# from pywinauto import Application, application
from pywinauto import mouse, keyboard
import pywinauto.timings
from pywinauto.controls import uia_controls, win32_controls, common_controls

logging.config.fileConfig('config.ini')
log = logging

def Transact(app: Application, unit: Unit):
	pywinauto.timings.Timings.Fast()
	log.info(f"Starting Transact script with unit: {unit.serial_number_prefix+unit.serial_number}")
	form = 'Units'
	sl_win = app.win32.window(title_re='Infor ERP SL (EM)*')
	sl_uia = app.uia.window(title_re='Infor ERP SL (EM)*')
	# while sl_win.exists():
	if not sl_win.exists():
		unit.reset()
		sys.exit(1)
	log.debug([x.texts()[0] for x in sl_uia.WindowMenu.items()])
	if form not in app.forms:  # If required form is not open
		sl_win.send_keystrokes('^o')
		app.win32.SelectForm.AllContainingEdit.set_text(form)
		app.win32.SelectForm.set_focus()
		app.win32.SelectForm.FilterButton.click()
		common_controls.ListViewWrapper(app.win32.SelectForm.ListView).item(form).click()
		app.win32.SelectForm.set_focus()
		app.win32.SelectForm.OKButton.click()
		sleep(4)
		if form not in app.forms:
			raise ValueError()
	# TODO: Check if 'Units' form is focused, if not, do so
	try:
		try:
			def handle_popup(title: str='Infor ERP SL', specific_method: str=None, best_match: str=None):
				sleep(0.5)
				# negative_item_regex
				# pag._failSafeCheck()
				if best_match is not None:
					while sl_uia.child_window(best_match=best_match).exists():
						log.debug(sl_uia.child_window(best_match=best_match).get_properties())
						dlg_text = ''.join(
							text for cls, text in zip(sl_uia.child_window(best_match=best_match).children(), sl_uia.child_window(best_match=best_match).children_texts()) if cls.friendly_class_name() == 'Static')
						log.debug(f"Dialog text: {dlg_text}")
						if specific_method is None:
							log.debug("Close pop-up")
							sl_uia.child_window(best_match=best_match).close()
						else:
							button = [cls for cls, text in zip(sl_uia.child_window(best_match=best_match).children(), sl_uia.child_window(best_match=best_match).children_texts()) if
							          (cls.friendly_class_name() == 'Button') and (text.lower() == specific_method.lower())]
							if button:
								button = button[0]
							button.click()
							log.debug(f"Pop-up button '{specific_method}' clicked")
						sleep(0.2)
				else:
					while sl_uia.child_window(title=title).exists():
						log.debug(sl_uia.child_window(title=title).get_properties())
						dlg_text = ''.join(text for cls,text in zip(sl_uia.child_window(title=title).children(), sl_uia.child_window(title=title).children_texts()) if cls.friendly_class_name() == 'Static')
						log.debug(f"Dialog text: {dlg_text}")
						if specific_method is None:
							log.debug("Close pop-up")
							sl_uia.child_window(title=title).close()
						else:
							button = [cls for cls, text in zip(sl_uia.child_window(title=title).children(), sl_uia.child_window(title=title).children_texts()) if (cls.friendly_class_name() == 'Button') and (text.lower() == specific_method.lower())]
							if button:
								button = button[0]
							button.click()
							log.debug(f"Pop-up button '{specific_method}' clicked")
						sleep(0.2)
			for i in range(2):
				try:
					sl_win.UnitEdit.set_text(unit.serial_number_prefix+unit.serial_number)  # Input serial number
					sleep(0.2)
					sl_win.send_keystrokes('{F4}')  # Filter in Place
					count = 0
					# or (not sl_uia.UnitEdit.legacy_properties()['IsReadOnly'])
					while (sl_win.UnitEdit.texts()[0].strip() != unit.serial_number_prefix+unit.serial_number) and sl_win.UnitEdit.texts()[0].strip():  # While actual serial number != attempted serial number
						if count >= 30:
							raise SyteLineFilterInPlaceError(f"SyteLine had trouble entering serial number '{unit.serial_number_prefix+unit.serial_number}'")
						sleep(0.4)
						count += 1
					else:
						count = 0
					if sl_win.UnitEdit.texts()[0].strip() != unit.serial_number_prefix+unit.serial_number:
						if not sl_win.UnitEdit.texts()[0].strip():
							raise InvalidSerialNumberError(f"Expected input serial number '{unit.serial_number_prefix+unit.serial_number}', returned None")
						else:
							raise SyteLineFilterInPlaceError(f"Expected input serial number '{unit.serial_number_prefix+unit.serial_number}', returned '{sl_win.UnitEdit.texts()[0].strip()}'")
				except InvalidSerialNumberError as ex:
					if i < 1:
						sl_win.send_keystrokes('{F4}')
						sl_win.send_keystrokes('{F5}')
						if unit.serial_number_prefix == 'BE':
							unit._serial_number_prefix = 'ACB'
						elif unit.serial_number_prefix == 'ACB':
							unit._serial_number_prefix = 'BE'
					else:
						raise ex
				except SyteLineFilterInPlaceError as ex:
					if i < 1:
						sl_win.send_keystrokes('{F4}')
						sl_win.send_keystrokes('{F5}')
					else:
						raise ex
				else:
					if unit.serial_number_prefix == 'ACB':
						if '650' in unit.build:
							unit.build = '660'
							unit._whole_build = None
					elif unit.serial_number_prefix == 'BE':
						if '660' in unit.build:
							unit.build = '650'
							unit._whole_build = None
					break
			unit.start()
			# pag._failSafeCheck()
			log.debug(sl_win.ServiceOrderLinesButton.get_properties())
			if not sl_win.ServiceOrderLinesButton.is_enabled():
				raise UnitClosedError("Service Order Lines Button is disabled")
			# common_controls.TabControlWrapper(sl_win.TabControl).select('Owner History')  # Open 'Owner History' Tab
			# owner_history_grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info)  # Wrap DataGridView
			# log.debug(owner_history_grid.get_properties())
			# if owner_history_grid.control_count() < 3:  # If there are no SROs in the DataGrid
			# 	raise UnitClosedError("No SROs found in Data Grid")
			# initial_date = datetime.datetime.strptime(sorted(access_grid(owner_history_grid, 'Eff Date'), reverse=True)[0][0], '%m/%d/%Y')  # Get 'Initial Date'
			# log.info(f"Initial Date found: {initial_date.strftime('%m/%d/%Y')}")
			log.debug("Service Order Lines Button clicked")
			sl_win.set_focus()
			timer.start()
			sl_win.ServiceOrderLinesButton.click()
			sl_win.ServiceOrderOperationsButton.wait('visible', 2, 0.09)
		except Exception as ex:  # Placeholder
			raise ex
		try:
			t_temp = timer.stop()
			log.debug(f"Time waited for Service Order Lines: {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
			app.find_value_in_collection('Service Order Lines', 'SRO (SroNum)', unit.sro_num)
			# if len(sros) == 0:
			# 	raise UnitClosedError("No Open SROs found")
			# log.debug(f"Found Open SRO(s) and Line(s):{''.join([f' {sro},{line}' for sro,line in sros])}")
			# log.info(f"Found {len(sros)} Open SRO(s)")
			# for sro,line in sros:
			# 	form = 1
			# 	try:
			# 		sro2 = sl_win.SROEdit.texts()[0].strip()
			# 		line2 = sl_win.LineEdit.texts()[0].strip()
			# 		if not ((sro == sro2) and (line == line2)):
			# 			pass
			# 		if sl_win.StatusEdit2.texts()[0].strip() != 'Open':
			# 			log.warning(f"SRO '{sro}' closed on SRO Lines level")
			# 			raise SROClosedWarning(f"SRO '{sro}' closed on SRO Lines level")
			# 	except SROClosedWarning:
			# 		continue
			# 	try:
			# log.info(f"SRO '{sro}' open on SRO Lines level")
			log.debug("Service Order Operations Button clicked")
			sl_win.set_focus()
			timer.start()
			sl_win.ServiceOrderOperationsButton.click()
			sl_win.SROLinesButton.wait('visible', 2, 0.09)
		except Exception as ex:  # Placeholder
			raise ex

		try:
			# form = 2
			t_temp = timer.stop()
			log.debug(f"Time waited for Service Order Operations: {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
			unit.sro_operations_timer.start()
			# if sl_uia.StatEdit.texts()[0].strip() != unit.SRO_Operations_status:
			# 	raise InvalidSerialNumberError("")  # Placeholder
			# print(sl_win.StatusEdit3.texts()[0].strip())
			# pag._failSafeCheck()
			if sl_win.StatusEdit3.texts()[0].strip() == 'Closed':
				status = win32_controls.EditWrapper(sl_win.StatusEdit3.element_info)
				status.set_text('Open')
				status.send_keystrokes('{TAB}')
				handle_popup(best_match='ResetDatesDialog')
				save = sl_uia.SaveButton
				save.click()
			sl_win.SROTransactionsButton.wait('enabled', 2, 0.09)
			sl_win.SROTransactionsButton.wait('enabled', 2, 0.09)
			# 	if sl_win.StatusEdit3.texts()[0].strip() != 'Open' or not sl_win.SROTransactionsButton.is_enabled():
			# 		log.warning(f"SRO '{sro}' closed on SRO Operations level")
			# 		raise SROClosedWarning(f"SRO '{sro}' closed on SRO Operations level")
			# 	log.info(f"SRO '{sro}' open on SRO Operations level")
			# 		except SROClosedWarning:
			# 			sl_win.CancelCloseToolbarButton.click()
			# 			continue
			# 		else:
			# 			break
			# 	else:
			# 		raise UnitClosedError("No Open SROs found")
			# except UnitClosedError as ex:
			# 	log.exception(f"Unit '{unit.serial_number_prefix+unit.serial_number}' has no open SROs")
			# 	for presses in range(form):
			# 		sl_win.CancelCloseToolbarButton.click()
			# 	raise ex
			if unit.parts:
				try:
					unit.sro_operations_time += unit.sro_operations_timer.stop()
					unit.sro_transactions_timer.start()
					sl_win.set_focus()
					timer.start()
					sl_win.SROTransactionsButton.click()
					log.debug("SRO Transactions Button clicked")
					# sl_win.PostBatchButton.wait('active', 2, 0.09)
					sl_win.FilterDateRangeEdit.wait('ready', 2, 0.09)
					t_temp = timer.stop()
					log.debug(f"Time waited for SRO Transactions: {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
					log.info("Starting transactions")
					sl_win.FilterDateRangeEdit.set_text(unit.eff_date.strftime('%m/%d/%Y'))
					timer.start()
					# sl_win.FilterDateRangeEdit2.set_text()
					sl_win.ApplyFilterButton.click()
					sl_win.ApplyFilterButton.wait('ready', 2, 0.09)
					t_temp = timer.stop()
					log.debug(f"Time waited for first Application of Filter: {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
					transaction_grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info)
					log.debug(transaction_grid.get_properties())
					# Columns to get:
					# 'Posted', 'Item', 'Location', 'Quantity', 'Billing Code', 'Trans Date'
					posted_parts = access_grid(transaction_grid, ['Posted', 'Item', 'Location', 'Quantity', 'Billing Code', 'Trans Date'], condition=('Posted', True), requirement='Item')
					log.debug(f"Posted parts: {posted_parts}")
					posted_part_numbers= {p.Item for p in posted_parts}
					sl_win.IncludePostedButton.click()
					timer.start()
					sl_win.ApplyFilterButton.click()
					sl_win.ApplyFilterButton.wait('ready', 2, 0.09)
					t_temp = timer.stop()
					log.debug(f"Time waited for second Application of Filter: {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
					unposted_parts = access_grid(transaction_grid, ['Posted', 'Item', 'Location', 'Quantity', 'Billing Code', 'Trans Date'], requirement='Item')
					log.debug(f"Unposted parts: {unposted_parts}")
					unposted_part_numbers= {p.Item for p in unposted_parts}
					# TODO: Based on already posted and unposted, transact accordingly
					row_i = None
					columns = ['Item', 'Location', 'Quantity', 'Billing Code', 'Trans Date']
					top_row = transaction_grid.children()[transaction_grid.children_texts().index('Top Row')]
					log.debug(F"Columns: {top_row.children_texts()[1:10]}")
					loc_rec_list = []
					for part in unit.parts:
						# pag._failSafeCheck()
						if (part.part_number in posted_part_numbers) or (part.part_number in unposted_part_numbers):
							continue
						if row_i is None:
							if unposted_parts:
								row_i = -1
							else:
								row_i = -2
						else:
							row_i = -1
						log.debug(f"Attempting to transact part {part}")
						last_row = uia_controls.ListViewWrapper(transaction_grid.children()[row_i].element_info)
						item = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('Item')).element_info)
						r_i = item.rectangle()
						sl_win.set_focus()
						c_coords = center(x1=r_i.left, y1=r_i.top, x2=r_i.right, y2=r_i.bottom)
						mouse.click(coords=c_coords)
						handle_popup()
						last_row = uia_controls.ListViewWrapper(transaction_grid.children()[-2].element_info)
						location = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('Location')).element_info)
						quantity = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('Quantity')).element_info)
						billcode = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('Billing Code')).element_info)
						r_loc = location.rectangle()
						r_qty = quantity.rectangle()
						r_bill = billcode.rectangle()
						keyboard.SendKeys(str(part.part_number))
						sleep(0.5)
						if part.quantity > 1:
							sl_win.set_focus()
							c_coords = center(x1=r_qty.left, y1=r_qty.top, x2=r_qty.right, y2=r_qty.bottom)
							mouse.click(coords=c_coords)
							handle_popup()
							sleep(0.5)
							keyboard.SendKeys(str(part.quantity))
							sleep(0.5)
						sl_win.set_focus()
						c_coords = center(x1=r_bill.left, y1=r_bill.top, x2=r_bill.right, y2=r_bill.bottom)
						mouse.click(coords=c_coords)
						handle_popup()
						if unit.suffix == 'Direct' or unit.suffix == 'RTS':
							bc = 'Contract'
						else:
							bc = 'No Charge'
						sleep(0.5)
						keyboard.SendKeys(str(bc), with_spaces=True)
						sleep(0.5)
						loc_rec_list.append((center(x1=r_loc.left, y1=r_loc.top, x2=r_loc.right, y2=r_loc.bottom), part.location))
						unit.parts_transacted.append(part)
					else:
						last_row = uia_controls.ListViewWrapper(transaction_grid.children()[-1].element_info)
						item = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('Item')).element_info)
						r_i = item.rectangle()
						sl_win.set_focus()
						c_coords = center(x1=r_i.left, y1=r_i.top, x2=r_i.right, y2=r_i.bottom)
						mouse.click(coords=c_coords)
						handle_popup()
						for coord,loc in loc_rec_list:
							sl_win.set_focus()
							mouse.click(coords=coord)
							handle_popup()
							sleep(0.5)
							keyboard.SendKeys(str(loc), with_spaces=True)
							sleep(0.5)
						last_row = uia_controls.ListViewWrapper(transaction_grid.children()[-1].element_info)
						item = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('Item')).element_info)
						r_i = item.rectangle()
						sl_win.set_focus()
						c_coords = center(x1=r_i.left, y1=r_i.top, x2=r_i.right, y2=r_i.bottom)
						mouse.click(coords=c_coords)
						handle_popup()
				except Exception as ex:  # Placeholder
					raise ex
				else:
					added_parts = access_grid(transaction_grid, ['Posted', 'Item', 'Location', 'Quantity', 'Billing Code', 'Trans Date'], requirement='Item')
					log.debug(f"Added parts: {added_parts}")
					added_part_numbers = {p.Item for p in added_parts}
					if added_parts:
						save = sl_uia.SaveButton
						sl_win.set_focus()
						save.click()
						handle_popup()
						log.debug("Saved")
						sl_win.set_focus()
						sl_win.PostBatchButton.click()
						sl_win.PostBatchButton.wait('ready', 2, 0.09)
						handle_popup()
						log.debug("Batch posted")
						sl_win.set_focus()
						save.click()
						sleep(1)
				handle_popup()
				sl_win.set_focus()
				for presses in range(2):
					sl_uia.CancelCloseButton.click()
				sl_win.ServiceOrderOperationsButton.wait('visible', 2, 0.09)
				sl_win.set_focus()
				timer.start()
				sl_win.ServiceOrderOperationsButton.click()
				sl_win.SROLinesButton.wait('visible', 2, 0.09)
				t_temp = timer.stop()
				log.debug(f"Time waited for Service Order Lines(part 2): {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
				unit.sro_transactions_time += unit.sro_transactions_timer.stop()
				unit.sro_operations_timer.start()
			log.debug(f"Recieved date: {sl_win.ReceivedDateEdit.texts()[0].strip()}")
			log.debug(f"Floor date: {sl_win.FloorDateEdit.texts()[0].strip()}")
			log.debug(f"Completed date: {sl_win.CompletedDateEdit.texts()[0].strip()}")
			if not sl_win.ReceivedDateEdit.texts()[0].strip():
				sl_win.ReceivedDateEdit.set_text(unit.eff_date.strftime('%m/%d/%Y %I:%M:%S %p'))
			if not sl_win.FloorDateEdit.texts()[0].strip():
				sl_win.FloorDateEdit.set_text(unit.datetime.strftime('%m/%d/%Y %I:%M:%S %p'))
			if not sl_win.CompletedDateEdit.texts()[0].strip() and unit.operation == 'QC':
				sl_win.CompletedDateEdit.set_text(unit.datetime.strftime('%m/%d/%Y %I:%M:%S %p'))
			sl_win.CompletedDateEdit.send_keystrokes('^s')
			sleep(0.5)
			log.debug(f"Recieved date: {sl_win.ReceivedDateEdit.texts()[0].strip()}")
			log.debug(f"Floor date: {sl_win.FloorDateEdit.texts()[0].strip()}")
			log.debug(f"Completed date: {sl_win.CompletedDateEdit.texts()[0].strip()}")
			if not sl_win.CompletedDateEdit.texts()[0].strip() and unit.operation == 'QC':
				sl_win.CompletedDateEdit.set_text(unit.datetime.strftime('%m/%d/%Y %I:%M:%S %p'))
				sl_win.CompletedDateEdit.send_keystrokes('^s')
				sleep(2)
			log.debug(f"Recieved date: {sl_win.ReceivedDateEdit.texts()[0].strip()}")
			log.debug(f"Floor date: {sl_win.FloorDateEdit.texts()[0].strip()}")
			log.debug(f"Completed date: {sl_win.CompletedDateEdit.texts()[0].strip()}")
			common_controls.TabControlWrapper(sl_win.TabControl).select('Reasons')  # Open 'Reasons' Tab
			if unit.operation == 'QC':
				reason_grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info)
				reason_rows = access_grid(reason_grid, ['General Reason', 'Specific Reason', 'General Resolution', 'Specific Resolution'], requirement='General Reason')
				last_row_i = len(reason_rows)-1
				last_row2 = reason_rows[last_row_i]
				top_row_i = reason_grid.children_texts().index('Top Row')
				top_row = reason_grid.children()[top_row_i]
				last_row = uia_controls.ListViewWrapper(reason_grid.children()[last_row_i+top_row_i+1].element_info)

				gen_resn = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('General Reason')).element_info)
				gen_resn_i = gen_resn.rectangle()
				sl_win.set_focus()
				c_coords = center(x1=gen_resn_i.left, y1=gen_resn_i.top, x2=gen_resn_i.right, y2=gen_resn_i.bottom)
				mouse.click(coords=c_coords)
				handle_popup()
				sleep(0.5)

				if last_row2.Specific_Reason is None:
					spec_resn = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('Specific Reason')).element_info)
					spec_resn_i = spec_resn.rectangle()
					sl_win.set_focus()
					c_coords = center(x1=spec_resn_i.left, y1=spec_resn_i.top, x2=spec_resn_i.right, y2=spec_resn_i.bottom)
					mouse.click(coords=c_coords)
					handle_popup()
					sleep(0.5)
					keyboard.SendKeys('20')
				if last_row2.General_Resolution is None:
					gen_reso = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('General Resolution')).element_info)
					gen_reso_i = gen_reso.rectangle()
					sl_win.set_focus()
					c_coords = center(x1=gen_reso_i.left, y1=gen_reso_i.top, x2=gen_reso_i.right, y2=gen_reso_i.bottom)
					mouse.click(coords=c_coords)
					handle_popup()
					sleep(0.5)
					keyboard.SendKeys('10000')
				if last_row2.Specific_Resolution is None:
					spec_reso = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('Specific Resolution')).element_info)
					spec_reso_i = spec_reso.rectangle()
					sl_win.set_focus()
					c_coords = center(x1=spec_reso_i.left, y1=spec_reso_i.top, x2=spec_reso_i.right, y2=spec_reso_i.bottom)
					mouse.click(coords=c_coords)
					handle_popup()
					sleep(0.5)
					keyboard.SendKeys('100')
				resn_notes = sl_win.ReasonNotesEdit
				if resn_notes.texts()[0].strip():
					resn_notes.send_keystrokes(resn_notes.texts()[0].strip() + "{ENTER}[UDI]{ENTER}[PASSED ALL TESTS]")
				else:
					resn_notes.send_keystrokes("[UDI]{ENTER}[PASSED ALL TESTS]")
			reso_notes = sl_win.ResolutionNotesEdit
			if unit.parts:
				reso_string = ", ".join([p.display_name for p in unit.parts])
				if reso_notes.texts()[0].strip():
					reso_notes.send_keystrokes(reso_notes.texts()[0].strip() + "{ENTER}[" + reso_string + "]{ENTER}" + f"[{unit.operator_initials} {unit.datetime.strftime('%m/%d/%Y')}]")
				else:
					reso_notes.send_keystrokes("[" + reso_string + "]{ENTER}" + f"[{unit.operator_initials} {unit.datetime.strftime('%m/%d/%Y')}]")
			status = win32_controls.EditWrapper(sl_win.StatusEdit3.element_info)
			status.send_keystrokes('^s')
			status.wait_for_idle()
			if unit.operation == 'QC':
				status = win32_controls.EditWrapper(sl_win.StatusEdit3.element_info)
				status.set_text('Closed')
				sl_win.set_focus()
				status.send_keystrokes('^s')
				sleep(1)
				handle_popup()
				sleep(1)
				handle_popup()
				sleep(1)
				handle_popup()
				status.wait_for_idle()
			unit.sro_operations_time += unit.sro_operations_timer.stop()
			for presses in range(2):
				sl_uia.CancelCloseButton.click()
			sl_win.UnitEdit.wait('visible', 2, 0.09)
			sleep(0.2)
			sl_win.send_keystrokes('{F4}')  # Clear Filter
			sleep(0.2)
			sl_win.send_keystrokes('{F5}')  # Clear Filter
			sleep(0.2)
		except Exception as ex:  # Placeholder
			raise ex
	# except pag.FailSafeException:
	# 	unit.reset()
	# 	sys.exit(1)
	except Exception:  # Placeholder
		unit.skip()
		for presses in range(3):
			sl_uia.CancelCloseButton.click()
	else:
		unit.complete()

	# 6342086
"""Select m.Item, m.matl_qty from fs_sro_matl m(nolock)
Inner join fs_sro_line l(nolock)
on m.sro_num = l.sro_num and l.sro_line = m.sro_line
left join fs_sro_line l2(nolock)
on l.ser_num = l2.ser_num and l.recorddate < l2.recorddate
where l2.RecordDate is null and l.ser_num = 'OT1154319'"""
