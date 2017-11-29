#! python3 -W ignore
# coding=utf-8
"""Makes sure 'Units' form is open"""
import logging
import warnings
from time import sleep
from typing import List, Sequence

import pyautogui as pag
import pywinauto.timings
from pywinauto import keyboard
from pywinauto.controls import common_controls, uia_controls, win32_controls

from common import *
from common import PuppetMaster, DataGridNEW
from config import *
from constants import REGEX_CREDIT_HOLD, REGEX_NEGATIVE_ITEM, SYTELINE_WINDOW_TITLE, TRANSACTION_STATUS, WHITE
from exceptions import *
from utils.tools import get_background_color
import numpy as np

import sys

# TODO: Initialization

log = logging.getLogger('root')
# TODO: Rework process

starting_forms = {'Units'}

def get_units(*, exclude: List[str] = set()) -> Sequence[Unit]:
	serial_number = mssql.execute("""SELECT TOP 10 [Serial Number] FROM PyComm WHERE Status = %s AND DateTime <= DATEADD(MINUTE, -5, GETDATE()) ORDER BY DateTime ASC""", TRANSACTION_STATUS)
	if serial_number:
		for serial in serial_number:
			if serial[0] not in exclude:
				return Unit.from_serial_number(serial_number[0].Serial_Number, TRANSACTION_STATUS)
	else:
		return None

def count_units(*, distinct: bool=False, similar: bool=False) -> int:
	if distinct:
		if similar:
			return mssql.execute("""SELECT COUNT(DISTINCT [Serial Number]) as [SN_Count] FROM PyComm WHERE [Status] like %s""", '%'+TRANSACTION_STATUS+'%')[0]
		else:
			return mssql.execute("""SELECT COUNT(DISTINCT [Serial Number]) as [SN_Count] FROM PyComm WHERE [Status] = %s""", TRANSACTION_STATUS)[0]
	else:
		if similar:
			return mssql.execute("""SELECT COUNT([Serial Number]) as [SN_Count] FROM PyComm WHERE [Status] like %s""", '%'+TRANSACTION_STATUS+'%')[0]
		else:
			return mssql.execute("""SELECT COUNT([Serial Number]) as [SN_Count] FROM PyComm WHERE [Status] = %s""", TRANSACTION_STATUS)[0]

def dummy(self: PuppetMaster.Puppet, default_wait: float, units: List[Unit]):
	retval = {}
	# UNITS FORM START - - - - - - - - - - - - - - - - - - - - - - - - -
	app = self.app
	app.ensure_form("Units")
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

