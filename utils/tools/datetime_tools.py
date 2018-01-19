# coding=utf-8
import datetime


def date_string(dt: datetime.datetime, century: bool = False) -> str:
	return dt.strftime("%m/%d/%Y") if century else dt.strftime("%m/%d/%y")


def time_string(dt: datetime.datetime, military: bool = True) -> str:
	return dt.strftime("%H:%M:%S") if military else dt.strftime("%I:%M:%S %p")


def week_number(dt: datetime.datetime, start: str = 'S') -> int:
	values = {'M': 0, 'S': 1}
	start = start.upper()
	if start not in values:
		raise ValueError()  # TODO: Specify error
	return int(dt.strftime("%U")) if values[start] else int(dt.strftime("%W"))


def weekday_string(dt: datetime.datetime, abbreviated: bool = True) -> str:
	return dt.strftime("%a") if abbreviated else dt.strftime("%A")


def month_string(dt: datetime.datetime, abbreviated: bool = True) -> str:
	return dt.strftime("%b") if abbreviated else dt.strftime("%B")


def fix_isoweekday(dt) -> int:
	val = dt.isoweekday()
	mod = (val // 7) * 7
	return val - mod


__all__ = ['time_string', 'week_number', 'weekday_string', 'month_string', 'fix_isoweekday']
