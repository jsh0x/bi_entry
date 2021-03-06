from secrets import choice, randbelow
from string import ascii_letters, digits, punctuation
from typing import Optional, Tuple

"""for i in range(3):
	a = set([])
	while len(a) < 16:
		val = randbelow(78)
		if val > 9:
			a.add(val)
	print(tuple(a))"""


def make_keymap(x1: int, x2: int, x3: int, x4: int, swapped=False) -> dict:
	key_dict = {}
	keybase_set = ((digits, ascii_letters, punctuation),
	               (digits, punctuation, ascii_letters),
	               (ascii_letters, digits, punctuation),
	               (ascii_letters, punctuation, digits),
	               (punctuation, digits, ascii_letters),
	               (punctuation, ascii_letters, digits))
	keypart_set1 = (69, 70, 40, 73,
	                42, 75, 12, 76,
	                17, 18, 19, 20,
	                55, 56, 28, 63)
	keypart_set2 = (68, 36, 38, 71,
	                44, 13, 46, 47,
	                49, 50, 51, 22,
	                57, 60, 61, 30)
	keypart_set3 = (70, 27, 42, 11,
	                43, 45, 13, 15,
	                49, 50, 23, 25,
	                59, 60, 30, 31)
	keybase = keybase_set[x1]
	for key_set, val, base in zip((keypart_set1, keypart_set2, keypart_set3), (x2, x3, x4), keybase):
		if val >= 16:
			val -= 16
			base = base[::-1]
		for i in range(len(base)):
			j = str((i + key_set[val]) * key_set[val])
			if swapped:
				key_dict[int(j)] = base[i]
			else:
				while len(j) < 4:
					char = choice(ascii_letters)
					j = char + j
				key_dict[base[i]] = j
	return key_dict


def encrypt(data: str, key: Optional[str] = None) -> Tuple[str, str]:
	retry = True
	if not key:
		gave_key = False
	else:
		gave_key = True
	while retry:
		if not gave_key:
			key = str(randbelow(6) + 1) + str(randbelow(32)).rjust(2, '0') + str(randbelow(32)).rjust(2, '0') + str(randbelow(32)).rjust(2, '0')
		val1, val2, val3, val4 = int(key[0]) - 1, int(key[1:3]), int(key[3:5]), int(key[5:])
		key_dict = make_keymap(val1, val2, val3, val4)
		if len(key_dict) < 94:
			if gave_key:
				raise ValueError(f"{key} is not a valid key!")
		else:
			retry = False
	retval = ''
	for char in data:
		retval += key_dict[char]
	return retval, key


def decrypt(data: str, key: str) -> str:
	val1, val2, val3, val4 = int(key[0]) - 1, int(key[1:3]), int(key[3:5]), int(key[5:])
	key_dict = make_keymap(val1, val2, val3, val4, swapped=True)
	if len(key_dict) < 94:
		raise ValueError(f"{key} is not a valid key!")
	retval = ''
	for i in range(0, len(data), 4):
		chars = data[i:i + 4]
		for j in range(4):
			if chars[j] in digits:
				break
		retval += key_dict[int(chars[j:])]
	return retval

# import os.urandom


# class HashSlingingSlasher:
# 	def __init__(self):
# 		self._count = 0
#
# 	@property
# 	def _hashit(self):
# 		self._count += 1
# 		blake2b(salt=os.urandom(blake2b.SALT_SIZE))
#
# 	def hashit(self, data1, data2):
# 		h = self._hashit
# 		h.update(data1)
# compare_digest
