# coding=utf-8
import logging
import sys
from time import sleep
from typing import List, Sequence, Callable

import numpy as np
import pyautogui as pag
import pywinauto.timings
from _globals import *
from core import *
from exceptions import *
from pywinauto.controls import common_controls, uia_controls, win32_controls
from utils.tools import get_background_color
from constants import SYTELINE_WINDOW_TITLE, WHITE, REGEX_RESOLUTION


log = logging.getLogger('root')
u_log = logging.getLogger('UnitLogger')

starting_forms = {'Units'}
REASON_STATUS = 'Reason'
REASON_COMPLETED = 'C3'


class ReasonUnit(Unit, completion_string=REASON_COMPLETED, status_string=REASON_STATUS):
	def __init__(self, ID: int):
		Unit.__init__(self, ID)

		try:

			try:
				self.sro, self.sro_line = self.get_sro(self.serial_number)
			except TypeError:
				raise NoSROError(serial_number=self.serial_number.number)
			else:
				log.info(f"Attribute sro='{self.sro}'")
				log.info(f"Attribute sro_line={self.sro_line}")
				u_log.debug(f"{str('SN=' + str(self.serial_number.number)).ljust(13)}|INFO|SRO={self.sro}")
				u_log.debug(f"{str('SN=' + str(self.serial_number.number)).ljust(13)}|INFO|SRO Line={self.sro_line}")

			if not self.sro_open_status['Lines']:
				raise NoOpenSROError(serial_number=self.serial_number.number, sro=self.sro)

			m = REGEX_RESOLUTION.fullmatch(str(self.notes))
			if m:
				self.general_reason = 1000
				self.specific_reason = 20
				self.general_resolution, self.specific_resolution = [int(x) for x in m.groups()]
				if self.general_resolution == 10000 and self.specific_resolution == 100:
					self.general_resolution_name = 'Pass'
				else:
					res = mssql.execute("""SELECT TOP 1 Failure FROM FailuresRepairs WHERE ReasonCodes = %s""", str(self.notes))
					if res:
						self.general_resolution_name = res[0].Failure
					else:
						raise InvalidReasonCodeError(reason_code=str(self.notes), spec_id=str(self.ID))
			elif not self.notes:  # Because HomeGuard -_-
				self.general_resolution = None
				self.specific_resolution = None
				self.general_resolution_name = None
			else:
				raise InvalidReasonCodeError(reason_code=str(self.notes), spec_id=str(self.ID))

		except BI_EntryError as ex:
			self.skip(ex)
			raise ex
		except Exception as ex2:
			raise ex2

def get_units(*, exclude: List[str] = set()) -> Sequence[Unit]:
	serial_number = mssql.execute("""SELECT TOP 10 [Serial Number] FROM PyComm WHERE Status = %s AND DateTime <= DATEADD(MINUTE, -5, GETDATE()) ORDER BY DateTime ASC""", REASON_STATUS)
	if serial_number:
		for serial in serial_number:
			if serial[0] not in exclude:
				return Unit.from_serial_number(serial_number[0].Serial_Number, REASON_STATUS)
	else:
		return None

def count_units(*, distinct: bool=False, similar: bool=False) -> int:
	if distinct:
		if similar:
			return mssql.execute("""SELECT COUNT(DISTINCT [Serial Number]) as [SN_Count] FROM PyComm WHERE [Status] like %s""", '%'+REASON_STATUS+'%')[0]
		else:
			return mssql.execute("""SELECT COUNT(DISTINCT [Serial Number]) as [SN_Count] FROM PyComm WHERE [Status] = %s""", REASON_STATUS)[0]
	else:
		if similar:
			return mssql.execute("""SELECT COUNT([Serial Number]) as [SN_Count] FROM PyComm WHERE [Status] like %s""", '%'+REASON_STATUS+'%')[0]
		else:
			return mssql.execute("""SELECT COUNT([Serial Number]) as [SN_Count] FROM PyComm WHERE [Status] = %s""", REASON_STATUS)[0]

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

