import re


# - - - - - - - - - - - - - - - - - - - - REGEX - - - - - - - - - - - - - - - - - - - - -
REGEX_USER_SESSION_LIMIT = re.compile(r"session count limit")
REGEX_PASSWORD_EXPIRE = re.compile(r"password will expire")
REGEX_INVALID_LOGIN = re.compile(r"user ?name.*password.*invalid")
REGEX_REPLACE_SESSION = re.compile(r"(?im)session .* user '(?P<user>\w+)' .* already exists(?s:.*)[\n\r](?P<question>.+\?)")
REGEX_WINDOW_MENU_FORM_NAME = re.compile(r"^\d+ (?P<name>[\w* ?]+\w*) .*")
REGEX_ROW_NUMBER = re.compile(r"^Row (?P<row_number>\d+)")
REGEX_SAVE_CHANGES = re.compile(r"save your changes to")
REGEX_CREDIT_HOLD = re.compile(r".*Credit Hold is Yes.*\[Customer: *(?P<customer>\d+)\].*")
REGEX_NEGATIVE_ITEM = re.compile(r"On Hand is -(?P<quantity>\d+)\.0+.*\[Item: (?P<item>\d+-\d{2}-\d{5}-\d+)\].*\[Location: (?P<location>[a-zA-Z0-9_-]+)\]")
REGEX_SQL_DATE = re.compile(r"(?P<year>\d{4})[/-](?P<month>[01]\d)[/-](?P<day>[0-3]\d)")
REGEX_SQL_TIME = re.compile(r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})(?:\.(?P<microsecond>\d+))?")
REGEX_BUILD = re.compile(r"(?P<prefix>[A-Z]{2})-(?P<build>\d{3}(?P<carrier>[VS])?)(?:-(?P<suffix>M|DEMO|R|T))?")
REGEX_BUILD_ALT = re.compile(r"(?P<prefix>[A-Z]{2})-(?P<build>(?P<carrier>\d)\d{3})(?:-(?P<suffix>M|DEMO|R|T))?")

REGEX_RESOLUTION = re.compile(r"(?P<general>\d+),(?P<specific>\d+)")


# - - - - - - - - - - - - - - - - - - - - COMMON  - - - - - - - - - - - - - - - - - - - -
# noinspection SpellCheckingInspection
# language=RegExp
SYTELINE_WINDOW_TITLE = r'Infor ERP SL \(EM\).*'


CELLULAR_BUILDS = ('EX-600-M', 'EX-625S-M', 'EX-600-T', 'EX-600', 'EX-625-M', 'EX-600-DEMO', 'EX-600S', 'EX-600S-DEMO', 'EX-600V-M',
						'EX-600V', 'EX-680V-M', 'EX-600V-DEMO', 'EX-680V', 'EX-680S', 'EX-680V-DEMO', 'EX-600V-R', 'EX-680S-M', 'HG-2200-M',
						'CL-4206-DEMO', 'CL-3206-T', 'CL-3206', 'CL-4206', 'CL-4206', 'CL-3206-DEMO', 'CL-4206-M', 'CL-3206-M', 'HB-110',
						'HB-110-DEMO', 'HB-110-M', 'HB-110S-DEMO', 'HB-110S-M', 'HB-110S', 'LC-800V-M', 'LC-800S-M', 'LC-825S-M', 'LC-800V-DEMO',
						'LC-825V-M', 'LC-825V-DEMO', 'LC-825V', 'LC-825S', 'LC-825S-DEMO', 'LC-800S-DEMO')

# noinspection SpellCheckingInspection
SUFFIX_DICT = {'M': 'Monitoring', 'R': 'Refurb',
               'T': 'Trial', 'DEMO': 'Demo', '-': 'Direct'}

CARRIER_DICT = {'V': 'Verizon', 'S': 'Sprint', '-': None,
                '3': 'Verizon', '4': 'Sprint', '2': None}
