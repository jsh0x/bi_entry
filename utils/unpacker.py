#! python3 -W ignore
# coding=utf-8
import zipfile
import os
# from __init__ import *
import shutil

"""def main():
	path = 'build/exe.win-amd64-3.6/build.zip'
	if my_directory.exists():
		try:
			bin_dir = my_directory / 'bin'
			if bin_dir.exists():
				bin_dir.rename(my_directory / 'bin_OLD')
			config_file = my_directory / 'config.json'
			if config_file.exists():
				os.remove(config_file.as_posix())
			if any([bin_dir.exists(), config_file.exists()]):
				raise FileExistsError()
			with zipfile.ZipFile(path) as myzip:
				myzip.extractall(my_directory.as_posix())
			create_shortcut(name='BI_Entry', exe_path=my_directory / 'bin' / 'exe.win-amd64-3.6' / 'bi_entry.exe', startin=my_directory / 'bin' / 'exe.win-amd64-3.6',
			                icon_path=my_directory / 'bin' / 'exe.win-amd64-3.6' / 'bi_entry.ico')
			if not bin_dir.exists():
				raise FileNotFoundError()
			shutil.rmtree(bin_dir.with_name('bin_OLD').as_posix())
		except Exception as ex:
			bin_dir = my_directory / 'bin_OLD'
			if bin_dir.exists():
				bin_dir.rename(my_directory / 'bin')
			raise ex
	else:
		with zipfile.ZipFile(path) as myzip:
			myzip.extractall(my_directory.as_posix())
		create_shortcut(name='BI_Entry', exe_path=my_directory / 'bin' / 'exe.win-amd64-3.6' / 'bi_entry.exe', startin=my_directory / 'bin' / 'exe.win-amd64-3.6',
		                icon_path=my_directory / 'bin' / 'exe.win-amd64-3.6' / 'bi_entry.ico')
"""