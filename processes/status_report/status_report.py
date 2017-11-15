# coding=utf-8
import datetime

from _common import Timer, pprint_dict, week_number
from config import *

null_replacer = """UPDATE table_name SET col1 = NULL WHERE col1 = ''"""


timer = Timer.start()


def run(self=None, flags: dict = None):
	default_flags = {'QueuedCount': 100, 'QueuedOldest': 2, 'SkippedQueuedCount': 50, 'SkippedQueuedSerialCount': 10,
	                 'ReasonCount': 100, 'ReasonOldest': 1, 'SkippedReasonCount': 50, 'SkippedReasonSerialCount': 10}
	flags = default_flags if not flags else flags
	results = mssql.execute("""SELECT * FROM
	(SELECT
		 COUNT(Id) AS QueuedCount,
		 COUNT(DISTINCT [Serial Number]) AS QueuedSerialCount,
		 MIN(DateTime) AS QueuedOldest FROM PyComm
	 WHERE Status = 'Queued') q,
	(SELECT
		 COUNT(Id) AS SkippedQueuedCount,
		 COUNT(DISTINCT [Serial Number]) AS SkippedQueuedSerialCount,
		 MIN(DateTime) AS SkippedQueuedOldest FROM PyComm
	 WHERE Status = 'Skipped(Queued)') sq,
	(SELECT
		 COUNT(Id) AS ReasonCount,
		 COUNT(DISTINCT [Serial Number]) AS ReasonSerialCount,
		 MIN(DateTime) AS ReasonOldest FROM PyComm
	 WHERE Status = 'Reason') r,
	(SELECT
		 COUNT(Id) AS SkippedReasonCount,
		 COUNT(DISTINCT [Serial Number]) AS SkippedReasonSerialCount,
		 MIN(DateTime) AS SkippedReasonOldest FROM PyComm
	 WHERE Status = 'Skipped(Reason)') sr""")
	for r in results:
		res = r._asdict()
		for k, v in res.items():
			v = [v, 0]
			if k in flags and v[0] is not None:
				if 'Oldest' in k:
					if 'Skipped' not in k and res['Skipped' + k] is not None:
						v[0] = min(res[k], res['Skipped' + k])
					now = datetime.datetime.today()
					week_now = week_number(now, 'M')
					then = v[0]
					week_then = week_number(then, 'M')
					diff_days = (now - then).days - ((week_now - week_then) * 2)
					if diff_days >= flags[k]:
						v[1] = diff_days - flags[k]
				else:
					if 'Skipped' not in k and res['Skipped' + k] is not None:
						v[0] = res[k] + res['Skipped' + k]
					if v[0] >= flags[k]:
						v[1] = v[0] - flags[k]
			else:
				if 'Skipped' not in k and res['Skipped' + k] is not None and res[k] is not None:
					v[0] = res[k] + res['Skipped' + k]
			res[k] = tuple(v)
		pprint_dict(res, 1, 1)


run()

