"""Makes sure 'Miscellaneous Issue' and 'Units' forms are open"""
# TODO: Initialization

import logging
import sqlite3
import sys
from operator import attrgetter
from time import sleep
from typing import Callable, List
import itertools

import numpy as np
import pyautogui as pag
import pywinauto.timings
from core import *
from _globals import *
from config import *
from common import *
from utils.tools.control_tools import *
from exceptions import *
from pywinauto.controls import win32_controls, common_controls

from constants import SYTELINE_WINDOW_TITLE, REGEX_RESOLUTION

log = logging.getLogger('root')
u_log = logging.getLogger('UnitLogger')
reason_dict = {'Monitoring': 22, 'RTS': 24, 'Direct': 24}
SCRAP_STATUS = 'Scrap'
SCRAP_COMPLETED = 'C2'

# class ScrapUnit(Unit):# TODO: Process-specific Unit subclasses
class ScrapUnit(Unit, completion_string=SCRAP_COMPLETED, status_string=SCRAP_STATUS):
	def __init__(self, ID: int):
		Unit.__init__(self, ID)

		try:
			self.sro, self.sro_line = self.get_sro(self.serial_number)
		except TypeError:
			self.sro = None
			self.sro_line = None
		finally:
			log.info(f"Attribute sro='{self.sro}'")
			log.info(f"Attribute sro_line={self.sro_line}")
			u_log.debug(f"{str('SN=' + str(self.serial_number.number)).ljust(13)}|INFO|SRO={self.sro}")
			u_log.debug(f"{str('SN=' + str(self.serial_number.number)).ljust(13)}|INFO|SRO Line={self.sro_line}")

		m = REGEX_RESOLUTION.fullmatch(str(self.notes))
		if m:
			res = mssql.execute("""SELECT TOP 1 Failure FROM FailuresRepairs WHERE ReasonCodes = %s""", str(self.notes))
			if res:
				self.general_resolution_name = res[0].Failure
				self.specific_resolution_name = self.status.upper()
			else:
				raise InvalidReasonCodeError(reason_code=str(self.notes), spec_id=str(self.ID))
		else:
			raise InvalidReasonCodeError(reason_code=str(self.notes), spec_id=str(self.ID))

	@classmethod
	def get_units(cls, total_qty: int, qty: int):  # TODO: Refine scrap sorting process
		assert total_qty >= qty
		data = mssql.execute("""SELECT TOP %d ID FROM PyComm WHERE Status = 'Scrap' ORDER BY DateTime ASC""", total_qty)

		conn = sqlite3.connect(':memory:')
		c = conn.cursor()
		c.execute("CREATE TABLE scrap (ID INTEGER, serial_number TEXT, build TEXT, location TEXT, datetime TEXT, operator TEXT)")
		conn.commit()

		all_units = [cls(d) for d in data]
		for unit in all_units:
			c.execute(f"""INSERT INTO scrap(ID, serial_number, build, location, datetime, operator) VALUES 
			({unit.ID}, '{str(unit.serial_number)}', '{unit.build}', '{unit.location}', '{unit.datetime.strftime('%m/%d/%Y %H:%M:%S')}', '{unit.operator.username}')""")  # FIXME: SQL command w/ parameters
			conn.commit()
		results = c.execute(f"SELECT build,location,COUNT(location) AS count FROM scrap GROUP BY build, location ORDER BY count DESC").fetchall()  # FIXME: SQL command w/ parameters

		retval = []
		for i in range(0, total_qty, qty):
			sleep(1)
			id_list = []
			serial_set = set()
			for build, location, count in results:
				id_results = c.execute(f"SELECT ID, serial_number FROM scrap WHERE build = '{build}' AND location = '{location}' ORDER BY datetime ASC").fetchall()  # FIXME: SQL command w/ parameters
				for x in id_results:
					id_list.append(x[0])
					serial_set.add(x[1])
					if len(serial_set) >= 10:
						break
				if len(serial_set) >= 10:
					break
			sub_list = sorted([unit for unit in all_units if unit.ID in id_list], key=attrgetter('serial_number'))	# Sort Units by build and location, and order by serial number ascending
			log.debug(sub_list)
			retval.append(sub_list)
		# for u in retval:
		# 	print(u.ID, u.serial_number)
		# print(serial_set, len(serial_set))
		return retval
# TODO: Rework process

