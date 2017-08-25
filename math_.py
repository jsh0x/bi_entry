import datetime
from collections import UserList
from typing import Tuple, Sequence, Iterable
from colorsys import hsv_to_rgb

import numpy as np
from matplotlib import pyplot as plt


class Timer:
	def __init__(self):
		self.start_time = None

	def start(self):
		self.start_time = datetime.datetime.now()

	def lap(self) -> datetime.timedelta:
		return datetime.datetime.now() - self.start_time

	def restart(self) -> datetime.timedelta:
		retval = self.lap()
		self.start()
		return retval


def get_total_reliability(a: np.ndarray) -> float:
	"""Calculates the total reliability as:  Sum(a) * ( Average(a) / StandardDeviation(a) )"""
	x = a.std(dtype=np.float)
	y = a.sum()
	z = a.mean(dtype=np.float)
	if y > 0:
		# print(f'x: {x}\ny: {y}\nz: {z}\nz/x: {np.true_divide(z, x)}\ny*(z/x): {np.multiply(np.true_divide(z, x), y)}')
		return float(np.round(np.multiply(np.true_divide(z, x), y), decimals=3))
	else:
		return 0.000


def power(x1, x2):
	mode = '+'
	if x2 == 0:
		return 1
	elif x2 < 0:
		x2 = np.abs(x2)
		mode = '-'
	retval = np.power(x1, x2)
	if mode == '-':
		return np.reciprocal(float(retval))
	else:
		return retval


def LEARN_TEST():
	# master_list = []
	# time_list = []
	img = []
	mod = 18
	timer = Timer()
	timer.start()
	while len(img) < 25:
		r,g,b = rgb = np.random.randint(1, 17, 3, dtype=np.int32)
		if timer.lap().seconds > 1:
			mod -= 1
			timer.start()
		if len(img) > 0:
			for (r2,g2,b2) in img:
				# print(len(img), np.abs(np.diff([r, r2]))+np.abs(np.diff([g, g2]))+np.abs(np.diff([b, b2])))
				if np.abs(np.diff([r, r2]))+np.abs(np.diff([g, g2]))+np.abs(np.diff([b, b2])) < mod:
					break
			else:
				img.append(rgb)
				time = timer.restart()
				time = time.seconds+(time.microseconds*power(10, -6))
				print(len(img), mod, rgb, time)
				# time_list.append(float(time))
			continue
		else:
			img.append(rgb)
			time = timer.restart()
			time = time.seconds + (time.microseconds * power(10, -6))
			print(len(img), mod, rgb, time)
			# time_list.append(float(time))
	# ml = zip(master_list, ['r', 'g', 'b', 'y'])
	# map(plt.plot, ml)
	# plt.show()
	# plt.plot(master_list[0], 'r-', alpha=0.3)
	# plt.plot(master_list[1], 'g-', alpha=0.3)
	# plt.plot(master_list[2], 'b-', alpha=0.3)
	# plt.plot(master_list[3], 'y-', alpha=0.3)
	# avgR = master_list[0].mean()
	# avgG = master_list[1].mean()
	# avgB = master_list[2].mean()
	# avgY = master_list[3].mean()
	# plt.plot(np.full_like(master_list[0], avgR), 'r')
	# plt.plot(np.full_like(master_list[1], avgG), 'g')
	# plt.plot(np.full_like(master_list[2], avgB), 'b')
	# plt.plot(np.full_like(master_list[3], avgY), 'y')
	# plt.show()
	# quit()
	# time_array = np.array(time_list, dtype=np.float16)
	a = np.array(img, dtype=np.uint16).reshape((5, 5, 3))

	a *= 16
	a = np.asarray(np.where(a == 256, 255, a), dtype=np.uint8)
	plt.imshow(np.dstack([a[..., 2],a[..., 0],a[..., 1]]), cmap='brg')
	plt.show()

# LEARN_TEST()


def rgb_float_to_int(rgb: Sequence[float]) -> Tuple[int, int, int]:
	assert (isinstance(rgb[0], float) and isinstance(rgb[1], float) and isinstance(rgb[2], float) and min(rgb) >= 0. and max(rgb) <= 1.)
	return tuple(np.asarray(np.multiply(np.array(rgb, dtype=np.float), 255), dtype=np.uint8).tolist())


def rgb_int_to_float(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
	assert (isinstance(rgb[0], int) and isinstance(rgb[1], int) and isinstance(rgb[2], int) and min(rgb) >= 0 and max(rgb) <= 255)
	return tuple(np.true_divide(np.array(rgb, dtype=np.float), 255).tolist())


def colorspace_iterator(num: int) -> Iterable[Tuple[int, int, int]]:
	hue = np.linspace(0., 1., num, dtype=np.float)
	# hue = np.array([np.float(str(x)) for x in np.linspace(0., 1., num, dtype=np.float)])
	return map(rgb_float_to_int, map(hsv_to_rgb, *np.vstack((hue, np.ones_like(hue), np.ones_like(hue)))))


def colorspace_transition(start: float, stop: float, num: int):
	assert (isinstance(start, float) and isinstance(stop, float) and isinstance(num, int) and start < stop)
	np.linspace(start, stop, num, dtype=np.float)


# colorspace_iterator(16)