def main(app: Application, units: Sequence[Unit], *, debug_mode: bool=False):
	# TODO: Adjust wait times, replace with appropriate variables
	# TODO: *hopefully* get rid of/find cleaner and more consistant alternative to "app.get_popup"

	wait_duration = 3  # fast speed
	wait_duration = 60  # slow speed
	wait_duration = 15  # normal speed

	wait_interval = 1  # slow speed
	wait_interval = 0.09  # normal & fast speeds

	pywinauto.timings.Timings.Fast()
	sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
	sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
	sleep(0.2)
	unit = units[0]
	
	if not sl_win.exists():
		for x in units:
			x.reset()
		sys.exit(1)
	app.ensure_form('Units')

	def stage1() -> bool:
		if debug_mode:
			log.debug("Stage 1 started")
			# log.debug("Stage 1: 0%")
		sl_win.UnitEdit.exists()
		sl_win.UnitEdit.wait('visible', wait_duration, wait_interval)
		if get_background_color(sl_win.UnitEdit) != WHITE:
			sl_win.send_keystrokes('{F4}')
			sl_win.send_keystrokes('{F5}')
		sl_win.UnitEdit.set_text(unit.serial_number)
		sleep(0.2)
		sl_win.send_keystrokes('{F4}')
		# if debug_mode:
		# 	log.debug("Stage 1: 25%")
		while get_background_color(sl_win.UnitEdit) == WHITE:
			if sl_win.UnitEdit.texts()[0].strip() != unit.serial_number:
				if not sl_win.UnitEdit.texts()[0].strip():
					raise InvalidSerialNumberError(unit.serial_number)
				else:
					raise SyteLineFilterInPlaceError(unit.serial_number, f"Expected input serial number '{unit.serial_number}', returned '{sl_win.UnitEdit.texts()[0].strip()}'")
		# if debug_mode:
		# 	log.debug("Stage 1: 50%")
		if not sl_win.ServiceOrderLinesButton.is_enabled():
			raise NoOpenSROError(serial_number=unit.serial_number.number, sro=unit.sro, msg="Service Order Lines Button is disabled")
		if not debug_mode:
			for x in units:
				x.start()
		# if debug_mode:
		# 	log.debug("Stage 1: 75%")
		sl_win.set_focus()
		sl_win.ServiceOrderLinesButton.click()
		try:
			sl_win.ServiceOrderOperationsButton.wait('visible', wait_duration, wait_interval)
		except TimeoutError:
			return False
		else:
			if debug_mode:
				# log.debug("Stage 1: 100%")
				log.debug("Stage 1 completed")
			return True

	def stage2() -> bool:
		if debug_mode:
			log.debug("Stage 2 started")
		for i in range(3):
			found_sro = app.find_value_in_collection('Service Order Lines', 'SRO (SroNum)', unit.sro)
			if found_sro:
				break
			sleep(1)
		else:
			raise ValueError()
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
		try:
			sl_win.SROLinesButton.wait('visible', wait_duration, wait_interval)
		except TimeoutError:
			return False
		else:
			if debug_mode:
				log.debug("Stage 2 completed")
			return True

	def stage3() -> bool:
		if debug_mode:
			log.debug("Stage 3 started")
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
		try:
			sl_win.SROTransactionsButton.wait('enabled', wait_duration, wait_interval)
		except TimeoutError:
			return False
		else:
			if debug_mode:
				log.debug("Stage 3 completed")
			return True

	def stage4() -> bool:
		if debug_mode:
			log.debug("Stage 4 started")
		if any(len(x.parts) > 0 for x in units) or debug_mode:
			sl_win.set_focus()
			sl_win.SROTransactionsButton.click()

			sleep(10)  # THINK: Consider the necessity of
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
				if not row[1]:
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
					pag.press('enter')
					pag.press('esc', 10)

				# for part, row_num in part_list:
				# 	transaction_grid.set_cell('Location', row_num, part.location)
				# 	if part.quantity > 1:
				# 		transaction_grid.set_cell('Quantity', row_num, part.quantity)
				# 	transaction_grid.set_cell('Billing Code', row_num, bc)

				transaction_grid.select_cell(transaction_grid.get_cell('Location', 1))
				if debug_mode:
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
						sl_win.PostBatchButton.wait('ready', wait_duration, wait_interval)
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
			sl_win.ServiceOrderOperationsButton.wait('visible', wait_duration, wait_interval)
			sl_win.set_focus()
			sl_win.ServiceOrderOperationsButton.click()
			try:
				sl_win.SROLinesButton.wait('visible', wait_duration, wait_interval)
			except TimeoutError:
				return False
			else:
				if debug_mode:
					log.debug("Stage 4 completed")
				return True

	def stage5() -> bool:
		if debug_mode:
			log.debug("Stage 5 started")
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
			reason_notes_text_lines = reason_notes.texts()[1:]
			reason_notes_text = [line.strip() for line in reason_notes_text_lines if line.strip()]
			if '[UDI]' not in reason_notes_text:
				reason_notes_text.append('[UDI]')
			if '[PASSED ALL TESTS]' not in reason_notes_text:
				reason_notes_text.append('[PASSED ALL TESTS]')
			reason_notes.set_text('\r\n'.join(line.strip() for line in reason_notes_text if line.strip()))
			reason_notes.send_keystrokes('^s')

		if any(len(x.parts) > 0 for x in units):
			resolution_notes = sl_win.ResolutionNotesEdit
			resolution_notes_text_lines = resolution_notes.texts()[1:]
			resolution_notes_text = [line.strip() for line in resolution_notes_text_lines if line.strip()]
			for unit in units:
				reason_notes_text_pairs = [(string1, string2) for string1, string2 in zip(reason_notes_text[:-1], reason_notes_text[1:])]
				part_text = f"[{', '.join([p.display_name for p in unit.parts])}]"
				operator_text = f"[{unit.operator} {unit.datetime.strftime('%m/%d/%Y')}]"
				if (part_text, operator_text) not in reason_notes_text_pairs:
					resolution_notes_text.append(part_text)
					resolution_notes_text.append(operator_text)
			resolution_notes.set_text('\r\n'.join(line.strip() for line in resolution_notes_text if line.strip()))
			resolution_notes.send_keystrokes('^s')

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
					pag.press('esc')
		sro_operations_time = timer.stop() / len(units)
		for x in units:
			x.sro_operations_time += sro_operations_time
		sl_uia.CancelCloseButton.click()
		if unit.passed_QC:  # FIXME: Refine recursive sro closing
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
		if debug_mode:
			log.debug("Stage 5 completed")
		return True

	try:
		done = False
		if stage1():
			if stage2():
				if stage3():
					if stage4():
						if stage5():
							done = True
		if not done:
			raise ValueError()
	except Exception as ex:
		log.exception("SOMETHING HAPPENED!!!")
		for x in units:
			if debug_mode:
				x.reset()
			else:
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

if __name__ == '__main__':
	sys.argv  # TODO: Handle arguments, such as debug mode, etc
	main()
