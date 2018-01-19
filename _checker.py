# coding=utf-8
import pathlib
import os
import subprocess

def check():
	q_path = pathlib.Path("//bldrhome01/DOP/MFG/Josh's Folder/BI_Entry/BIEntry_Installer.exe")
	prog_dir = pathlib.WindowsPath(os.environ["PROGRAMDATA"]) / 'BI_Entry'
	exe_dir = prog_dir / 'bin' / 'exe.win-amd64-3.6' / 'bi_entry.exe'

	if q_path.exists():
		subprocess.run([q_path.as_posix()])
	else:
		os.chdir(prog_dir.as_posix())
		subprocess.run([exe_dir.relative_to(pathlib.Path.cwd()).as_posix()])

if __name__ == '__main__':
	check()