def scrap(app):
	raise NotImplementedError
	sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
	sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)

	wait_duration = 3  # fast speed
	wait_duration = 60  # slow speed
	wait_duration = 15  # normal speed

	wait_interval = 1  # slow speed
	wait_interval = 0.09  # normal & fast speeds

	pywinauto.timings.Timings.Fast()
	sleep(0.2)


	# counter = itertools.count()
	# for sn in unit_serials:
	# 	count = next(counter)
	# 	timer = Timer.start()
	# 	log.debug(f'{count} {str(sn)}')
	# 	app.find_value_in_collection(collection='SLSerials', property_='S/N (SerNum)', value=str(sn))
	# 	cell = sl_win.get_focus()
	# 	cell.send_keystrokes('{SPACE}')
	# 	units_group = [u for u in units if u.serial_number.number == sn]
	# 	for u in units_group:
	# 		global_units.append(u)
	# 	units_group = [u for u in units if u.serial_number.number == sn][0]
	# 	unit.misc_issue_time += (timer.stop() / len(global_units))
	# 	sleep(0.2)
	#
	# def stage1(build, location, units):
	# 	log.debug("Stage 1 started")
	# 	sl_win.ItemEdit.set_text(build)
	# 	sleep(0.2)
	# 	sl_win.ItemEdit.send_keystrokes('{TAB}')
	# 	reason_code = 22  # 24 if direct'
	#
	# 	app.ensure_form('Miscellaneous Issue')
	# 	if location.lower() == 'out of inventory':
	# 		return units
	#
	# 	docnum = f"SCRAP {units[0].operator}"
	#
	# 	qty = len({u.serial_number for u in units})
	#
	# 	sl_win.LocationEdit.wait('ready', 2, 0.09)
	# 	sl_win.LocationEdit.set_text(location)
	# 	sl_win.LocationEdit.send_keystrokes('{TAB}')
	# 	sl_win.LocationEdit.wait('ready', 2, 0.09)
	#
	# 	sl_win.QuantityEdit.wait('ready', 2, 0.09)
	# 	sl_win.QuantityEdit.set_text(str(qty) + '.000')
	# 	sl_win.QuantityEdit.send_keystrokes('{TAB}')
	#
	# 	sl_win.ReasonEdit.wait('ready', 2, 0.09)
	# 	sl_win.ReasonEdit.set_text(str(reason_code))
	# 	sl_win.ReasonEdit.send_keystrokes('{TAB}')
	#
	# 	sl_win.DocumentNumEdit.wait('ready', 2, 0.09)
	# 	sl_win.DocumentNumEdit.set_text(docnum)
	# 	sl_win.DocumentNumEdit.send_keystrokes('{TAB}')
	#
	# 	sl_win.SerialNumbersTab.wait('ready', 2, 0.09)
	# 	sl_win.SerialNumbersTab.select('Serial Numbers')
	#
	# 	sl_win.GenerateQtyEdit.wait('ready', 2, 0.09)
	# 	sl_win.GenerateQtyEdit.set_text(str(max_qty))
	# 	sl_win.GenerateQtyEdit.send_keystrokes('{TAB}')
	#
	# 	sl_win.GenerateButton.wait('ready', 2, 0.09)
	# 	sl_win.GenerateButton.click()
	#
	# 	sl_win.SelectRangeButton.wait('ready', 2, 0.09)
	# 	counter = 0
	# 	for unit_sn in unit_serials:
	# 		counter += 1
	# 		timer = Timer.start()
	# 		log.debug(f'{counter} {str(unit_sn)}')
	# 		app.find_value_in_collection(collection='SLSerials', property_='S/N (SerNum)', value=str(unit_sn))
	# 		cell = sl_win.get_focus()
	# 		cell.send_keystrokes('{SPACE}')
	# 		unit = [u for u in units if u.serial_number.number == unit_sn]
	# 		for u in unit:
	# 			global_units.append(u)
	# 		unit = [u for u in units if u.serial_number.number == unit_sn][0]
	# 		unit.misc_issue_time += (timer.stop() / len(global_units))
	# 		sleep(0.2)
	# 	sl_win.SelectedQtyEdit.wait('ready', 2, 0.09)
	# 	text1, text2, text3 = [x.strip() for x in (sl_win.SelectedQtyEdit.texts()[0], sl_win.TargetQtyEdit.texts()[0], sl_win.RangeQtyEdit.texts()[0])]
	# 	if text1 == text2:
	# 		log.debug(f"{text1} == {text2}")
	# 	else:
	# 		log.error(f"{text1} != {text2}")
	# 		raise ValueError()
	# 	if text3 == '0':
	# 		log.debug(f"{text3} == 0")
	# 	else:
	# 		log.error(f"{text3} != 0")
	# 		raise ValueError()
	# 	sl_win.ProcessButton.click()
	# 	sleep(30)  ###########################
	# 	dlg = app.get_popup(10)
	# 	if dlg:
	# 		dlg[0].OKButton.click()
	# 		dlg[0].wait_not('exists', 2, 0.09)
	# 	sl_win.LocationEdit.wait('visible', 2, 0.09)



	for unit_set in ScrapUnit.get_units(100, 10):
		completed_units = []
		global_units = []

		# def stage1()

		try:
			log.debug(f"Starting Scrap script with units: {', '.join(str(unit.serial_number) for unit in units)}")
			sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
			sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
			if not sl_win.exists():
				for unit in unit_set:
					unit.reset()
				sys.exit(1)
			log.debug([x.texts()[0] for x in sl_uia.WindowMenu.items()])

			try:
				app.ensure_form('Units')
				app.ensure_form('Miscellaneous Issue')
			except pywinauto.findbestmatch.MatchError:
				for unit in unit_set:
					unit.reset()
				sys.exit(1)

			build_dict = {}
			for unit in unit_set:
				if unit.build not in build_dict:
					build_dict[unit.build] = {unit.location: []}
				elif unit.location not in build_dict[unit.build]:
					build_dict[unit.build][unit.location] = []
				build_dict[unit.build][unit.location].append(unit)
				unit.start()

			max_qty = 9999999
			for build, location_dict in build_dict.items():
				app.ensure_form('Miscellaneous Issue')
				sl_win.ItemEdit.set_text(build)
				sleep(0.2)
				sl_win.ItemEdit.send_keystrokes('{TAB}')
				reason_code = 22  # 24 if direct'
				for location, units in location_dict.items():
					app.ensure_form('Miscellaneous Issue')
					if location.lower() == 'out of inventory':
						for unit in units:
							global_units.append(unit)
						continue
					docnum = f"SCRAP {units[0].operator}"
					qty = len({u.serial_number for u in units})
					sl_win.LocationEdit.wait('ready', 2, 0.09)
					sl_win.LocationEdit.set_text(location)
					sl_win.LocationEdit.send_keystrokes('{TAB}')
					sl_win.LocationEdit.wait('ready', 2, 0.09)
					sl_win.QuantityEdit.wait('ready', 2, 0.09)
					sl_win.QuantityEdit.set_text(str(qty) + '.000')
					sl_win.QuantityEdit.send_keystrokes('{TAB}')
					sl_win.ReasonEdit.wait('ready', 2, 0.09)
					sl_win.ReasonEdit.set_text(str(reason_code))
					sl_win.ReasonEdit.send_keystrokes('{TAB}')
					sl_win.DocumentNumEdit.wait('ready', 2, 0.09)
					sl_win.DocumentNumEdit.set_text(docnum)
					sl_win.DocumentNumEdit.send_keystrokes('{TAB}')
					sl_win.SerialNumbersTab.wait('ready', 2, 0.09)
					sl_win.SerialNumbersTab.select('Serial Numbers')
					sl_win.GenerateQtyEdit.wait('ready', 2, 0.09)
					sl_win.GenerateQtyEdit.set_text(str(max_qty))
					sl_win.GenerateQtyEdit.send_keystrokes('{TAB}')
					sl_win.GenerateButton.wait('ready', 2, 0.09)
					sl_win.GenerateButton.click()
					sl_win.SelectRangeButton.wait('ready', 2, 0.09)
					counter = 0
					for unit_serial in sorted({u.serial_number.number for u in units}):
						counter += 1
						timer = Timer.start()
						log.debug(f'{counter} {str(unit_serial)}')
						app.find_value_in_collection(collection='SLSerials', property_='S/N (SerNum)', value=str(unit_serial))
						cell = sl_win.get_focus()
						cell.send_keystrokes('{SPACE}')
						unit = [u for u in units if u.serial_number.number == unit_serial]
						for u in unit:
							global_units.append(u)
						unit = [u for u in units if u.serial_number.number == unit_serial][0]
						unit.misc_issue_time += (timer.stop() / len(global_units))
						sleep(0.2)
					sl_win.SelectedQtyEdit.wait('ready', 2, 0.09)
					text1, text2, text3 = [x.strip() for x in (sl_win.SelectedQtyEdit.texts()[0], sl_win.TargetQtyEdit.texts()[0], sl_win.RangeQtyEdit.texts()[0])]
					if text1 == text2:
						log.debug(f"{text1} == {text2}")
					else:
						log.error(f"{text1} != {text2}")
						raise ValueError()
					if text3 == '0':
						log.debug(f"{text3} == 0")
					else:
						log.error(f"{text3} != 0")
						raise ValueError()
					sl_win.ProcessButton.click()
					sleep(30)  ###########################
					dlg = app.get_popup(10)
					if dlg:
						dlg[0].OKButton.click()
						dlg[0].wait_not('exists', 2, 0.09)
					sl_win.LocationEdit.wait('visible', 2, 0.09)
			# reset_units = set(units) - set(global_units)
			# for unit in reset_units:
			# 	unit.reset()
			app.change_form('Units')
			sl_win.UnitEdit.wait('ready', 2, 0.09)
			for unit in global_units:
				app.ensure_form('Units')
				sl_win.UnitEdit.set_text(str(unit.serial_number))
				sl_win.UnitEdit.send_keystrokes('{F4}')  # Filter in Place
				while (sl_win.UnitEdit.texts()[0].strip() != str(unit.serial_number)) and sl_win.UnitEdit.texts()[
					0].strip():  # While actual serial number != attempted serial number
					state = sl_uia.UnitEdit.legacy_properties()['State']
					bin_state = bin(state)
					log.debug(f"Units Textbox State: {state}")
					if int(bin_state[-7], base=2):  # If the seventh bit == 1
						break
					sleep(0.4)
				if sl_win.UnitEdit.texts()[0].strip() != str(unit.serial_number):
					if not sl_win.UnitEdit.texts()[0].strip():
						raise InvalidSerialNumberError(f"Expected input serial number '{str(unit.serial_number)}', returned None")
					else:
						raise SyteLineFilterInPlaceError(f"Expected input serial number '{str(unit.serial_number)}', returned '{sl_win.UnitEdit.texts()[0].strip()}'")
				sl_win.set_focus()
				customer_number = 302
				ship_to = int(unit.is_cellular) + 1  # if unit.phone: 2, else: 1
				scrap_code = 'SCRAPPED' + ('1' * int(unit.is_cellular))  # if unit.phone: 'SCRAPPED1', else: 'SCRAPPED'
				sl_win.CustNumEdit.wait('ready', 2, 0.09)
				cust_num = sl_win.CustNumEdit.texts()[0].strip()
				if cust_num != str(customer_number):
					sl_win.CustNumEdit.set_text(str(customer_number))
					sl_win.CustNumEdit.send_keystrokes('{TAB}')
					sl_win.ShipToEdit.wait('ready', 2, 0.09)
				st = sl_win.ShipToEdit.texts()[0].strip()
				if st != str(ship_to):
					sl_win.ShipToEdit.set_text(str(ship_to))
					sl_win.ShipToEdit.send_keystrokes('{TAB}')
					sl_win.ShipToEdit.wait('ready', 2, 0.09)
				statcode = sl_win.UnitStatusCode.texts()[0].strip()
				if statcode != str(scrap_code):
					r_i = sl_win.ChangeStatusButton.rectangle()
					c_coords = center(r_i)
					pag.click(*c_coords)
					sleep(0.2)
					dlg = app.get_popup()
					if dlg:
						dlg[0].YesButton.click()
						dlg[0].wait_not('exists', 2, 0.09)
					# pag.hotkey('alt', 'y')  # 'Yes' button, (ALT + Y)
					sl_win.UnitStatusCodeEdit.wait('ready', 2, 0.09)
					sl_win.UnitStatusCodeEdit.set_text(str(scrap_code))
					sl_win.UnitStatusCodeEdit.send_keystrokes('{TAB}')
					sl_win.UnitStatusCodeEdit.wait('ready', 2, 0.09)
				pag.hotkey('ctrl', 's')
				sl_win.UnitStatusCodeEdit.wait_for_idle()

				if unit.sro_open_status['Lines']:
					sl_win.set_focus()
					sl_win.ServiceOrderLinesButton.click()
					sl_win.ServiceOrderOperationsButton.wait('visible', 30, 0.09)
					sl_win.set_focus()
					sl_win.ServiceOrderOperationsButton.click()
					sl_win.SROLinesButton.wait('visible', 30, 0.09)
					timer = Timer.start()
					if not unit.sro_open_status['Operations']:
						status = win32_controls.EditWrapper(sl_win.StatusEdit3.element_info)
						status.set_text('Open')
						status.click_input()
						pag.press('tab')
						pag.press('esc')
						save = sl_uia.SaveButton
						save.click()
					sl_win.SROTransactionsButton.wait('enabled', 30, 0.09)

					common_controls.TabControlWrapper(sl_win.TabControl).select('Reasons')  # Open 'Reasons' Tab

					reason_grid = DataGridNEW.default(app, ['General Reason', 'Specific Reason', 'General Resolution', 'Specific Resolution'])
					reason_grid.populate()
					gen_rsn = 1000
					for i, row in enumerate(reason_grid.grid):
						if reason_grid.grid[i, 0]:
							gen_rsn = reason_grid.grid[i, 0]
						if np.count_nonzero(list(reason_grid.grid[i, :1]) + list(reason_grid.grid[i, 2:])) < 3:
							break
					resolution_pairs = [(gen, spec) for gen, spec in zip(reason_grid.grid[..., 2], reason_grid.grid[..., 3])]
					if (unit.general_resolution, unit.specific_resolution) in resolution_pairs:
						continue
					try:
						i += 1
					except IndexError:
						pass
					row = reason_grid.grid[i]
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
					reason_grid.select_cell(reason_grid.get_cell('General Reason', 1))
					sleep(0.5)
					pag.hotkey('ctrl', 's')
					sleep(1)

					reason_notes = sl_win.ReasonNotesEdit
					reason_notes_text_lines = reason_notes.texts()[1:]
					reason_notes_text = [line.strip() for line in reason_notes_text_lines if line.strip()]
					resolution_name = f'[{unit.specific_resolution_name} {unit.general_resolution_name.upper()}]'
					if resolution_name not in reason_notes_text:
						reason_notes_text.append(resolution_name)
					reason_notes.set_text('\r\n'.join(line.strip() for line in reason_notes_text if line.strip()))
					reason_notes.send_keystrokes('^s')

					resolution_notes = sl_win.ResolutionNotesEdit
					resolution_notes_text_lines = resolution_notes.texts()[1:]
					resolution_notes_text = [line.strip() for line in resolution_notes_text_lines if line.strip()]
					operator_text = f"[{unit.operator} {unit.datetime.strftime('%m/%d/%Y')}]"
					if operator_text not in resolution_notes_text:
						resolution_notes_text.append(operator_text)
					resolution_notes.set_text('\r\n'.join(line.strip() for line in resolution_notes_text if line.strip()))
					resolution_notes.send_keystrokes('^s')

					status = win32_controls.EditWrapper(sl_win.StatusEdit3.element_info)
					status.send_keystrokes('^s')
					status.wait_for_idle()
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

					unit.sro_operations_time += timer.stop() / len(global_units)
					sl_uia.CancelCloseButton.click()
					sl_uia.CancelCloseButton.click()
					sleep(0.5)
					sl_win.ServiceOrderLinesButton.wait('visible', 30, 0.09)
				sl_win.send_keystrokes('%s')  # Actions Menu, (ALT + S)
				sleep(0.2)
				sl_win.send_keystrokes('o')  # Notes For Current, (O)
				sleep(1)
				app.find_value_in_collection(collection='Object Notes', property_='Subject (DerDesc)', value='NOTES', case_sensitive=True)
				sleep(1)
				dlg = app.get_popup(2)
				if dlg:
					dlg[0].send_keystrokes('{ENTER}')
					sleep(0.5)
					sl_win.send_keystrokes('{F8 20}')
					sleep(0.5)
					sl_win.SubjectEdit.set_text('NOTES')
				sl_uia.window(auto_id='DerContentEdit').set_focus()
				note = sl_win.get_focus()

				note_text_lines = note.texts()[1:]
				note_text = [line.strip() for line in note_text_lines if line.strip()]

				note_text.append(f"[{unit.specific_resolution_name} {unit.general_resolution_name}]")
				note_text.append(f"[{unit.operator} {unit.datetime.strftime('%m/%d/%Y')}]")

				note.set_text('\r\n'.join(line.strip() for line in note_text if line.strip()))
				note.send_keystrokes('^s')
				sl_win.send_keystrokes('^s')
				sl_uia.CancelCloseButton.click()
				sl_win.send_keystrokes('{F4}')
				sl_win.send_keystrokes('{F5}')
				completed_units.append(unit)

		except Exception as ex:
			log.exception("SOMETHING HAPPENED!!!")
			for x in global_units:
				if x in completed_units:
					continue
				x.skip(batch_amt=len(global_units))
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
		finally:
			log.info(f"Unit: {str(units[0].serial_number)} completed")
			for x in completed_units:
				log.info(f"Unit: {str(x.serial_number)} completed")
				x.complete(batch_amt=len(global_units))
