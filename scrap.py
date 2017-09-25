import logging.config
from time import sleep
import sys
from typing import List
from collections import Counter

from common import Application, Unit, timer, access_grid
from constants import REGEX_BUILD as build_regex
from exceptions import *

import pyautogui as pag
from pywinauto import mouse, keyboard
import pywinauto.timings
from pywinauto.controls import uia_controls, win32_controls, common_controls

logging.config.fileConfig('config.ini')
log = logging


def Scrap(app: Application, units: List[Unit]):
	pywinauto.timings.Timings.Fast()
	log.debug(f"Starting Scrap script with units: {', '.join(unit.serial_number_prefix+unit.serial_number for unit in units)}")
	forms = ['Units', 'Miscellaneous Issue']
	sl_win = app.win32.window(title_re='Infor ERP SL (EM)*')
	sl_uia = app.uia.window(title_re='Infor ERP SL (EM)*')
	if not sl_win.exists():
		map(lambda x: x.reset(), units)
		sys.exit(1)
	log.debug([x.texts()[0] for x in sl_uia.WindowMenu.items()])
	for form in forms:
		if form not in app.forms:
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
	# Sort Units by build and location, and order by serial number ascending
	sub_units = {str(unit.whole_build)+'_'+str(unit.location): unit for unit in units if (not unit.whole_build.lower().startswith('sl')) or
	                                                         (not unit.whole_build.lower().startswith('cl'))}.update({unit.whole_build.replace(build_regex.match(unit.whole_build).group('build'), build_regex.match(unit.whole_build).group('build')[:3])+'_'+str(unit.location): unit for unit in units if unit.whole_build.lower().startswith('sl') or
		                                              unit.whole_build.lower().startswith('cl')})
	count = Counter(dict(zip(sub_units.keys(), map(len, sub_units.values()))))
	for k in range(1, len(count.keys())+1):
		if sum([x[1] for x in count.most_common(k)]) >= 10:
			break
	else:
		raise ValueError()
	units = [{z.serial_number: z for z in [sub_units[y] for y in [x[0] for x in count.most_common(k)]]}[a] for a in sorted({z.serial_number: z for z in [sub_units[y] for y in [x[0] for x in count.most_common(k)]]})[:10]]
	map(Unit.start, units)

	try:
		try:
			pass
		except Exception as ex:  # Placeholder
			raise ex
	except Exception as ex:  # Placeholder
		log.exception("BLAH")
		quit()
	else:
		pass
