import numpy as np


def get_total_reliability(a: np.ndarray) -> float:
	"""Calculates the total reliability as:  Sum(a) * ( Average(a) / StandardDeviation(a) )"""
	x = a.std(dtype=np.float32)
	y = a.sum()
	z = a.mean(dtype=np.float32)
	return float(np.round(np.multiply(np.true_divide(z, x), y), decimals=3))
