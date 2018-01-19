# coding=utf-8
import compileall, pathlib

def compile_it():
	# Compiles the sourcecode
	for f in pathlib.Path.cwd().glob('*.py'):
		compileall.compile_file(f, force=True)
	compileall.compile_dir(pathlib.Path.cwd() / 'processes', force=True)
	compileall.compile_dir(pathlib.Path.cwd() / 'utils', force=True)
	compileall.compile_dir(pathlib.Path.cwd() / 'core', force=True)
	compileall.compile_dir(pathlib.Path.cwd() / 'config', force=True)

__all__ = ['compile_it']
