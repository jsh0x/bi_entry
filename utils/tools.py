# coding=utf-8
from collections import Counter
from typing import Tuple
import datetime

import numpy as np
from pywinauto.base_wrapper import BaseWrapper


def prepare_string(text: str, strip_chars: str = None, *, remove_all_whitespace: bool = False) -> str:  # THINK: Maybe as decorator?
	if text is None:
		return text
	strip_chars = ' ' if strip_chars is None else strip_chars + ' '
	text = text.strip(strip_chars)
	if remove_all_whitespace:
		while ' ' in text:
			text = text.replace(' ', '')
	if not text:
		return None
	return text


def get_background_color(control: BaseWrapper) -> Tuple[int, int, int]:
	img = control.capture_as_image()
	im = np.array(img)
	assert im.ndim == 3
	counter = Counter([str(tuple(im[y, x])) for y in np.arange(im.shape[0]) for x in np.arange(im.shape[1])])
	retval = counter.most_common(1)[0][0].strip('()').replace(' ', '')
	return tuple(int(n) for n in retval.split(','))


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


def fix_isoweekday(dt) -> int:
	val = dt.isoweekday()
	mod = (val // 7) * 7
	return val - mod


def log_friendly_string(text: str) -> str:
	while ('\r' in text) or ('\n' in text) or ('\t' in text):
		text = text.replace('\r', '')
		text = text.replace('\n', '')
		text = text.replace('\t', '')
	else:
		return text


# TODO: TA Login
# https://ta.bi.com/
"""
<body>
	<form name="loginForm" class="loginForm" id="loginForm" onsubmit="javascript:return WebForm_OnSubmit();" action="./login.aspx" method="post">
        <div id="centeredDiv">
            <div id="body">
                <div id="loginbox">
                    <div class="loginRow" id="loginUsername">
                        <label>User Name:</label>
                        <input name="logAppLogin$UserName" tabindex="1" class="inputF" id="logAppLogin_UserName" type="text">
                        <span class="val" id="logAppLogin_UserNameRequired" style="color: red; visibility: hidden;">*</span>
                    </div>
                    <div class="loginRow" id="loginPassword">
                        <label>Password:</label>
                        <input name="logAppLogin$Password" tabindex="2" class="inputF" id="logAppLogin_Password" type="password">
                        <span class="val" id="logAppLogin_PasswordRequired" style="color: red; visibility: hidden;">*</span>
                    </div>
                    <div class="loginRow">
                        <input name="logAppLogin$Login" tabindex="4" class="loginBtn" id="logAppLogin_Login" style="border-width: 0px;" onmousedown="src='Image/Login-button-p.png'" onmouseup="src='Image/Login-button.png'" onclick='javascript:WebForm_DoPostBackWithOptions(new WebForm_PostBackOptions("logAppLogin$Login", "", true, "", "", false, false))' type="image" src="Image/Login-button.png" text="Login">
                    </div>
                </div>
            </div>
        </div>
	</form>
</body>
"""
