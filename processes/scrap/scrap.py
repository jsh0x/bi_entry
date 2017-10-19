import logging
import sys
from operator import attrgetter
from time import sleep
from typing import List

import pyautogui as pag
import pywinauto.timings
from pywinauto import keyboard
from pywinauto.controls import common_controls, uia_controls, win32_controls

from _common import *
from constants import SYTELINE_WINDOW_TITLE
from exceptions import *
from utils import MS_SQL, SQL_Lite


log = logging.getLogger(__name__)
reason_dict = {'Monitoring': 22, 'RTS': 24, 'Direct': 24}

def Scrap(app: Application, units: List[Unit]):
	completed_units = []
	global_units = []
	try:
		pywinauto.timings.Timings.Fast()
		log.debug(f"Starting Scrap script with units: {', '.join(unit.serial_number_prefix+unit.serial_number for unit in units)}")
		sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
		sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
		if not sl_win.exists():
			for unit in units:
				unit.reset()
			sys.exit(1)
		log.debug([x.texts()[0] for x in sl_uia.WindowMenu.items()])
		app.verify_form('Units')
		app.verify_form('Miscellaneous Issue')
		# Sort Units by build and location, and order by serial number ascending

		_assorted_lengths_of_string = ('30803410313510753080335510753245107531353410',
		                               '3660426037804620468050404740384034653780366030253080',
		                               '474046203600486038404260432039003960',
		                               '63004620S875486038404260S875432039003960',
		                               '58803900396063004620360048603840426038404620',
		                               '54005880Q750516045004500',
		                               '1121327')
		_adr_data, _adr_data_sl, _usr_data, _pwd_data, _db_data, _db_data_sl, _key = _assorted_lengths_of_string
		mssql = MS_SQL.legacy_encrypted_connection(_key, address=_adr_data, username=_usr_data, password=_pwd_data, database=_db_data)

		sql = SQL_Lite(':memory:')
		sql.execute("CREATE TABLE scrap (id integer, serial_number text, build text, location text, datetime text, operator text)")
		for unit in units:
			sql.execute(
					f"INSERT INTO scrap(id, serial_number, build, location, datetime, operator) VALUES "
					f"({unit.id}, '{unit.serial_number}', '{unit.whole_build}', '{unit.location}', '{unit.datetime.strftime('%m/%d/%Y %H:%M:%S')}', '{unit.operator}')")
		results = sql.execute(f"SELECT build,location,COUNT(location) AS count FROM scrap GROUP BY build, location ORDER BY count DESC", fetchall=True)
		sleep(1)
		id_list = []
		for build, location, count in results:
			for x in sql.execute(f"SELECT * FROM scrap WHERE build = '{build}' AND location = '{location}' ORDER BY datetime ASC", fetchall=True):
				id_list.append(x.id)
				if len(id_list) >= 10:
					break
			if len(id_list) >= 10:
				break
		units_master = sorted([unit for unit in units if unit.id in id_list], key=attrgetter('serial_number'))
		unit_dict = {}
		for unit in units_master:
			if unit.whole_build not in unit_dict:
				unit_dict[unit.whole_build] = {unit.location: []}
			elif unit.location not in unit_dict[unit.whole_build]:
				unit_dict[unit.whole_build][unit.location] = []
			unit_dict[unit.whole_build][unit.location].append(unit)
			unit.start()
		max_qty = 9999999
		for build, v in unit_dict.items():
			app.verify_form('Miscellaneous Issue')
			sl_win.ItemEdit.set_text(build)
			sleep(0.2)
			sl_win.ItemEdit.send_keystrokes('{TAB}')
			reason_code = 22  # 24 if direct'
			for location, units in v.items():
				app.verify_form('Miscellaneous Issue')
				if location.lower() == 'out of inventory':
					for unit in units:
						global_units.append(unit)
					continue
				operator = sql.execute(f"SELECT operator, COUNT(operator) AS count FROM scrap WHERE {' OR '.join([f'id = {x.id}' for x in units])} GROUP BY operator ORDER BY count DESC")
				op = ''.join([x[0].upper() for x in mssql.execute(f"SELECT [FirstName],[LastName] FROM Users WHERE [Username] = '{operator[0].strip()}'")])
				docnum = f"SCRAP {op}"
				qty = len(units)
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
				for unit in units:
					unit.misc_issue_timer.start()
					unit.misc_issue_time += (unit._life_timer.lap() / len(units))
					app.find_value_in_collection(collection='SLSerials', property_='S/N (SerNum)', value=unit.serial_number)
					cell = sl_win.get_focus()
					cell.send_keystrokes('{SPACE}')
					unit.misc_issue_time += unit.misc_issue_timer.stop()
					global_units.append(unit)
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
			app.verify_form('Units')
			sl_win.UnitEdit.set_text(unit.serial_number_prefix + unit.serial_number)
			sl_win.UnitEdit.send_keystrokes('{F4}')  # Filter in Place
			while (sl_win.UnitEdit.texts()[0].strip() != unit.serial_number_prefix + unit.serial_number) and sl_win.UnitEdit.texts()[
				0].strip():  # While actual serial number != attempted serial number
				state = sl_uia.UnitEdit.legacy_properties()['State']
				bin_state = bin(state)
				log.debug(f"Units Textbox State: {state}")
				if int(bin_state[-7], base=2):  # If the seventh bit == 1
					break
				sleep(0.4)
			if sl_win.UnitEdit.texts()[0].strip() != unit.serial_number_prefix + unit.serial_number:
				if not sl_win.UnitEdit.texts()[0].strip():
					raise InvalidSerialNumberError(f"Expected input serial number '{unit.serial_number_prefix+unit.serial_number}', returned None")
				else:
					raise SyteLineFilterInPlaceError(f"Expected input serial number '{unit.serial_number_prefix+unit.serial_number}', returned '{sl_win.UnitEdit.texts()[0].strip()}'")
			sl_win.set_focus()
			customer_number = 302
			ship_to = int(unit.phone) + 1  # if unit.phone: 2, else: 1
			scrap_code = 'SCRAPPED' + ('1' * int(unit.phone))  # if unit.phone: 'SCRAPPED1', else: 'SCRAPPED'
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
				c_coords = center(x1=r_i.left, y1=r_i.top, x2=r_i.right, y2=r_i.bottom)
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

			if unit.SRO_Line_status != 'Closed':
				sl_win.set_focus()
				sl_win.ServiceOrderLinesButton.click()
				sl_win.ServiceOrderOperationsButton.wait('visible', 3, 0.09)
				sl_win.set_focus()
				sl_win.ServiceOrderOperationsButton.click()
				sl_win.SROLinesButton.wait('visible', 2, 0.09)
				unit.sro_operations_timer.start()
				if sl_win.StatusEdit3.texts()[0].strip() == 'Closed':
					status = win32_controls.EditWrapper(sl_win.StatusEdit3.element_info)
					status.set_text('Open')
					status.click_input()
					pag.press('tab')
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
				for i, row in enumerate(reason_rows[::-1]):
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
				if sl_win.ReasonNotesEdit.texts()[0].strip():
					sl_win.ReasonNotesEdit.set_text(sl_win.ReasonNotesEdit.texts()[0].strip() +
					                                f"\n[{unit.specific_resolution_name.upper()} {unit.general_resolution_name.upper()}]\n[{unit.operator_initials} {unit.datetime.strftime('%m/%d/%Y')}]")
				else:
					sl_win.ReasonNotesEdit.set_text(
							f"[{unit.specific_resolution_name.upper()} {unit.general_resolution_name.upper()}]\n[{unit.operator_initials} {unit.datetime.strftime('%m/%d/%Y')}]")
				sl_win.ReasonNotesEdit.send_keystrokes('^s')
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
				unit.sro_operations_time += unit.sro_operations_timer.stop()
				sl_uia.CancelCloseButton.click()
				sl_uia.CancelCloseButton.click()
				sleep(0.5)
				sl_win.ServiceOrderLinesButton.wait('visible', 2, 0.09)
			sl_win.send_keystrokes('%s')  # Actions Menu, (ALT + S)
			sleep(0.2)
			sl_win.send_keystrokes('o')  # Notes For Current, (O)
			sleep(0.5)
			app.find_value_in_collection(collection='Object Notes', property_='Subject (DerDesc)', value='NOTES', case_sensitive=True)
			dlg = app.get_popup(2)
			if dlg:
				dlg[0].send_keystrokes('{ENTER}')
				sl_win.send_keystrokes('{F8 20}')
				sl_win.SubjectEdit.set_text('NOTES')
			sl_uia.window(auto_id='DerContentEdit').set_focus()
			note_txt = sl_win.get_focus()
			if note_txt.texts()[0].strip():
				note_txt.set_text(note_txt.texts()[0].strip() + f"\n[{unit.specific_resolution_name} {unit.general_resolution_name}]\n[{unit.operator_initials} {unit.datetime.strftime('%m/%d/%Y')}]")
			else:
				note_txt.set_text(f"[{unit.specific_resolution_name} {unit.general_resolution_name}]\n[{unit.operator_initials} {unit.datetime.strftime('%m/%d/%Y')}]")
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
	finally:
		for x in completed_units:
			log.info(f"Unit: {x.serial_number_prefix+x.serial_number} completed")
			x.complete(batch_amt=len(global_units))
