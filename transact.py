from sys import exc_info
import logging.config
from time import sleep
from traceback import TracebackException

from common import Application, Unit
from exceptions import *

from common import timer, access_grid
import pywinauto as pwn
# from pywinauto import Application, application
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
	if sl_win.exists():  # If SyteLine window is open
		log.debug([x.texts()[0] for x in sl_uia.WindowMenu.items()])
		if form not in app.forms:  # If required form is not open
			sl_win.send_keystrokes('^o')
			app.win32.SelectForm.AllContainingEdit.set_text(form)
			app.win32.SelectForm.FilterButton.click()
			common_controls.ListViewWrapper(app.win32.SelectForm.ListView).item(form).click()
			app.win32.SelectForm.OKButton.click()
			sleep(4)
			if form not in app.forms:
				raise ValueError()
		# TODO: Check if 'Units' form is focused, if not, do so
		try:
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
				common_controls.TabControlWrapper(sl_win.TabControl).select('Owner History')  # Open 'Owner History' Tab
				owner_history_grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info)  # Wrap DataGridView
				log.debug(owner_history_grid.get_properties())
				if owner_history_grid.control_count() < 3:  # If there are no SROs in the DataGrid
					raise UnitClosedError("No SROs found in Data Grid")
				initial_date = datetime.datetime.strptime(sorted(access_grid(owner_history_grid, 'Eff Date'), reverse=True)[0][0], '%m/%d/%Y')  # Get 'Initial Date'
				log.info(f"Initial Date found: {initial_date.strftime('%m/%d/%Y')}")
				log.debug("Service Order Lines Button clicked")
				timer.start()
				sl_win.ServiceOrderLinesButton.click()
				sl_win.ServiceOrderOperationsButton.wait('visible', 2, 0.09)
			except UnitClosedError as ex:
				log.exception(f"Unit '{unit.serial_number_prefix+unit.serial_number}' has no SROs")
				raise ex
			try:
				t_temp = timer.stop()
				log.debug(f"Time waited for Service Order Lines: {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
				sro_grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info)
				log.debug(sro_grid.get_properties())
				sros = access_grid(sro_grid, ['SRO', 'Line'], ('Status', 'Open'))
				if len(sros) == 0:
					raise UnitClosedError("No Open SROs found")
				log.debug(f"Found Open SRO(s) and Line(s):{''.join([f' {sro},{line}' for sro,line in sros])}")
				log.info(f"Found {len(sros)} Open SRO(s)")
				for sro,line in sros:
					form = 1
					try:
						sro2 = sl_win.SROEdit.texts()[0].strip()
						line2 = sl_win.LineEdit.texts()[0].strip()
						if not ((sro == sro2) and (line == line2)):
							pass
						if sl_win.StatusEdit2.texts()[0].strip() != 'Open':
							log.warning(f"SRO '{sro}' closed on SRO Lines level")
							raise SROClosedWarning(f"SRO '{sro}' closed on SRO Lines level")
					except SROClosedWarning:
						continue
					try:
						log.info(f"SRO '{sro}' open on SRO Lines level")
						log.debug("Service Order Operations Button clicked")
						timer.start()
						sl_win.ServiceOrderOperationsButton.click()
						sl_win.SROLinesButton.wait('visible', 2, 0.09)
						form = 2
						t_temp = timer.stop()
						log.debug(f"Time waited for Service Order Lines: {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
						if sl_win.StatusEdit3.texts()[0].strip() != 'Open' or not sl_win.SROTransactionsButton.is_enabled():
							log.warning(f"SRO '{sro}' closed on SRO Operations level")
							raise SROClosedWarning(f"SRO '{sro}' closed on SRO Operations level")
						log.info(f"SRO '{sro}' open on SRO Operations level")
					except SROClosedWarning:
						sl_win.CancelCloseToolbarButton.click()
						continue
					else:
						break
				else:
					raise UnitClosedError("No Open SROs found")
			except UnitClosedError as ex:
				log.exception(f"Unit '{unit.serial_number_prefix+unit.serial_number}' has no open SROs")
				for presses in range(form):
					sl_win.CancelCloseToolbarButton.click()
				raise ex
			try:
				if unit.parts:
					timer.start()
					sl_win.SROTransactionsButton.click()
					log.debug("SRO Transactions Button clicked")
					# sl_win.PostBatchButton.wait('active', 2, 0.09)
					sl_win.FilterDateRangeEdit.wait('ready', 2, 0.09)
					t_temp = timer.stop()
					log.debug(f"Time waited for SRO Transactions: {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
					log.info("Starting transactions")
					sl_win.FilterDateRangeEdit.set_text(initial_date.strftime('%m/%d/%Y'))
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
					sl_win.IncludePostedButton.check()
					sl_win.ApplyFilterButton.click()
					sl_win.ApplyFilterButton.wait('ready', 2, 0.09)
					t_temp = timer.stop()
					log.debug(f"Time waited for second Application of Filter: {t_temp.seconds}.{str(t_temp.microseconds/1000).split('.', 1)[0].rjust(3, '0')}")
					unposted_parts = access_grid(transaction_grid, ['Posted', 'Item', 'Location', 'Quantity', 'Billing Code', 'Trans Date'])
					print(transaction_grid.children_texts())
					quit()
					# TODO: Based on already posted and unposted, transact accordingly
					columns = ['Item', 'Location', 'Quantity', 'Billing Code', 'Trans Date']
					for part in unit.parts:
						log.debug(f"Attempting to transact part {part}")
						# TODO: Transact parts
					pass
			except ZeroDivisionError as ex:
				raise ex
			try:
				if not sl_win.ReceivedDateEdit.texts()[0].strip():
					sl_win.ReceivedDateEdit.set_text(initial_date.strftime('%m/%d/%Y %I:%M:%S %p'))
				if not sl_win.FloorDateEdit.texts()[0].strip():
					sl_win.FloorDateEdit.set_text(unit.datetime.strftime('%m/%d/%Y %I:%M:%S %p'))
				if unit.operation == 'QC':
					sl_win.CompletedDateEdit.set_text(unit.datetime.strftime('%m/%d/%Y %I:%M:%S %p'))
				common_controls.TabControlWrapper(sl_win.TabControl).select('Reasons')  # Open 'Reasons' Tab
				reason_grid = uia_controls.ListViewWrapper(sl_uia.DataGridView.element_info)
				# TODO: Handle Reasons Grid
				# TODO: Look into finding if trailing empty line or not
				if unit.operation == 'QC':
					sl_win.StatusEdit3.set_text('Closed')
				# TODO: Save and go back to beginning
				quit()
			except ZeroDivisionError as ex:
				raise ex
		except SyteLineFilterInPlaceError:
			sl_win.send_keystrokes('{F4}')
			sl_win.send_keystrokes('{F5}')
		except UnitClosedError:
			sl_win.send_keystrokes('{F4}')
			sl_win.send_keystrokes('{F5}')

		else:
			pass  # Success