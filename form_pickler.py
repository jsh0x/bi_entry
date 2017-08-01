import shelve
from forms import Form
import pywinauto as pwn

class PickledForm(pwn.WindowSpecification):
	def __init__(self, window: Form):
		for k, v in window.__dict__.items():
			if k != 'actions':
				self.__setattr__(k, v)

	def __getstate__(self):
		new_state = self.__dict__.copy()
		return new_state

	def __setstate__(self, data):
		self.__dict__ = data

def test(name, form: Form):
	with shelve.open('forms', writeback=True) as db:
		db[name] = PickledForm(form)
