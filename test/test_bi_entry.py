import unittest
import bi_entry
import itertools
from string import ascii_uppercase as letters
from commands import Application
from _crypt import decrypt
import datetime


class TestTimer:
	def __init__(self):
		self._start_time = None

	def start(self):
		self._start_time = datetime.datetime.now()

	def lap(self):
		if self._start_time:
			retval = datetime.datetime.now() - self._start_time
			return retval
		else:
			print(None)
			return None

	def reset(self):
		self._start_time = None

	def stop(self):
		retval = self.lap()
		self.reset()
		return retval
timer = TestTimer()


class MyTestCase(unittest.TestCase):
	def test_grid_times(self):
		usr = 'jredding'
		pwd = '75268094752664615822V209t1437070'
		crypt_key = '6170319'
		fp = 'C:/Users/mfgpc00/AppData/Local/Apps/2.0/QQC2A2CQ.YNL/K5YT3MK7.VDY/sl8...ient_002c66e0bc74a4c9_0008.0003_1fdd36ef61625f38/WinStudio.exe'

		timer.start()
		bi_entry.main(('bi_entry.py', 'dev', usr, pwd, '-fp', fp, '-k', crypt_key))
		time2 = timer.stop()

		timer.start()
		bi_entry.main(('bi_entry.py', 'reason', usr, pwd, '-fp', fp, '-k', crypt_key))
		time1 = timer.stop()

		self.assertGreater(time1, time2)

		print(f"Results:"
		      f"\n          Standard Method: {time1}"
		      f"\n      CF Threading Method: {time2}")

# class MyTestCase2(unittest.TestCase):
# 	def test_do(self):
# 		for i in range(4, 9):
# 			psbl = letters[:i]
# 			for length in range(2, 5):
# 				print(f"Chars: {psbl}, Length: {length}")
# 				timer.start()
# 				val1 = []
# 				for val in itertools.product(psbl, repeat=length):
# 					val1.append(val)
# 				t1 = timer.stop()
#
# 				timer.start()
# 				val2 = []
# 				for val in itertools.permutations(psbl, length):
# 					val2.append(val)
# 				t2 = timer.stop()
#
# 				timer.start()
# 				val3 = []
# 				for val in itertools.combinations(psbl, length):
# 					val3.append(val)
# 				t3 = timer.stop()
#
# 				timer.start()
# 				val4 = []
# 				for val in itertools.combinations_with_replacement(psbl, length):
# 					val4.append(val)
# 				t4 = timer.stop()
# 				print(f"\n                        Product: {len(val1)} - {t1}      ~{np.true_divide(len(val1), t1.seconds)} result(s) per second"
# 				      f"\n                   Permutations: {len(val2)} - {t2}      ~{np.true_divide(len(val2), t2.seconds)} result(s) per second"
# 				      f"\n                   Combinations: {len(val3)} - {t3}      ~{np.true_divide(len(val3), t3.seconds)} result(s) per second"
# 				      f"\n    Combinations w/ replacement: {len(val4)} - {t4}      ~{np.true_divide(len(val4), t4.seconds)} result(s) per second"
# 				      f"\n\n")

if __name__ == '__main__':
	unittest.main()
