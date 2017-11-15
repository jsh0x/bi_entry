import random
from string import ascii_letters, digits, punctuation, whitespace
from time import sleep

import pywinauto.timings

from _common import SyteLinePupperMaster, Unit
from config import *
from processes import transact

# _assorted_lengths_of_string = ('30803410313510753080335510753245107531353410', '3660426037804620468050404740384034653780366030253080',
#                                '474046203600486038404260432039003960', '63004620S875486038404260S875432039003960',
#                                '58803900396063004620360048603840426038404620', '54005880Q750516045004500', '1121327')
# _adr_data, _adr_data_sl, _usr_data, _pwd_data, _db_data, _db_data_sl, _key = _assorted_lengths_of_string
# mssql = MSSQL.legacy_encrypted_connection(_key, address=_adr_data, username=_usr_data, password=_pwd_data, database=_db_data)


#


# print(_check_units(mssql, 'Queued'))
# quit()
fp = application_filepath
fp2 = r'C:\Windows\System32\notepad.exe'
n = 2
pywinauto.timings.Timings.Fast()
# 1053 [255, 128, 128]
# 1059 [0, 255, 0]
colors = {}
val_list = ['10' + str(x).rjust(2, '0') for x in range(70)] + ['11' + str(x).rjust(2, '0') for x in range(17)]
rem = ['1015', '1038', '1044', '1065', '1066', '1067']

user_list = ['bigberae', username, 'BISync01', 'BISync02', 'BISync03']
pwd_list = ['W!nter17', password, 'N0Trans@cti0ns', 'N0Re@s0ns', 'N0Gue$$!ng']


def temp(char: str):
	if char in whitespace:
		return '0'
	elif char in ascii_letters:
		return '1'
	elif char in digits:
		return '2'
	else:
		return '3'


def parse_text(text: str) -> str:
	mapped_text = ''.join(temp(x) for x in text)
	char = [x for x in text if x in ascii_letters]
	num = [x for x in text if x in digits]
	sym = [x for x in text if x in punctuation]
	random.shuffle(char)
	random.shuffle(num)
	random.shuffle(sym)
	retval = ''
	for i in mapped_text:
		if i == '0':
			retval += ' '
		elif i == '1':
			retval += char.pop()
		elif i == '2':
			retval += num.pop()
		elif i == '3':
			retval += sym.pop()
	return retval


def main(process):
	with SyteLinePupperMaster(1) as pm:
		for ppt in pm.children():
			forms = process.starting_forms
			ppt.set_input(lambda x, y: x.app.quick_open_form(*y), forms)
		pm.run_process(process, ppt)
	quit()

main(transact)

if __name__ == '__main__':
	main(transact)
