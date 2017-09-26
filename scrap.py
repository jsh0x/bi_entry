import logging.config
from time import sleep
import sys
from typing import List
from operator import attrgetter

from common import Application, Unit, timer, access_grid
from constants import REGEX_BUILD as build_regex
from exceptions import *
from crypt import decrypt
from sql import SQL_Lite, MS_SQL

import pyautogui as pag
from pywinauto import mouse, keyboard
import pywinauto.timings
from pywinauto.controls import uia_controls, win32_controls, common_controls

logging.config.fileConfig('config.ini')
log = logging
reason_dict = {'Monitoring': 22, 'RTS': 24, 'Direct': 24}

def Scrap(app: Application, units: List[Unit]):
	pywinauto.timings.Timings.Fast()
	log.debug(f"Starting Scrap script with units: {', '.join(unit.serial_number_prefix+unit.serial_number for unit in units)}")
	sl_win = app.win32.window(title_re='Infor ERP SL (EM)*')
	sl_uia = app.uia.window(title_re='Infor ERP SL (EM)*')
	if not sl_win.exists():
		map(lambda x: x.reset(), units)
		sys.exit(1)
	log.debug([x.texts()[0] for x in sl_uia.WindowMenu.items()])
	app.open_form('Units', 'Miscellaneous Issue')
	# Sort Units by build and location, and order by serial number ascending



	_assorted_lengths_of_string = ('30803410313510753080335510753245107531353410',
	                               '3660426037804620468050404740384034653780366030253080',
	                               '474046203600486038404260432039003960',
	                               '63004620S875486038404260S875432039003960',
	                               '58803900396063004620360048603840426038404620',
	                               '54005880Q750516045004500',
	                               '1121327')
	_adr_data, _adr_data_sl, _usr_data, _pwd_data, _db_data, _db_data_sl, _key = _assorted_lengths_of_string
	mssql = MS_SQL(address=decrypt(_adr_data, _key), username=decrypt(_usr_data, _key), password=decrypt(_pwd_data, _key), database=decrypt(_db_data, _key))




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
	units_master = []
	max_qty = 9999999
	for build, v in unit_dict.items():
		app.verify_form('Miscellaneous Issue')
		sl_win.ItemEdit.set_text(build)
		sleep(0.2)
		sl_win.ItemEdit.send_keystrokes('{TAB}')
		for location, units in v.items():
			app.verify_form('Miscellaneous Issue')
			if location.lower() == 'out of inventory':
				map(units_master.append, units)
				continue
			reason_code = reason_dict[units[0].suffix]
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
			sl_win.ProcessButton.click()
			sl_win.LocationEdit.wait('visible', 2, 0.09)
	app.change_form('Units')
	sl_win.UnitEdit.wait('ready', 2, 0.09)
	for unit in units_master:
		app.verify_form('Units')



	log.info(f"Starting Scrap script with units: {', '.join(unit.serial_number_prefix+unit.serial_number for unit in units)}")
	for unit in units:
		print(unit.id, unit.serial_number, unit.whole_build, unit.location)
	try:
		try:
			for unit in units:
				pass
		except Exception as ex:  # Placeholder
			raise ex
	except Exception as ex:  # Placeholder
		log.exception("BLAH")
		quit()
	else:
		pass
