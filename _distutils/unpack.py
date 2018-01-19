#! python3 -W ignore
# coding=utf-8
import zipfile
import os
import shutil
import re
import pathlib
from win32com.client import Dispatch
import subprocess

def create_shortcut(name: str, exe_path, startin, icon_path):
	shell = Dispatch('WScript.Shell')
	# shortcut_file = pathlib.WindowsPath.home() / 'Desktop' / name + '.lnk'
	home = pathlib.WindowsPath.home()
	desktop = tuple(home.glob('./Desktop'))[0] if tuple(home.glob('./Desktop')) else None
	assert desktop is not None
	shortcut_file = desktop / (name + '.lnk')
	exe_path = exe_path.as_posix() if issubclass(type(exe_path), pathlib.Path) else exe_path
	startin = startin.as_posix() if issubclass(type(startin), pathlib.Path) else startin
	icon_path = icon_path.as_posix() if issubclass(type(icon_path), pathlib.Path) else icon_path
	shortcut = shell.CreateShortCut(shortcut_file.as_posix())
	shortcut.Targetpath = exe_path
	shortcut.WorkingDirectory = startin
	shortcut.IconLocation = icon_path
	shortcut.save()

def compare_versions(v1: str, v2: str):
	v1_score = sum([int(v1.split('.')[i]) * (10 ** (2 - i)) for i in range(3)])
	v2_score = sum([int(v2.split('.')[i]) * (10 ** (2 - i)) for i in range(3)])
	if v1_score == v2_score:
		if (v1.count('.') == 3) and (v2.count('.') == 2):
			return v2
		elif (v1.count('.') == 2) and (v2.count('.') == 3):
			return v1
		elif (v1.count('.') == 3) and (v2.count('.') == 3):
			v1_score += int(v1.split('.')[3])
			v2_score += int(v2.split('.')[3])
			if v1_score > v2_score:
				return v1
			else:
				return v2
		elif (v1.count('.') == 2) and (v2.count('.') == 2):
			return v2
		else:
			raise ValueError
	elif v1_score > v2_score:
		return v1
	else:
		return v2

def unpack_it():
	prog_dir = pathlib.WindowsPath(os.environ["PROGRAMDATA"]) / 'BI_Entry'
	path = 'build/exe.win-amd64-3.6/src.zip'
	vers_dir = prog_dir / 'bin' / 'lib' / '__version__.py'

	def extract_it():
		with zipfile.ZipFile(path) as myzip:
			myzip.extractall(prog_dir.as_posix())
		create_shortcut(name='BI_Entry', exe_path=prog_dir / 'bin' / 'exe.win-amd64-3.6' / 'checker.exe', startin=prog_dir / 'bin' / 'exe.win-amd64-3.6',
		                icon_path=prog_dir / 'bin' / 'exe.win-amd64-3.6' / 'bi_entry.ico')

	def get_version():
		with zipfile.ZipFile(path) as myzip:
			with myzip.open('bin/lib/__version__.py') as myfile:
				_vers = myfile.read()
			for line in _vers.splitlines():
				if b'full_version = ' in line:
					full_v = re.search(r"'(.*)'", line.decode('utf-8')).group().strip("'")
				elif b'short_version = ' in line:
					short_v = re.search(r"'(.*)'", line.decode('utf-8')).group().strip("'")
				elif b'release = ' in line:
					if b'True' in line:
						return short_v
					else:
						return full_v
				

	def update_it():
		bin_dir = prog_dir / 'bin'
		config_file = prog_dir / 'config.json'
		try:
			if bin_dir.exists():
				bin_dir.rename(prog_dir / 'bin_OLD')
			if config_file.exists():
				os.remove(config_file.as_posix())  # TODO: Handle overwriting old configs, ie maintaining data continuity where relevant
			if any([bin_dir.exists(), config_file.exists()]):
				raise FileExistsError()
			extract_it()
			if not bin_dir.exists():
				raise FileNotFoundError()
			try:
				shutil.rmtree(bin_dir.with_name('bin_OLD').as_posix())
			except Exception:
				pass
		except Exception as ex:
			bin_dir = prog_dir / 'bin_OLD'
			if bin_dir.exists():
				bin_dir.rename(prog_dir / 'bin')
			raise ex

	my_vers = get_version()

	if vers_dir.exists():
		match = None
		vers = vers_dir.read_text()
		for line in vers.splitlines():
			if 'full_version = ' in line:
				full_v = re.search(r"'(.*)'", line).group().strip("'")
			elif 'short_version = ' in line:
				short_v = re.search(r"'(.*)'", line).group().strip("'")
			elif 'release = ' in line:
				if 'True' in line:
					match = short_v
				else:
					match = full_v
		if compare_versions(match, my_vers) != match:
			update_it()
	elif prog_dir.exists():
		update_it()
	else:
		extract_it()
	startin = prog_dir / 'bin'
	os.chdir(startin.as_posix())
	subprocess.run((prog_dir / 'bin' / 'exe.win-amd64-3.6' / 'bi_entry.exe').relative_to(pathlib.Path.cwd()).as_posix())

if __name__ == '__main__':
	unpack_it()
