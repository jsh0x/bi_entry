# coding=utf-8
from collections import Counter
from typing import Tuple

import numpy as np
from pywinauto.base_wrapper import BaseWrapper


def get_background_color(control: BaseWrapper) -> Tuple[int, int, int]:  # FIXME: JUST FIX IT
	img = control.capture_as_image()
	im = np.array(img)
	assert im.ndim == 3
	counter = Counter([str(tuple(im[y, x])) for y in np.arange(im.shape[0]) for x in np.arange(im.shape[1])])
	retval = counter.most_common(1)[0][0].strip('()').replace(' ', '')
	return tuple(int(n) for n in retval.split(','))


__all__ = ['get_background_color']
