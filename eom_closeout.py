import datetime
import pathlib
import sys
from queue import Queue
from time import sleep

import pyautogui as pag
import pywinauto.timings
from pywinauto import keyboard
from pywinauto.controls import win32_controls

from common import Application_ALT, Unit_ALT
from constants import SYTELINE_WINDOW_TITLE
from crypt import decrypt
from sql_alt import MS_SQL


def main():
    fp = pathlib.WindowsPath.home() / 'AppData' / 'Local' / 'Apps' / '2.0' / 'QQC2A2CQ.YNL' / 'K5YT3MK7.VDY' / 'sl8...ient_002c66e0bc74a4c9_0008.0003_1fdd36ef61625f38' / 'WinStudio.exe'
    app = Application_ALT(fp.as_posix())
    usr = 'BISync01'
    pwd = 'N0Trans@cti0ns'
    _assorted_lengths_of_string = ('30803410313510753080335510753245107531353410',
                                   '3660426037804620468050404740384034653780366030253080',
                                   '474046203600486038404260432039003960',
                                   '63004620S875486038404260S875432039003960',
                                   '58803900396063004620360048603840426038404620',
                                   '54005880Q750516045004500',
                                   '1121327')
    _adr_data, _adr_data_sl, _usr_data, _pwd_data, _db_data, _db_data_sl, _key = _assorted_lengths_of_string
    mssql = MS_SQL(address=decrypt(_adr_data, _key), username=decrypt(_usr_data, _key),
                   password=decrypt(_pwd_data, _key), database=decrypt(_db_data, _key))
    slsql = MS_SQL(address=decrypt(_adr_data_sl, _key), username=decrypt(_usr_data, _key),
                   password=decrypt(_pwd_data, _key), database=decrypt(_db_data_sl, _key))
    q = Queue(maxsize=0)
    app.log_in(usr, pwd)
    print("Loading units...")
    results = mssql.execute(
        "Select distinct [Serial Number] From Operations Where Operation = 'QC' and Convert(date, DateTime) Between '9/1/2017' and '10/1/2017'",
        fetchall=True)
    for x in results:
        q.put(Unit_ALT(mssql, slsql, x[0]))
    print(f"~{q.qsize()} units loaded!")
    app.verify_form('Units')
    pywinauto.timings.Timings.Fast()
    print(f"Running...")
    while not q.empty():
        try:
            unit = q.get()
            if unit.SKIPME:
                continue
            sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
            sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
            if not sl_win.exists():
                sys.exit(1)
            app.verify_form('Units')
            sleep(0.2)
            sl_win.UnitEdit.set_text(unit.serial_number_prefix + unit.serial_number)
            sleep(0.2)
            sl_win.send_keystrokes('{F4}')
            count = 0
            while (sl_win.UnitEdit.texts()[0].strip() != unit.serial_number_prefix + unit.serial_number) and \
                    sl_win.UnitEdit.texts()[0].strip():
                if count >= 30:
                    raise ZeroDivisionError()
                sleep(0.4)
                count += 1
            if sl_win.UnitEdit.texts()[0].strip() != unit.serial_number_prefix + unit.serial_number:
                raise ZeroDivisionError()
            if not sl_win.ServiceOrderLinesButton.is_enabled():
                raise ZeroDivisionError()
            sl_win.set_focus()
            sl_win.ServiceOrderLinesButton.click()
            sl_win.ServiceOrderOperationsButton.wait('visible', 2, 0.09)
            app.find_value_in_collection('Service Order Lines', 'SRO (SroNum)', unit.sro_num)
            dlg = app.get_popup(0.5)
            count = 0
            while dlg:
                dlg[0].close()
                count += 1
                dlg = app.get_popup()
            else:
                if count > 0:
                    raise ZeroDivisionError()
            sl_win.set_focus()
            sl_win.ServiceOrderOperationsButton.click()
            sl_win.SROLinesButton.wait('visible', 2, 0.09)
            sl_win.CompletedDateEdit.set_text(datetime.datetime.now().strftime('%m/%d/%Y %I:%M:%S %p'))
            sl_win.CompletedDateEdit.send_keystrokes('^s')
            sleep(0.5)
            pag.hotkey('ctrl', 's')
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
            for presses in range(2):
                sl_uia.CancelCloseButton.click()
            sl_win.UnitEdit.wait('visible', 2, 0.09)
            sleep(0.2)
            sl_win.send_keystrokes('{F4}')  # Clear Filter
            sleep(0.2)
            sl_win.send_keystrokes('{F5}')  # Clear Filter
            sleep(0.2)
        except Exception as ex:
            sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
            sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
            if sl_uia.exists(2, 0.09):
                if 'SRO Transactions' in app.forms:
                    sl_uia.CancelCloseButton.click()
                    dlg = app.get_popup()
                    while dlg:
                        dlg[0].close()
                        dlg = app.get_popup()
                if 'Service Order Operations' in app.forms:
                    sl_uia.CancelCloseButton.click()
                    dlg = app.get_popup()
                    while dlg:
                        dlg[0].close()
                        dlg = app.get_popup()
                if 'Service Order Lines' in app.forms:
                    sl_uia.CancelCloseButton.click()
                    dlg = app.get_popup()
                    while dlg:
                        dlg[0].close()
                        dlg = app.get_popup()
                sl_win.send_keystrokes('{F4}')
                sl_win.send_keystrokes('{F5}')
    print(f"Done!")
    input('Press any key to exit...')


if __name__ == '__main__':
    main()
