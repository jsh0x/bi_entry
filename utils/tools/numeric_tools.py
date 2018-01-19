# coding=utf-8
from typing import Sequence, Tuple, Union, List


def just_over_half(y: int, x: int = None) -> float:
	# language=rst
	"""Input: :math:`x`, Output: :math:`z`
:math:`1<x<\infty`,
:math:`y=2^x`,
:math:`z = \frac{\frac{y}{2}+1}y`"""

	if x is None:
		x = y
		y = 1
	assert x > 1
	base = 2 ** x
	half_base = base / 2
	return y * ((half_base + 1) / base)


def normalize_numeric_range(r: Union[range, Sequence[int], Sequence[range]]) -> List[int]:
	retval = []
	for x in r:
		if isinstance(x, int):
			retval.append(x)
		elif isinstance(x, range):
			for y in x:
				retval.append(y)
		elif isinstance(x, (tuple, list, set)):
			retval += normalize_numeric_range(x)
	else:
		return sorted(set(retval))


def combine_ranges(ranges: Sequence[range]) -> Tuple[int, ...]:
	return tuple(sorted(set([y for x in ranges for y in x])))


# noinspection SpellCheckingInspection
def sigfig(template, x):
	x_str, y_str = map(str, [template, x])
	x_len = len(x_str.split('.', 1)[1].strip())
	y_sub1, y_sub2 = y_str.split('.', 1)
	y_sub2 = y_sub2.ljust(x_len, '0')
	y_new = eval(f"{y_sub1}.{y_sub2[:x_len]}")
	if len(y_sub2) > x_len and eval(y_sub2[x_len]) >= 5:
		val = 10 ** x_len
		y_new = ((y_new * val) + 1) / val
	return y_new


# noinspection SpellCheckingInspection
__all__ = ['sigfig', 'just_over_half', 'combine_ranges', 'normalize_numeric_range']
