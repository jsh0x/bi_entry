import json
import os
import pathlib
from typing import Any, Dict, Union


def write_config(obj, directory: Union[str, bytes, os.PathLike]):
	fp = pathlib.WindowsPath(directory) / 'config.json'
	json.dump(obj, fp.open(mode='w+'), indent='\t')


def read_config(directory: Union[str, bytes, os.PathLike]) -> Dict[str, Any]:
	fp = pathlib.WindowsPath(directory) / 'config.json'
	return json.load(fp.open())
