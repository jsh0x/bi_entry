# coding=utf-8
from time import sleep
from typing import List, Tuple

import pyautogui as pag
from PIL import ImageGrab


def get_screen_exact():
	sleep(0.05)
	pag.press('printscreen')
	sleep(0.1)
	return ImageGrab.grabclipboard()


def get_screen_size() -> List[Tuple[int, int]]:
	size1 = get_screen_exact()
	while not size1:
		size1 = get_screen_exact()
	size1 = size1.size
	size2 = ImageGrab.grab().size
	return [size2] * (size1[0] // size2[0])


def count_screens() -> int:
	return len(get_screen_size())


def total_screen_space() -> Tuple[int, int]:
	w = 0
	for scrn in get_screen_size():
		w += scrn[0]
		h = scrn[1]
	return (w, h)


def enumerate_screens() -> List[Tuple[int, int, int, int]]:
	total = total_screen_space()
	step = total[0] // count_screens()
	return [(x, 0, x + step, total[1]) for x in range(0, total[0], step)]


__all__ = ['get_screen_exact', 'get_screen_size', 'count_screens', 'total_screen_space', 'enumerate_screens']
