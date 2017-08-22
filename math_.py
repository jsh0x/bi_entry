import datetime

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
	x = a.std(dtype=np.float32)
	y = a.sum()
	z = a.mean(dtype=np.float32)
	return float(np.round(np.multiply(np.true_divide(z, x), y), decimals=3))


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