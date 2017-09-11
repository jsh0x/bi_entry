import logging.config
from time import sleep

from common import Application, Unit
from exceptions import *

import pywinauto as pwn
# from pywinauto import Application, application
from pywinauto.timings import Timings
from pywinauto.controls import uia_controls, win32_controls, common_controls

Timings.Fast()
logging.config.fileConfig('config2.ini')
log = logging


def transact(app: Application, unit: Unit):
	log.info(f"Starting Transact script with unit: {unit.serial_number_prefix+unit.serial_number}")
	form = 'Units'
	sl_win = app.win32.window(title_re='Infor ERP SL (EM)*')
	sl_uia = app.uia.window(title_re='Infor ERP SL (EM)*')
	# while sl_win.exists():
	if sl_win.exists():
		log.debug([x.texts()[0] for x in sl_uia.WindowMenu.items()])
		if form not in app.forms:
			sl_win.send_keystrokes('^o')
			app.win32.SelectForm.AllContainingEdit.set_text(form)
			app.win32.SelectForm.FilterButton.click()
			common_controls.ListViewWrapper(app.win32.SelectForm.ListView).item(form).click()
			app.win32.SelectForm.OKButton.click()
			sleep(4)
			if form not in app.forms:
				raise ValueError()
		# TODO: Check if 'Units' form is focused, if not, do so
		in_hell = 1
		while in_hell:
			try:
				sl_win.UnitEdit.set_text(unit.serial_number_prefix+unit.serial_number)
				sleep(0.2)
				sl_win.send_keystrokes('{F4}')
				count = 0
				while (sl_win.UnitEdit.texts()[0].strip() != unit.serial_number_prefix+unit.serial_number):  # or (not sl_uia.UnitEdit.legacy_properties()['IsReadOnly'])
					if count >= 30:
						raise SyteLineFilterInPlaceError('')
					sleep(0.4)
					count += 1
				else:
					count = 0
				if sl_win.UnitEdit.texts()[0].strip() != unit.serial_number_prefix+unit.serial_number:
					if not sl_win.UnitEdit.texts()[0].strip():
						raise InvalidSerialNumberError('')
					else:
						raise SyteLineFilterInPlaceError('')
				common_controls.TabControlWrapper(sl_win.TabControl).select('Owner History')
				grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info)
				log.debug(grid.get_properties())
				for ch in grid.children()[3:]:
					grid2 = uia_controls.ListViewWrapper(ch.element_info)
					data_item = grid2.item(1)
					log.debug(data_item.legacy_properties()['Value'])
				val = {name+str(i):t for i,ch in enumerate(grid.children()[3:]) for name,t in zip(uia_controls.ListViewWrapper(grid.children()[2].element_info).children_texts()[1:], uia_controls.ListViewWrapper(ch.element_info).children_texts()[1:])}
				print(val)
				quit()

			except TimeoutError:
				break
			except InvalidSerialNumberError as ex:
				if unit.serial_number_prefix == 'BE':
					unit._serial_number_prefix = 'ACB'
				else:
					raise ex
			except SyteLineFilterInPlaceError:
				pass
		else:
			pass  # Success