def reason(app: Application, units, *, debug_mode: bool=False):
	# TODO: Adjust wait times, replace with appropriate variables
	# TODO: *hopefully* get rid of/find cleaner and more consistant alternative to "app.get_popup"

	log.debug(f"{app}, {units}")

	wait_duration = 3  # fast speed
	wait_duration = 60  # slow speed
	wait_duration = 15  # normal speed

	wait_interval = 1  # slow speed
	wait_interval = 0.09  # normal & fast speeds

	pywinauto.timings.Timings.Fast()
	sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
	sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
	sleep(0.2)

	if not sl_win.exists():
		for x in units:
			x.reset()
		sys.exit(1)

	try:
		app.ensure_form('Units')
	except pywinauto.findbestmatch.MatchError:
		for x in units:
			x.reset()
		sys.exit(1)

	log.debug("Preparing stages")

	def stage1(unit: Unit) -> bool:
		log.debug("Stage 1 started")
		# log.debug("Stage 1: 0%")
		sl_win.UnitEdit.exists()
		sl_win.UnitEdit.wait('visible', wait_duration, wait_interval)
		for i in range(4):
			# if get_background_color(sl_win.UnitEdit) != WHITE:  # FIXME
			# 	sl_win.send_keystrokes('{F4}')
			# 	sl_win.send_keystrokes('{F5}')
			if i > 0:
				sleep(1.5)
				sl_win.send_keystrokes('{F4}')
				sl_win.send_keystrokes('{F5}')
			sl_win.UnitEdit.set_text(unit.serial_number)
			sleep(0.2)
			sl_win.UnitEdit.send_keystrokes('{F4}')
			sleep(0.4)
			# if debug_mode:
			# 	log.debug("Stage 1: 25%")
			if sl_win.UnitEdit.texts()[0].strip() != unit.serial_number:
				if not sl_win.UnitEdit.texts()[0].strip():
					ex = InvalidSerialNumberError(unit.serial_number)
				else:
					ex = SyteLineFilterInPlaceError(unit.serial_number, f"Expected input serial number '{unit.serial_number}', returned '{sl_win.UnitEdit.texts()[0].strip()}'")
			else:
				break
		else:
			raise ex
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
			# log.debug("Stage 1: 100%")
			log.debug("Stage 1 completed")
			return True

	def stage2(unit: Unit) -> bool:
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
			log.debug("Stage 2 completed")
			return True

	def stage3(unit: Unit) -> bool:
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
			log.debug("Stage 3 completed")
			return True

	def stage4(unit: Unit) -> bool:
		log.debug("Stage 4 started")
		timer = Timer.start()

		if not unit.sro_open_status['Operations']:
			log.debug(f"Completed date: {sl_win.CompletedDateEdit.texts()[0].strip()}")
			if not sl_win.CompletedDateEdit.texts()[0].strip():
				sl_win.CompletedDateEdit.set_text(unit.newest_datetime.strftime('%m/%d/%Y %I:%M:%S %p'))
				if not debug_mode:
					sl_win.CompletedDateEdit.send_keystrokes('^s')
				sleep(0.5)
			log.debug(f"Completed date: {sl_win.CompletedDateEdit.texts()[0].strip()}")

		common_controls.TabControlWrapper(sl_win.TabControl).select('Reasons')  # Open 'Reasons' Tab
		reason_grid = DataGridNEW.default(app, ['General Reason', 'Specific Reason', 'General Resolution', 'Specific Resolution'])
		reason_grid.populate()
		gen_rsn = 1000
		for i, row in enumerate(reason_grid.grid):
			if reason_grid.grid[i, 0]:
				gen_rsn = reason_grid.grid[i, 0]
			if np.count_nonzero(list(reason_grid.grid[i, :1]) + list(reason_grid.grid[i, 2:])) < 3:
				break
		for unit in units:
			resolution_pairs = [(gen, spec) for gen, spec in zip(reason_grid.grid[..., 2], reason_grid.grid[..., 3])]
			if (unit.general_resolution, unit.specific_resolution) in resolution_pairs:
				continue
			try:
				i += 1
				row = reason_grid.grid[i]
			except IndexError:
				row = reason_grid.grid[i - 1]
			count = np.count_nonzero(row)
			if reason_grid.scrollbar_v.exists():
				page_down = reason_grid.scrollbar_v.PagedownButton
				for move in range((reason_grid.row_count // 6) + 1):
					page_down.invoke()
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
			if reason_grid.scrollbar_v.exists():
				page_up = reason_grid.scrollbar_v.PageupButton
				for move in range((reason_grid.row_count // 6) + 2):
					page_up.invoke()

			dlg = app.get_popup(0.5)  # TODO: Address specific resolution incompatibilities
			while dlg:
				log.debug(f"Reason Grid dialog text: '{dlg.Text}'")
				if ("not a valid" in dlg.Text) and ("change the value now?" in dlg.Text):
					pag.press('n')
					raise InvalidReasonCodeError(unit.notes, unit.ID)
				dlg = app.get_popup()

		reason_grid.select_cell(reason_grid.get_cell('General Reason', 1))
		sleep(0.5)
		pag.hotkey('ctrl', 's')
		sleep(1)

		reason_notes = sl_win.ReasonNotesEdit
		reason_notes_text_lines = reason_notes.texts()[1:]
		reason_notes_text = [line.strip() for line in reason_notes_text_lines if line.strip()]
		for unit in units:
			if unit.general_resolution_name == 'Pass':
				res_text1 = '[POWER UP OK]'
				res_text2 = '[ACCEPTED]'
				if res_text1 not in reason_notes_text:
					reason_notes_text.append(res_text1)
				if res_text2 not in reason_notes_text:
					reason_notes_text.append(res_text2)
			else:
				resolution_name = f'[{unit.general_resolution_name}]'
				if resolution_name not in reason_notes_text:
					reason_notes_text.append(resolution_name)
		reason_notes.set_text('\r\n'.join(line.strip() for line in reason_notes_text if line.strip()))
		reason_notes.send_keystrokes('^s')

		resolution_notes = sl_win.ResolutionNotesEdit
		resolution_notes_text_lines = resolution_notes.texts()[1:]
		resolution_notes_text = [line.strip() for line in resolution_notes_text_lines if line.strip()]
		for unit in units:
			operator_text = f"[{unit.operator} {unit.datetime.strftime('%m/%d/%Y')}]"
			if operator_text not in resolution_notes_text:
				resolution_notes_text.append(operator_text)
		resolution_notes.set_text('\r\n'.join(line.strip() for line in resolution_notes_text if line.strip()))
		resolution_notes.send_keystrokes('^s')

		if not debug_mode:
			pag.hotkey('ctrl', 's')
			status = win32_controls.EditWrapper(sl_win.StatusEdit3.element_info)
			status.send_keystrokes('^s')
			status.wait_for_idle()
			if not unit.sro_open_status['Operations']:
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
		sl_uia.CancelCloseButton.click()
		sl_win.UnitEdit.wait('visible', 2, 0.09)
		sleep(0.2)
		sl_win.send_keystrokes('{F4}')  # Clear Filter
		sleep(0.2)
		sl_win.send_keystrokes('{F5}')  # Clear Filter
		sleep(0.2)
		try:
			sl_win.UnitEdit.wait('visible', wait_duration, wait_interval)
		except TimeoutError:
			return False
		else:
			log.debug("Stage 4 completed")
			return True

	log.debug("Stage preparation complete")

	try:
		local_functions = {k: v for k, v in locals().items() if callable(v) and k != 'unit_function' and v.__class__.__name__ == 'function'}
		stages = sorted(local_functions.values(), key=lambda x: [k for k, v in local_functions.items() if v == x][0])
		log.debug(stages)
		if not all([func(units[0]) for func in stages]):
			raise ValueError()
	except Exception as ex:
		log.exception("SOMETHING HAPPENED!!!")
		for x in units:
			if debug_mode:
				x.reset()
			else:
				x.skip(ex, batch_amt=len(units))
		if sl_uia.exists(2, 0.09):
			dlg = app.get_popup()
			while dlg:
				log.debug(f"Operations Cancel Close dialog text: '{dlg.Text}'")
				dlg[0].close()
				dlg = app.get_popup()
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


