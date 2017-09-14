from sys import exc_info
import logging.config
from time import sleep
from traceback import TracebackException

from common import Application, Unit, REGEX_ROW_NUMBER as row_number_regex
from exceptions import *

from common import timer, access_grid
import pywinauto as pwn
# from pywinauto import Application, application
import pyautogui as pag
import pywinauto.timings
from pywinauto.controls import uia_controls, win32_controls, common_controls

pywinauto.timings.Timings.Fast()
logging.config.fileConfig('config2.ini')
log = logging

def transact(app: Application, unit: Unit):
	log.info(f"Starting Transact script with unit: {unit.serial_number_prefix+unit.serial_number}")
	form = 'Units'
	sl_win = app.win32.window(title_re='Infor ERP SL (EM)*')
	sl_uia = app.uia.window(title_re='Infor ERP SL (EM)*')
	# while sl_win.exists():
	if not sl_win.exists():
		raise ValueError()
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
	except ZeroDivisionError:
		pass
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
	except ZeroDivisionError:
		pass

	try:
		# form = 2
		t_temp = timer.stop()
		log.debug(f"Time waited for Service Order Lines: {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
		# TODO: Open SRO Operations-level status if closed
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
				posted_parts = access_grid(transaction_grid, ['Posted', 'Item', 'Location', 'Quantity', 'Billing Code', 'Trans Date'], ('Posted', True))
				log.debug(posted_parts)
				sl_win.IncludePostedButton.click()
				timer.start()
				sl_win.ApplyFilterButton.click()
				sl_win.ApplyFilterButton.wait('ready', 2, 0.09)
				t_temp = timer.stop()
				log.debug(f"Time waited for second Application of Filter: {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
				unposted_parts = access_grid(transaction_grid, ['Posted', 'Item', 'Location', 'Quantity', 'Billing Code', 'Trans Date'])
				log.debug(unposted_parts)
				# TODO: Based on already posted and unposted, transact accordingly
				columns = ['Item', 'Location', 'Quantity', 'Billing Code', 'Trans Date']
				top_row = transaction_grid.children()[transaction_grid.children_texts().index('Top Row')]
				log.debug(F"Columns: {top_row.children_texts()[1:10]}")
				for part in unit.parts:
					log.debug(f"Attempting to transact part {part}")
					last_row = uia_controls.ListViewWrapper(transaction_grid.children()[-1].element_info)
					item = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('Item')).element_info)
					location = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('Location')).element_info)
					quantity = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('Quantity')).element_info)
					billcode = uia_controls.ListItemWrapper(last_row.item(top_row.children_texts().index('Billing Code')).element_info)
					# sl_win.set_focus()
					# TODO: Replace pag with pwn.mouse
					# TODO: Turn pag fs off
					pag.click(pag.center((item.rectangle().left, item.rectangle().top, item.rectangle().right-item.rectangle().left, item.rectangle().bottom-item.rectangle().top)))
					sleep(0.5)
					pag.press('enter', presses=2)
					sleep(0.5)
					pag.typewrite(part.part_number)
					sleep(0.5)
					if part.quantity > 1:
						# sl_win.set_focus()
						pag.click(pag.center((quantity.rectangle().left, quantity.rectangle().top, quantity.rectangle().right - quantity.rectangle().left, quantity.rectangle().bottom - quantity.rectangle().top)))
						sleep(0.5)
						pag.press('enter', presses=2)
						sleep(0.5)
						pag.typewrite(part.quantity)
						sleep(0.5)
						# while sl_win.InforSLDialog.exists():
						# 	print(sl_win.InforSLDialog.get_properties())
						# 	log.debug("Close pop-up")
						# 	sl_win.InforSLDialog.close()
						# 	sleep(0.2)
					# sl_win.set_focus()
					pag.click(pag.center((billcode.rectangle().left, billcode.rectangle().top, billcode.rectangle().right - billcode.rectangle().left, billcode.rectangle().bottom - billcode.rectangle().top)))
					sleep(0.5)
					pag.press('enter', presses=2)
					if unit.suffix == 'Direct' or unit.suffix == 'RTS':
						bc = 'Contract'
					else:
						bc = 'No Charge'
					sleep(0.5)
					pag.typewrite(bc)
					sleep(0.5)
					# sl_win.set_focus()
					pag.click(pag.center((location.rectangle().left, location.rectangle().top, location.rectangle().right - location.rectangle().left, location.rectangle().bottom - location.rectangle().top)))
					sleep(0.5)
					pag.press('enter', presses=2)
					sleep(0.5)
					pag.typewrite(part.location)
					sleep(0.5)
				pass
			except ZeroDivisionError:
				pass
		if not sl_win.ReceivedDateEdit.texts()[0].strip():
			sl_win.ReceivedDateEdit.set_text(unit.eff_date.strftime('%m/%d/%Y %I:%M:%S %p'))
		if not sl_win.FloorDateEdit.texts()[0].strip():
			sl_win.FloorDateEdit.set_text(unit.datetime.strftime('%m/%d/%Y %I:%M:%S %p'))
		if unit.operation == 'QC':
			sl_win.CompletedDateEdit.set_text(unit.datetime.strftime('%m/%d/%Y %I:%M:%S %p'))
		common_controls.TabControlWrapper(sl_win.TabControl).select('Reasons')  # Open 'Reasons' Tab
		if unit.operation == 'QC' or True:
			reason_grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info)
			for ch in reason_grid.children_texts():
				r = row_number_regex.match(ch)
				print(r.groups())
				print(r.group())
				print(r.groupdict())
				print(r.lastgroup)
			# rows = [for x in reason_grid.children_texts() if row_number_regex.match(x)]
			print(reason_grid.children_texts())
		# TODO: Handle Reasons Grid
		# TODO: Look into finding if trailing empty line or not
		if unit.operation == 'QC':
			sl_win.StatusEdit3.set_text('Closed')
		# TODO: Save and go back to beginning
		quit()
	except ZeroDivisionError:
		pass
	else:
		pass