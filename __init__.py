#! python3 -W ignore
# coding=utf-8
__author__ = 'jsh0x'
# import os
# with open('C:/Users/jredding/Desktop/quick.txt', 'w') as f:
# 	f.write(os.getcwd())
from _logging import initialize_logger
from _globals import *
from _globals import config
import logging
from exceptions import *
from processes import *
from utils.decorators import *
from processes.Transact import TransactUnit
from processes.Reason import ReasonUnit
from constants import SYTELINE_WINDOW_TITLE
from core.Application import Application
from time import sleep
"""
# try:
# 	config = read_config(my_directory)
# except FileNotFoundError:
# 	my_name = os.environ['COMPUTERNAME']
# 	if my_name == 'BIGBERAESEW10':
# 		create_config('BISync03', 'Gue$$!ngN0')
# 	elif my_name == 'MFGW10PC-1':
# 		create_config('jredding', 'JRJan18!')
# 	elif my_name == 'MFGPC89':
# 		create_config('BISync01', 'Trans@cti0nsN0')
# 	elif my_name == 'MFGW10PC-27':
# 		create_config('BISync02', 'Re@s0nsN0')
# 	else:
# 		create_config('jredding', 'JRJan18!')
# 	if False:
# 		create_config('bigberae', 'W!nter17')
# 	config = read_config(my_directory)
# desktop = pathlib.WindowsPath.home() / 'Desktop'
# shortcut = desktop / 'bi_entry.lnk'
# if not shortcut.exists():
# 	create_shortcut(name='BI_Entry', exe_path=my_directory / 'bin' / 'exe.win-amd64-3.6' / 'bi_entry.exe', startin=my_directory,
# 	                icon_path=my_directory / 'bin' / 'exe.win-amd64-3.6' / 'bi_entry.ico')
# 	sys.exit()

# bit = 8 * struct.calcsize("P")
# major, minor, micro = version.major, version.minor, version.micro
clap = argparse.ArgumentParser(prog='BI-Entry')
clap.add_argument('cmd', choices=['build', 'run'])
sub_clap = clap.add_subparsers(help='sub-command help')

# Create a parser for the "build" command
clap_bld = sub_clap.add_parser('build', help='build help')

clap_bld.add_argument('-v', '--version', default='stable')  # Accepts period-seperated int's, as well as the strings "stable" and "latest"
clap_bld.add_argument('-d', '--destination', type=pathlib.Path, default=pathlib.WindowsPath(os.environ["PROGRAMDATA"]))

bld_group = clap_bld.add_mutuallyexclusive_group(required=True)
bld_group.add_argument('-i', '--install', dest='sub_cmd', action='store_const', const=2)
bld_group.add_argument('-u', '--update', dest='sub_cmd', action='store_const', const=1)
bld_group.add_argument('-n', '--uninstall', dest='sub_cmd', action='store_const', const=0)

# Create a parser for the "run" command
clap_run = sub_clap.add_parser('run', help='run help')


args = clap.parse_args()

main(args)
# try:
# 	initialize_logger(config['Logging'])
# except ModuleNotFoundError:
# 	pass"""
log = logging.getLogger('root')

@scheduler
def main(app: Application, machine_name: str=my_name):
	if 'Units' not in app.get_focused_form():
		dlg = app.win32.window(class_name="#32770")
		while dlg.exists(1, 0.09):
			dlg.send_keystrokes('{ESC}')
			dlg = app.win32.window(class_name="#32770")
		sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
		while sl_uia.CancelCloseButton.is_enabled():
			sl_uia.CancelCloseButton.click()
			dlg = app.win32.window(class_name="#32770")
			while dlg.exists(1, 0.09):
				dlg.send_keystrokes('{ESC}')
				dlg = app.win32.window(class_name="#32770")
		app.ensure_form('Units')

	serial = mssql.execute("""SELECT SerialNumber FROM PuppetMaster WHERE MachineName = %s""", machine_name)
	if serial:
		for process, unit_type in zip((reason, transact), (ReasonUnit, TransactUnit)):
			try:
				units = unit_type.from_serial_number(serial[0].SerialNumber)
				if units is None:
					continue
			except BI_EntryError:
				continue
			except Exception as ex:
				mssql.execute("""UPDATE PuppetMaster SET SerialNumber = '' WHERE MachineName = %s""", machine_name)
				raise ex
			else:
				log.debug(f"{app}, {units}")
				if units:
					process(app, units)
		else:
			mssql.execute("""UPDATE PuppetMaster SET SerialNumber = '' WHERE MachineName = %s""", machine_name)


if __name__ == '__main__':
	# import urllib.request, urllib.error
	# url = 'http://BLDRSYTE8UT01/IDORequestService/RequestService.aspx'
	# try:
	#     gc = urllib.request.urlopen(url).getcode()
	#     if gc != 200:
	#         raise urllib.error.URLError
	# except urllib.error.URLError:
	#     pass  # Wait for connection
	# else:
	#     pass  # Keep going
	initialize_logger(config['Logging'])

	main.register_schedule(active_time)

	with Application.start(application_filepath) as app:
		def start_func(_app: Application, usr: str, pwd: str):
			"""Run startup procedure"""
			_app.quick_log_in(usr, pwd)

		def end_func(_app: Application):
			"""Run shutdown procedure"""
			_app.quick_log_out()

		main.register_start(start_func, [app, username, password])
		main.register_end(end_func, [app])

		while True:
			main(app)
			sleep(1)

"""else:
	# process_dict = {'transact': Transact.transact, 'reason': Reason.reason, 'scrap': Scrap.scrap}
	process_dict = {}
	clap = argparse.ArgumentParser(prog='BI-Entry')
	clap.add_argument('cmd', choices=list(k for k in process_dict.keys()))
	clap.add_argument('unit_IDs', nargs='+', type=int)
	clap.add_argument('-s', '--speed', type=int, choices=range(3), default=1)
	clap.add_argument('-p', '--pid', type=int, required=True)

	args = clap.parse_args()
	proc = process_dict[args.cmd]
	units = [Unit(i) for i in args.unit_IDs]
	app = Application(args.pid)
	proc(units, app, args.speed)"""
