# coding=utf-8
import os, pathlib, typing
from win32com.client import Dispatch


Filepath = typing.Union[str, bytes, os.PathLike, pathlib.Path]

def normalize_filepath(fp: Filepath) -> pathlib.Path:
	return pathlib.Path(str(fp))

def find_file(name, path="C:/") -> Filepath:
	for root, dirs, files in os.walk(path):
		if name in files:
			return normalize_filepath(str(os.path.join(root, name)).replace('\\', '/'))
	else:
		return None

def find_SyteLine() -> Filepath:
	path = pathlib.WindowsPath.home() / 'AppData' / 'Local' / 'Apps'
	res = [i for i in path.rglob('winstudio.exe') if i.parent.name.startswith('sl8') and '_none_' not in i.parent.name]
	if res:
		return normalize_filepath(res[0])
	else:
		return None

def create_shortcut(name: str, exe_path:Filepath, startin: Filepath, icon_path: Filepath):
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

__all__ = ['Filepath', 'normalize_filepath', 'find_SyteLine', 'find_file', 'create_shortcut']