"""import decimal
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
# terrain, binary, coolwarm, gist_earth, Blues
# {cmap} + _r = reversed


class AdvancedDecimal:
	def __init__(self, x, prec: int=9):
		self.c = decimal.Context(prec, rounding=decimal.ROUND_HALF_UP)
		self._x = decimal.Decimal(float(x), self.c).normalize(self.c)

	@property
	def x(self):
		return decimal.Decimal(self._x, self.c).normalize(self.c)

	@x.setter
	def x(self, value):
		self._x = decimal.Decimal(value, self.c).normalize(self.c)

	def __repr__(self):
		return repr(self.x)

	def __str__(self):
		return str(self.x)

	def __int__(self):
		return int(self.x)

	def __float__(self):
		return float(self.x)

	def __add__(self, other):
		return float((self.x + decimal.Decimal(other, self.c)).normalize(self.c))

	def __sub__(self, other):
		return float((self.x - decimal.Decimal(other, self.c)).normalize(self.c))

	def __mul__(self, other):
		return float((self.x * decimal.Decimal(other, self.c)).normalize(self.c))

	def __truediv__(self, other):
		return float((self.x / decimal.Decimal(other, self.c)).normalize(self.c))

	def __floordiv__(self, other):
		return float((self.x // decimal.Decimal(other, self.c)).normalize(self.c))

	def __mod__(self, other):
		return float((self.x % decimal.Decimal(other, self.c)).normalize(self.c))

	def __pow__(self, power, modulo=None):
		return float(decimal.Decimal(float(self.x) ** power, self.c).normalize(self.c))

	def __iadd__(self, other):
		self.x = (self.x + decimal.Decimal(other, self.c)).normalize(self.c)
		return self

	def __isub__(self, other):
		self.x = (self.x - decimal.Decimal(other, self.c)).normalize(self.c)
		return self

	def __imul__(self, other):
		self.x = (self.x * decimal.Decimal(other, self.c)).normalize(self.c)
		return self

	def __itruediv__(self, other):
		self.x = (self.x / decimal.Decimal(other, self.c)).normalize(self.c)
		return self

	def __ifloordiv__(self, other):
		self.x = (self.x // decimal.Decimal(other, self.c)).normalize(self.c)
		return self

	def __imod__(self, other):
		self.x = (self.x % decimal.Decimal(other, self.c)).normalize(self.c)
		return self

	def __ipow__(self, power, modulo=None):
		self.x = decimal.Decimal(float(self.x) ** power, self.c).normalize(self.c)
		return self


class ExtendedArray:
	def __init__(self, a: np.ndarray, h: float, rando: float=1.0):
		assert 0.0 <= h <= 1.0
		self.array = self.check_shape(a)
		self.H = h
		self._rando = rando
		self.passes = 0

	@property
	def rando(self):
		rando_range = self._rando
		for i in range(self.passes):
			rando_range *= np.power(2, -self.H)
		val = AdvancedDecimal(np.random.random_integers(-int(rando_range*10), int(rando_range*10)))
		return val / 10

	@classmethod
	def ones(cls, size_factor: int, h: float, rando: float=1.0):
		sizes = {(2 ** x) + 1 for x in range(2, 11)}
		size = (2 ** size_factor) + 1
		assert size in sizes
		return cls(np.ones((size, size)), h, rando)

	@classmethod
	def zeros(cls, size_factor: int, h: float, rando: float=1.0):
		sizes = {(2 ** x) + 1 for x in range(2, 11)}
		size = (2 ** size_factor) + 1
		assert size in sizes
		return cls(np.zeros((size, size)), h, rando)

	@staticmethod
	def center(a: np.ndarray):
		return [x // 2 for x in a.shape[:2]]

	@staticmethod
	def check_shape(a: np.ndarray) -> np.ndarray:
		if a.shape[0] != a.shape[1]:
			a = a.reshape((np.sqrt(a.size), np.sqrt(a.size)))
		dim = np.log2(a.shape[0]-1)
		assert not dim % int(dim)
		return a

	def diamond_step(self, a: np.ndarray):
		cy, cx = self.center(a)
		corners = ((0, 0), (0, -1), (-1, 0), (-1, -1))
		corner_sum = AdvancedDecimal(sum(a[y, x] for x, y in corners))
		corner_avg = corner_sum / 4
		a[cy, cx] = float(self.rando + corner_avg)
		return a

	def square_step(self, a: np.ndarray):
		cy, cx = self.center(a)
		coords = [(((0, 0), (-1, 0), (cx, cy)), (cx, 0)),
		          (((0, 0), (0, -1), (cx, cy)), (0, cy)),
		          (((0, -1), (-1, -1), (cx, cy)), (cx, -1)),
		          (((-1, 0), (-1, -1), (cx, cy)), (-1, cy))]
		for corners, (cx, cy) in coords:
			corner_sum = AdvancedDecimal(sum(a[y, x] for x, y in corners))
			corner_avg = corner_sum / 3
			a[cy, cx] = float(self.rando + corner_avg)
		return a

	def subdivide(self):
		n = 4 ** self.passes
		side_count = np.sqrt(n)
		# print("Side count:", side_count)
		# print("Edge length:", self.array.shape[0] - 1)
		step = int((self.array.shape[0] - 1) / side_count)
		# print("Step:", step+1)
		rando_range = self._rando
		for i in range(self.passes):
			rando_range *= np.power(2, -self.H)
		# print("Rando range:", rando_range)
		count = 0
		if step < 2:
			return False
		for y in np.arange(0, self.array.shape[0] - 1, step):
			for x in np.arange(0, self.array.shape[1] - 1, step):
				# print(x, x+step+1, y, y+step+1)
				a = self.array[y:y + step + 1, x:x + step + 1].view()
				self.diamond_step(a)
				self.square_step(a)
				# a = self.array[y:y + step+1, x:x + step+1].copy()
				# a = self.diamond_step(a)
				# self.array[y:y + step + 1, x:x + step + 1] = self.square_step(a)
				count += 1
		# print(count)
		# print()
		self.passes += 1
		return True

	def recursive_subdivide(self):
		res = True
		while res:
			res = self.subdivide()

	def show(self):
		fig, (ax1, ax2) = plt.subplots(2, 1)
		ax1.imshow(self.array, cmap='viridis')
		ax2.imshow(self.array, cmap='viridis_r')
		plt.show()


# vals = np.linspace(1.0, 0.0, 25)
# factors = range(3, 11)
# total = len(list(factors))
# for j,f in enumerate(factors):
# 	fig, ((ax1, ax2, ax3, ax4, ax5),
# 	      (ax6, ax7, ax8, ax9, ax10),
# 	      (ax11, ax12, ax13, ax14, ax15),
# 	      (ax16, ax17, ax18, ax19, ax20),
# 	      (ax21, ax22, ax23, ax24, ax25)) = plt.subplots(5, 5, sharex=True, sharey=True)
# 	fig.suptitle(f"Size: {(2 ** f) + 1}x{(2 ** f) + 1}  ({j+1}/{total})", fontsize=12)
# 	fig.subplots_adjust(left=None, bottom=None, right=None, top=None)
# 	axes = [ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9, ax10,
# 	        ax11, ax12, ax13, ax14, ax15, ax16, ax17, ax18, ax19, ax20,
# 	        ax21, ax22, ax23, ax24, ax25]
# 	for i,(v,ax) in enumerate(zip(vals, axes)):
# 		# ar = ExtendedArray(7, v)
# 		ar = ExtendedArray.ones(f, v)
# 		ar.recursive_subdivide()
# 		ax.set_title(f"Roughness Constant: {AdvancedDecimal(v, 3)}", fontsize=6)
# 		ax.tick_params(axis='both', bottom='off', right='off', left='off', top='off', labelbottom='off', labelright='off', labelleft='off', labeltop='off')
# 		ax.imshow(ar.array, cmap='binary')
# 	plt.show()

# --- Custom colormaps ---
cdict1 = {'red':   ((0.0,  0.0, 0.0),
                    (0.5,  1.0, 1.0),
                    (1.0,  1.0, 1.0)),

          'green': ((0.0,  0.0, 0.0),
                    (0.25, 0.0, 0.0),
                    (0.75, 1.0, 1.0),
                    (1.0,  1.0, 1.0)),

          'blue':  ((0.0,  0.0, 0.0),
                    (0.5,  0.0, 0.0),
                    (1.0,  1.0, 1.0))}

red = np.linspace(0.0, 1.0, 64)
green = np.linspace(0.0, 1.0, 64)
blue = np.linspace(0.0, 1.0, 64)
rgb = np.array([(1.0, g, 0.0) for g in green] + [(1.0-r, 1.0, 0.0) for r in red] + [(0.0, 1.0, b) for b in blue] + [(0.0, 1.0-g, 1.0) for g in green] + [(r, 0.0, 1.0) for r in red] + [(1.0, 0.0, 1.0-b) for b in blue])

hlf = rgb.shape[0]/2
thd = rgb.shape[0]/3
qrt = rgb.shape[0]/4
oct = rgb.shape[0]/8
hpt = rgb.shape[0]/10
hx_ = rgb.shape[0]/16
color = np.array([(1.0, 0.0, 0.0), (1.0, 0.5, 0.5), (0.5, 0.0, 0.0),
                  (1.0, 0.25, 0.0), (1.0, 0.5, 0.0), (0.75, 0.5, 0.0), (1.0, 0.75, 0.0), (1.0, 1.0, 0.0), (1.0, 1.0, 0.5), (0.5, 0.5, 0.0),
                  (0.5, 1.0, 0.0), (0.0, 1.0, 0.0), (0.5, 1.0, 0.5), (0.0, 0.5, 0.0), (0.0, 0.5, 0.5), (0.0, 0.5, 1.0), (0.0, 0.0, 1.0), (0.5, 0.5, 1.0), (0.0, 0.0, 0.5), (0.0, 0.5, 0.5)]).reshape((20, 1, 3))
color2 = np.hstack((color, color, color, color, color, color, color, color))
plt.imshow(color2)
plt.show()
quit()
rgb = rgb.reshape((384, 1, 3))
a = np.hstack((rgb, rgb, rgb, rgb, rgb, rgb, rgb, rgb))
plt.imshow(a)
plt.show()
quit()
# blue_red2 = LinearSegmentedColormap('BlueRed2', cdict2)
# plt.register_cmap(cmap=blue_red2)
plt.register_cmap(name='BlueRed3', data=cdict1)

h = 0.958
arr = ExtendedArray.ones(7, h)
arr.recursive_subdivide()
mx = arr.array.max()
mn = arr.array.min()
for diff in np.linspace(mn, mx, 9):
	fig, ((ax1, ax2, ax3), (ax4, ax5, ax6)) = plt.subplots(2, 3, sharex=True, sharey=True)
	diff = float(AdvancedDecimal(diff, 5))
	mn2 = diff + mn
	mx2 = mx - diff
	arr2 = np.where(arr.array <= mx2, 1, arr.array)
	arr3 = np.where(arr.array >= mn2, 0, arr.array)
	arr4 = np.where(arr.array >= mx2, 1, arr.array)
	arr5 = np.where(arr.array <= mn2, 0, arr.array)
	fig.suptitle(f"Threshold: {diff}", fontsize=12)
	fig.subplots_adjust(left=0.02, bottom=0.02, right=0.98, top=0.88, wspace=0.00, hspace=0.00)
	ax1.imshow(arr.array, cmap='binary_r')
	ax2.imshow(arr2, cmap='binary_r')
	ax3.imshow(arr3, cmap='binary_r')
	ax4.imshow(arr4, cmap='binary_r')
	ax5.imshow(arr5, cmap='binary_r')
	ax6.imshow(arr.array, cmap='tab20')
	ax1.tick_params(axis='both', bottom='off', right='off', left='off', top='off', labelbottom='off', labelright='off', labelleft='off', labeltop='off')
	ax2.tick_params(axis='both', bottom='off', right='off', left='off', top='off', labelbottom='off', labelright='off', labelleft='off', labeltop='off')
	ax3.tick_params(axis='both', bottom='off', right='off', left='off', top='off', labelbottom='off', labelright='off', labelleft='off', labeltop='off')
	ax4.tick_params(axis='both', bottom='off', right='off', left='off', top='off', labelbottom='off', labelright='off', labelleft='off', labeltop='off')
	ax5.tick_params(axis='both', bottom='off', right='off', left='off', top='off', labelbottom='off', labelright='off', labelleft='off', labeltop='off')
	ax6.tick_params(axis='both', bottom='off', right='off', left='off', top='off', labelbottom='off', labelright='off', labelleft='off', labeltop='off')
	plt.show()
# tab20, Set1

# arr.show()
# 1.0, 0.958, 0.917, 0.875, 0.833"""