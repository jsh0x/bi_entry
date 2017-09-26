import datetime
import logging.config
import configparser
from random import randint
from time import sleep
import sys
from exceptions import *


def main():
	from transact import Transact
	from scrap import Scrap
	from reason import reason
	from common import Application, Unit
	from sql import MS_SQL
	from crypt import decrypt

	_assorted_lengths_of_string = ('30803410313510753080335510753245107531353410',
	                               '3660426037804620468050404740384034653780366030253080',
	                               '474046203600486038404260432039003960',
	                               '63004620S875486038404260S875432039003960',
	                               '58803900396063004620360048603840426038404620',
	                               '54005880Q750516045004500',
	                               '1121327')
	_adr_data, _adr_data_sl, _usr_data, _pwd_data, _db_data, _db_data_sl, _key = _assorted_lengths_of_string
	mssql = MS_SQL(address=decrypt(_adr_data, _key), username=decrypt(_usr_data, _key), password=decrypt(_pwd_data, _key), database=decrypt(_db_data, _key))
	slsql = MS_SQL(address=decrypt(_adr_data_sl, _key), username=decrypt(_usr_data, _key), password=decrypt(_pwd_data, _key), database=decrypt(_db_data_sl, _key))
	config = configparser.ConfigParser()
	logging.config.fileConfig('config.ini')
	log = logging

	sleep(randint(10, 20) / 10)
	log.info("Attempting to read 'config.ini'")
	config.read_file(open('config.ini'))
	log.info("Starting Application")
	app = Application(config.get('Paths', 'sl_exe'))
	usr = config.get('Login', 'username')
	pwd = config.get('Login', 'password')

	"""if True:
		from common import center, access_grid
		from sql import SQL_Lite
		from pywinauto.controls import uia_controls, win32_controls
		import pyautogui as pag
		from operator import attrgetter
		app.win32.SignIn.UserLoginEdit.set_text(usr)
		app.win32.SignIn.PasswordEdit.set_text(pwd)
		app.win32.SignIn.set_focus()
		app.win32.SignIn.OKButton.click()
		sleep(5)
		log.info(f"Successfully logged in as '{usr}'")
		app.logged_in = True
		sl_win = app.win32.window(title_re='Infor ERP SL (EM)*')
		sl_uia = app.uia.window(title_re='Infor ERP SL (EM)*')
		app.open_form('Units', 'Miscellaneous Issue')

		results = mssql.execute("SELECT TOP 100 * FROM PyComm WHERE [Status] = 'Scrap' ORDER BY [DateTime] ASC", fetchall=True)
		units = [Unit(mssql, slsql, x) for x in results]

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
			# unit.start()
		units_master = []
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
					# map(units_master.append, units)
					continue
				operator = sql.execute(f"SELECT operator, COUNT(operator) AS count FROM scrap WHERE {' OR '.join([f'id = {x.id}' for x in units])} GROUP BY operator ORDER BY count DESC")
				op = ''.join([x[0].upper() for x in mssql.execute(f"SELECT [FirstName],[LastName] FROM Users WHERE [Username] = '{operator[0].strip()}'")])
				print(op)
				docnum = f"SCRAP {op}"
				qty = len(units)
				sl_win.LocationEdit.wait('ready', 2, 0.09)
				sl_win.LocationEdit.set_text(location)
				sl_win.LocationEdit.send_keystrokes('{TAB}')
				sl_win.LocationEdit.wait('ready', 2, 0.09)
				sl_win.QuantityEdit.wait('ready', 2, 0.09)
				sl_win.QuantityEdit.set_text(str(qty)+'.000')
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
					# unit.misc_issue_timer.start()
					# unit.misc_issue_time += (unit._life_timer.lap() / len(units))
					app.find_value_in_collection(collection='SLSerials', property_='S/N (SerNum)', value=unit.serial_number)
					cell = sl_win.get_focus()
					cell.send_keystrokes('{SPACE}')
					# unit.misc_issue_time += unit.misc_issue_timer.stop()
					units_master.append(unit)
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
				# sl_win.ProcessButton.click()
				# sl_win.LocationEdit.wait('visible', 2, 0.09)
		app.change_form('Units')
		sl_win.UnitEdit.wait('ready', 2, 0.09)
		for unit in units_master:
			app.verify_form('Units')
			sl_win.UnitEdit.set_text(unit.serial_number_prefix+unit.serial_number)
			sl_win.UnitEdit.send_keystrokes('{F4}')  # Filter in Place
			while (sl_win.UnitEdit.texts()[0].strip() != unit.serial_number_prefix + unit.serial_number) and sl_win.UnitEdit.texts()[0].strip():  # While actual serial number != attempted serial number
				state = sl_uia.UnitEdit.legacy_properties()['State']
				bin_state = bin(state)
				log.debug(f"Units Textbox State: {state}")
				if int(bin_state[-7], base=2):  # If the seventh bit == 1
					break
				sleep(0.4)
			if sl_win.UnitEdit.texts()[0].strip() != unit.serial_number_prefix+unit.serial_number:
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
			print(f"'{cust_num}'")
			if cust_num != str(customer_number):
				sl_win.CustNumEdit.set_text(str(customer_number))
				sl_win.CustNumEdit.send_keystrokes('{TAB}')
				sl_win.ShipToEdit.wait('ready', 2, 0.09)
			st = sl_win.ShipToEdit.texts()[0].strip()
			print(f"'{st}'")
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
				dlg.wait('exists', 2, 0.09)
				dlg.YesButton.click()
				dlg.wait_not('exists', 2, 0.09)
				# pag.hotkey('alt', 'y')  # 'Yes' button, (ALT + Y)
				sl_win.UnitStatusCode.wait('ready', 2, 0.09)
				sl_win.UnitStatusCode.set_text(str(scrap_code))
				sl_win.UnitStatusCode.send_keystrokes('{TAB}')
				sl_win.UnitStatusCode.wait('ready', 2, 0.09)
			# pag.hotkey('ctrl', 's')
			sl_win.UnitStatusCode.wait_for_idle()

			if unit.SRO_Line_status != 'Closed':
				sl_win.set_focus()
				sl_win.ServiceOrderLinesButton.click()
				sl_win.ServiceOrderOperationsButton.wait('visible', 2, 0.09)
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
				reason_grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info)
				reason_rows = access_grid(reason_grid, ['General Reason', 'Specific Reason', 'General Resolution', 'Specific Resolution'])
				last_row_i = len(reason_rows) - 1
				last_row2 = reason_rows[last_row_i - 1]
				top_row_i = reason_grid.children_texts().index('Top Row')
				top_row = reason_grid.children()[top_row_i]
				last_row = uia_controls.ListViewWrapper(reason_grid.children()[last_row_i + top_row_i + 1].element_info)

				gen_resn = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('General Reason')).element_info)
				gen_resn_i = gen_resn.rectangle()
				c_coords = center(x1=gen_resn_i.left, y1=gen_resn_i.top, x2=gen_resn_i.right, y2=gen_resn_i.bottom)
				pag.click(*c_coords)
				q = []
				q.append((c_coords, last_row2.General_Reason))
				spec_resn = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('Specific Reason')).element_info)
				spec_resn_i = spec_resn.rectangle()
				c_coords = center(x1=spec_resn_i.left, y1=spec_resn_i.top, x2=spec_resn_i.right, y2=spec_resn_i.bottom)
				q.append((c_coords, str(unit.specific_reason)))
				gen_reso = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('General Resolution')).element_info)
				gen_reso_i = gen_reso.rectangle()
				c_coords = center(x1=gen_reso_i.left, y1=gen_reso_i.top, x2=gen_reso_i.right, y2=gen_reso_i.bottom)
				q.append((c_coords, str(unit.general_resolution)))
				spec_reso = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('Specific Resolution')).element_info)
				spec_reso_i = spec_reso.rectangle()
				c_coords = center(x1=spec_reso_i.left, y1=spec_reso_i.top, x2=spec_reso_i.right, y2=spec_reso_i.bottom)
				q.append((c_coords, str(unit.specific_resolution)))
				for coord, num in q:
					pag.click(*coord)
					sleep(0.5)
					pag.typewrite(num)
					sleep(0.5)

				unit.sro_operations_time += unit.sro_operations_timer.stop()
			sleep(0.2)
			sl_win.send_keystrokes('%s')  # Actions Menu, (ALT + S)
			sleep(0.2)
			sl_win.send_keystrokes('o')  # Notes For Current, (O)
			sleep(0.2)
			app.find_value_in_collection(collection='Object Notes', property_='Subject (DerDesc)', value='NOTES', case_sensitive=True)
			dlg = app.get_popup()
			if dlg.exists(2, 0.09):
				dlg.send_keystrokes('{ENTER}')
				pag.press('f8', 20)
				sl_win.SubjectEdit.set_text('NOTES')
			sl_uia.window(auto_id='DerContentEdit').set_focus()
			note_txt = sl_win.get_focus()
			if note_txt.texts()[0].strip():
				note_txt.set_text(note_txt.texts()[0].strip() + '')
				note_txt.type_keys(f"[{spec_rso_name}")
				note_txt.type_keys("{SPACE}")
				note_txt.type_keys(f"{gen_rso_name}]")
				note_txt.type_keys("{ENTER}")
				note_txt.type_keys(f"[{unit.operator_initials}")
				note_txt.type_keys("{SPACE}")
				note_txt.type_keys(f"{unit.datetime.strftime('%m/%d/%Y')}]")
		quit()"""

	active_days = [int(x) for x in config.get('Schedule', 'active_days').split(',')]
	active_hours = [int(x) for x in config.get('Schedule', 'active_hours').split(',')]
	# active_days = list(range(7))  # TEMP
	# active_hours = list(range(24))  # TEMP
	# Switch between Reason, Scrap, and Transaction
	while True:  # Core Loop
		dt = datetime.datetime.now()
		weekday = int(dt.__format__('%w'))
		# if (weekday not in active_days) or (dt.hour not in active_hours):
		if app.logged_in:
			if app.logged_in:
				sl_uia = app.uia.window(title_re='Infor ERP SL (EM)*')
				sl_uia.SignOutMenuItem.click()
				app.logged_in = False
			sleep(5)
			continue
		if not app.logged_in:
			log.info("SyteLine not logged in, starting login procedure")
			"""try:
				app.win32.SignIn.wait('ready')
				while app.win32.SignIn.exists():
					app.win32.SignIn.UserLoginEdit.set_text(usr)
					app.win32.SignIn.PasswordEdit.set_text(pwd)
					if (app.win32.SignIn.UserLoginEdit.texts()[0] != usr) or (app.win32.SignIn.PasswordEdit.texts()[0] != pwd) or (not app.win32.SignIn.OKButton.exists()):
						raise ValueError()
					app.win32.SignIn.set_focus()
					app.win32.SignIn.OKButton.click()
					Dialog2 = app.uia.top_window()
					while Dialog2.exists():
						# Get dialog info
						Dialog = Dialog2.children()[0]
						title = Dialog.texts()
						buttons = {ctrl.texts()[0].strip('!@#$%^&*()_ ').replace(' ', '_').lower() + '_button': ctrl for ctrl in Dialog.children() if ctrl.friendly_class_name() == 'Button'}
						text = [ctrl.texts()[0].capitalize() for ctrl in Dialog.children() if ctrl.friendly_class_name() == 'Static' and ctrl.texts()[0]]
						if not text:
							break
						log.debug([title, buttons, text, replace_session_regex.search(text[0]), user_session_regex.search(text[0])])
						if replace_session_regex.search(text[0]):  # Handle better in future
							if 'yes_button' in buttons:
								Dialog.set_focus()
								buttons['yes_button'].click()
						elif password_expire_regex.search(text[0]):  # Handle better in future
							if 'ok_button' in buttons:
								Dialog.set_focus()
								buttons['ok_button'].click()
						elif user_session_regex.search(text[0]):  # Handle better in future
							if 'ok_button' in buttons:
								Dialog.set_focus()
								buttons['ok_button'].click()
						elif invalid_login_regex.search(text[0]):  # Handle better in future
							if 'ok_button' in buttons:
								Dialog.set_focus()
								buttons['ok_button'].click()
								raise SyteLineLogInError('')
						else:
							raise ValueError()
			except ValueError:
				continue  # Handle better in future
			else:
				log.info(f"Successfully logged in as '{usr}'")
				app.logged_in = True"""
			sleep(4)
			app.win32.SignIn.UserLoginEdit.set_text(usr)
			app.win32.SignIn.PasswordEdit.set_text(pwd)
			app.win32.SignIn.set_focus()
			app.win32.SignIn.OKButton.click()
			sleep(10)
			log.info(f"Successfully logged in as '{usr}'")
			app.logged_in = True
		if app.logged_in:
			flow = config.get('DEFAULT', 'flow')
			# result = mssql.execute("SELECT TOP 1 * FROM PyComm WHERE [Status] = 'Queued' OR [Status] = 'Reason' OR [Status] = 'Scrap' ORDER BY [DateTime] ASC")
			# result = mssql.execute("SELECT TOP 1 * FROM PyComm WHERE [Status] = 'Queued' ORDER BY [DateTime] ASC")
			result = mssql.execute(f"SELECT TOP 1 * FROM PyComm WHERE [Status] = 'Queued' OR [Status] = 'Custom(Queued)' ORDER BY [DateTime] {flow}")
			# if '3' in usr:
			# 	result2 = mssql.execute("SELECT TOP 100 * FROM PyComm WHERE [Status] = 'Scrap' ORDER BY [DateTime] ASC", fetchall=True)
			# 	if result2:
			# 		result = result2
			if result is None:
				log.info("No valid results, waiting...")
				sleep(10)
				continue
			try:
				unit = Unit(mssql, slsql, result)
			except ValueError:
				log.exception("EARLY ERROR!!!")
				mssql.execute(f"UPDATE PyComm SET [Status] = 'Skipped(VALUE_ERROR)({result.Status})' WHERE [Id] = {result.Id} AND [Serial Number] = '{result.Serial_Number}'")
				continue
			except UnitClosedError:
				log.exception(f"No SRO's exist for serial number: {result.Serial_Number}")
				mssql.execute(f"UPDATE PyComm SET [Status] = 'No Open SRO({result.Status})' WHERE [Serial Number] = '{result.Serial_Number}'")
				continue
			log.info(f"Unit object created with serial_number={unit.serial_number}'")
			script_dict = {'Queued': Transact, 'Reason': reason, 'Scrap': Scrap, 'Custom(Queued)': Transact}
			try:
				if unit.SRO_Line_status == 'Closed':
					raise UnitClosedError(f"Unit '{unit.serial_number}' closed on SRO Lines level")
				if unit.sro_num is None:
					raise UnitClosedError(f"Unit '{unit.serial_number}' has no SROs")
				script_dict.get(result.Status, lambda x,y: None)(app, unit)
			except UnitClosedError:
				unit.skip('No Open SRO')
			# except pag.FailSafeException:
			# 	mssql.execute(f"UPDATE PyComm SET [Status] = '{result.Status}' WHERE [Id] = {result.Id} AND [Serial Number] = '{result.Serial_Number}'")
			# 	sys.exit(1)
			else:
				log.info(f"Unit: {unit.serial_number_prefix+unit.serial_number} completed")
			finally:
				log.info('-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------UNIT-----------------------')

if __name__ == '__main__':
	main()
