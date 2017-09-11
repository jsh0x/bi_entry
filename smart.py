import datetime
import calendar
import sqlite3
import operator
from collections import defaultdict
from colorsys import hsv_to_rgb, rgb_to_hsv

from matplotlib import pyplot as plt
from matplotlib import gridspec
import numpy as np

from _sql import MS_SQL
from _crypt import decrypt


_assorted_lengths_of_string = ('30803410313510753080335510753245107531353410',
                              '474046203600486038404260432039003960',
                              '63004620S875486038404260S875432039003960',
                              '58803900396063004620360048603840426038404620',
                              '1121327')
_adr_data, _usr_data, _pwd_data, _db_data, _key = _assorted_lengths_of_string
mssql = MS_SQL(address=decrypt(_adr_data, _key), username=decrypt(_usr_data, _key), password=decrypt(_pwd_data, _key), database=decrypt(_db_data, _key))
dt_start = datetime.datetime.strptime('01/01/17 12:00:00 AM', '%m/%d/%y %I:%M:%S %p')


# def convert_array(value: bytes) -> np.ndarray:
# 	return array_splicer(bytes.decode(value, encoding='utf-8'), mode='join')
# def adapt_array(value: np.ndarray) -> bytes:
# 	return bytes(array_splicer(value, mode='split'), encoding='utf-8')
# sqlite3.register_adapter(np.ndarray, adapt_array)
# sqlite3.register_converter('ARRAY', convert_array)
conn = sqlite3.connect(database='smart.db', detect_types=sqlite3.PARSE_DECLTYPES)
c = conn.cursor()
# c.execute("DROP TABLE statistics")
# conn.commit()
c.execute("CREATE TABLE IF NOT EXISTS statistics("
          "Id INTEGER PRIMARY KEY, "
          "MinuteHour INTEGER, "
          "HourDay INTEGER, "
          "DayMonth INTEGER, "
          "WeekMonth INTEGER, "
          "MonthYear INTEGER, "
          "Year INTEGER, "
          "DayWeek INTEGER, "
          "DayYear INTEGER, "
          "WeekYear INTEGER, "
          "SeasonYear INTEGER, "
          "Product TEXT, "
          "Operation TEXT, "
          "Operator TEXT, "
          "Resolution TEXT"
          ")")
conn.commit()

def main():
	dt_current = dt_start
	dt_temp = datetime.datetime.strptime('09/01/17 12:00:00 AM', '%m/%d/%y %I:%M:%S %p')
	# while dt_current < dt_temp:  # datetime.datetime.now():
	# 	dt_future = dt_current + datetime.timedelta(hours=1.)
	# 	data = mssql.execute(f"SELECT [Product],[Operation],[Operator],[Resolution],[DateTime] FROM Operations WHERE [DateTime] >= '{dt_current}' AND [DateTime] < '{dt_future}'", fetchall=True)
	# 	if data:
	# 		for  product, operation, operator, resolution, dt_data in data:
	# 			mh, hd, dm, wm, my, y, dw, dy, wy, sy = [int(x) for x in (dt_data.strftime('%M,%H,%d,')+f"{int(dt_data.strftime('%U'))-(4*(int(dt_data.strftime('%U'))//4))},"+dt_data.strftime('%m,%Y,%w,%j,%W,')+f"{(int(dt_data.strftime('%m'))-1)//4}").split(',')]
	# 			c.execute("INSERT INTO statistics(MinuteHour, HourDay, DayMonth, WeekMonth, MonthYear, Year, DayWeek, DayYear, WeekYear, SeasonYear, Product, Operation, Operator, Resolution) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
	# 			          (mh, hd, dm, wm, my, y, dw, dy, wy, sy, product, operation, operator, resolution))
	# 	dt_current = dt_future
	# else:
	# 	conn.commit()
	# c.execute("SELECT * FROM statistics ORDER BY [Id]")
	# for text in [f"HourDay: {hd}, DayMonth: {dm}, WeekMonth: {wm}, MonthYear: {my}, Year: {y}, DayWeek: {dw}, DayYear: {dy}, WeekYear: {wy}, SeasonYear: {sy}, Product: {product}, Operation: {operation}, Operator: {operator}, Resolution: {resolution}" for Id, hd, dm, wm, my, y, dw, dy, wy, sy, product, operation, operator, resolution in c.fetchall()]:
	# 	print(text)
	# print()
	# quit()
	month_dict = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
	              7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'}
	week_dict = {0: 'Week 1', 1: 'Week 2', 2: 'Week 3', 3: 'Week 4'}
	day_dict = {0: 'Sunday', 1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 5: 'Friday', 6: 'Saturday'}
	hour_dict = {4: '4 am', 5: '5 am', 6: '6 am', 7: '7 am', 8: '8 am', 9: '9 am', 10: '10 am', 11: '11 am',
	             12: '12 pm', 13: '1 pm', 14: '2 pm', 15: '3 pm', 16: '4 pm', 17: '5 pm', 18: '6 pm'}
	h_set = [int(x[0]) for x in c.execute("SELECT DISTINCT [HourDay] FROM statistics WHERE [HourDay] != 0").fetchall()]
	d_set = [int(x[0]) for x in c.execute("SELECT DISTINCT [DayWeek] FROM statistics WHERE [HourDay] != 0").fetchall()]
	w_set = [int(x[0]) for x in c.execute("SELECT DISTINCT [WeekMonth] FROM statistics WHERE [HourDay] != 0").fetchall()]
	m_set = [int(x[0]) for x in c.execute("SELECT DISTINCT [MonthYear] FROM statistics WHERE [HourDay] != 0").fetchall()]

	color_dict = {1: [255, 000, 000], 2: [204, 75, 32], 3: [255, 127, 000],
	              4: [255, 241, 000], 5: [116, 255, 32], 6: [60, 170, 60],
	              7: [95, 255, 157], 8: [28, 234, 255], 9: [0, 68, 255],
	              10: [33, 127, 193], 11: [189, 131, 241], 12: [218, 57, 184]}

	line_width = 0.25
	m_set = range(1, 9)
	w_set = range(4)
	d_set = range(1, 7)
	h_set = range(4, 19)

	m_labels = [month_dict[i] for i in m_set]
	w_labels = [week_dict[i] for j in m_set for i in w_set]
	d_labels = [day_dict[i] for j in w_set for k in m_set for i in d_set]
	h_labels = [hour_dict[i] for j in d_set for k in w_set for l in m_set for i in h_set]

	operation = 'QC'
	# -15
	products = ['LOC8', 'ET1', 'LOC8 Beacon', 'ET1 Beacon']
	fig, ((ax1, ax2),(ax3, ax4)) = plt.subplots(2, 2, sharex=True, sharey=True, squeeze=True)
	for ax_num, (ax, prod) in enumerate(zip([ax1, ax2, ax3, ax4], products)):
		max_x = 1200
		rng = np.arange(0, max_x, max_x / len(m_set))
		width = max_x/len(m_set)
		for i,m in zip(rng, m_set):
			color = color_dict[m]
			color_hsv = rgb_to_hsv(*color[:3])
			color2 = list(hsv_to_rgb(color_hsv[0], color_hsv[1] - 20, color_hsv[2]))
			color3 = list(hsv_to_rgb(color_hsv[0], color_hsv[1] - 40, color_hsv[2]))
			color4 = list(hsv_to_rgb(color_hsv[0], color_hsv[1] - 60, color_hsv[2]))
			retval_m = []
			retval_w = []
			retval_d = []
			retval_h = []
			# c.execute("SELECT COUNT([Id]) FROM statistics WHERE [MonthYear] = ? AND [Operation] = ? AND [Product] = ?", (m, operation, product))
			# retval_m.append(c.fetchone()[0])
			# for w in w_set:
			# 	c.execute("SELECT COUNT([Id]) FROM statistics WHERE [MonthYear] = ? AND [WeekMonth] = ? AND [Operation] = ? AND [Product] = ?", (m, w, operation, product))
			# 	retval_w.append(c.fetchone()[0])
			# 	for d in d_set:
			# 		c.execute("SELECT COUNT([Id]) FROM statistics WHERE [MonthYear] = ? AND [WeekMonth] = ? AND [DayWeek] = ? AND [Operation] = ? AND [Product] = ?", (m, w, d, operation, product))
			# 		retval_d.append(c.fetchone()[0])
			# 		for h in h_set:
			# 			c.execute("SELECT COUNT([Id]) FROM statistics WHERE [MonthYear] = ? AND [WeekMonth] = ? AND [DayWeek] = ? AND [HourDay] = ? AND [Operation] = ? AND [Product] = ?", (m, w, d, h, operation, product))
			# 			retval_h.append(c.fetchone()[0])
			c.execute("SELECT COUNT([Id]) FROM statistics WHERE [MonthYear] = ? AND [Product] = ? AND [Operation] = ?", (m, prod, operation))
			retval_m.append(c.fetchone()[0])
			for w in w_set:
				c.execute("SELECT COUNT([Id]) FROM statistics WHERE [MonthYear] = ? AND [WeekMonth] = ? AND [Product] = ? AND [Operation] = ?", (m, w, prod, operation))
				retval_w.append(c.fetchone()[0])
				for d in d_set:
					c.execute("SELECT COUNT([Id]) FROM statistics WHERE [MonthYear] = ? AND [WeekMonth] = ? AND [DayWeek] = ? AND [Product] = ? AND [Operation] = ?", (m, w, d, prod, operation))
					retval_d.append(c.fetchone()[0])
					for h in h_set:
						c.execute("SELECT COUNT([Id]) FROM statistics WHERE [MonthYear] = ? AND [WeekMonth] = ? AND [DayWeek] = ? AND [HourDay] = ? AND [Product] = ? AND [Operation] = ?", (m, w, d, h, prod, operation))
						retval_h.append(c.fetchone()[0])
			ax.bar(left=np.arange(i, i + width, width / len(retval_m)), height=retval_m, width=width / len(retval_m), align='edge', color=color.append(255), linewidth=line_width, edgecolor=[0, 0, 0])
			ax.bar(left=np.arange(i, i + width, width / len(retval_w)), height=retval_w, width=width / len(retval_w), align='edge', color=color2.append(255), linewidth=line_width, edgecolor=[0, 0, 0])
			ax.bar(left=np.arange(i, i + width, width / len(retval_d)), height=retval_d, width=width / len(retval_d), align='edge', color=color3.append(255), linewidth=line_width, edgecolor=[0, 0, 0])
			ax.bar(left=np.arange(i, i + width, width / len(retval_h)), height=retval_h, width=width / len(retval_h), align='edge', color=color4.append(255), linewidth=line_width, edgecolor=[0, 0, 0])
		ymin, ymax = plt.ylim()
		major_ticks = np.arange(0, ymax, 1000)
		minor_ticks = np.arange(0, ymax, 100)
		# ax.set_xticks(major_ticks)
		# ax.set_xticks(minor_ticks, minor=True)
		ax.set_yticks(major_ticks)
		ax.set_yticks(minor_ticks, minor=True)
		ax.yaxis.grid(which='minor', alpha=0.2)
		ax.yaxis.grid(which='major', alpha=0.4)
		if ax_num == 0:
			ax.tick_params(axis='x', which='both', bottom=False, top=False, left=False, right=False, labelbottom=False, labeltop=False, labelleft=False, labelright=False)
			ax.tick_params(axis='y', which='both', direction='inout', bottom=False, top=False, left=True, right=False, labelbottom=False, labeltop=False, labelleft=True, labelright=False)
			ax.tick_params(axis='y', which='minor', direction='in')
		elif ax_num == 1:
			ax.tick_params(axis='both', which='both', bottom=False, top=False, left=False, right=False, labelbottom=False, labeltop=False, labelleft=False, labelright=False)
			ax.tick_params(axis='y', which='both', direction='in', bottom=False, top=False, left=False, right=True, labelbottom=False, labeltop=False, labelleft=False, labelright=False)
		elif ax_num == 2:
			ax.tick_params(axis='x', which='both', direction='out', bottom=True, top=False, left=False, right=False, labelbottom=True, labeltop=False, labelleft=False, labelright=False)
			ax.tick_params(axis='y', which='both', direction='inout', bottom=False, top=False, left=True, right=False, labelbottom=False, labeltop=False, labelleft=True, labelright=False)
			ax.tick_params(axis='y', which='minor', direction='in')
		elif ax_num == 3:
			ax.tick_params(axis='x', which='both', direction='out', bottom=True, top=False, left=False, right=False, labelbottom=True, labeltop=False, labelleft=False, labelright=False)
			ax.tick_params(axis='y', which='both', direction='in', bottom=False, top=False, left=False, right=True, labelbottom=False, labeltop=False, labelleft=False, labelright=False)
		plt.xlim(xmin=0, xmax=max_x)
		plt.xticks(np.linspace(0, max_x, len(m_set) + 1)[:-1], calendar.month_name[1:13], rotation=17)
		plt.tight_layout(pad=0.54, h_pad=0.0, w_pad=0.0)
	# plt.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=None, hspace=None)
	# plt.axes().set_aspect('equal')
	# major ticks every 20, minor ticks every 5
	# major_ticks = np.arange(0, 101, 20)
	# minor_ticks = np.arange(0, 101, 5)
	#
	# ax.set_xticks(major_ticks)
	# ax.set_xticks(minor_ticks, minor=True)
	# ax.set_yticks(major_ticks)
	# ax.set_yticks(minor_ticks, minor=True)
	#
	# # and a corresponding grid
	#
	# ax.grid(which='both')
	#
	# # or if you want differnet settings for the grids:
	# ax.grid(which='minor', alpha=0.2)
	# ax.grid(which='major', alpha=0.5)
	plt.show()
	plt.savefig('bar_figure.pdf')
	quit()

	c.execute("SELECT DISTINCT [Operation] FROM statistics")
	for op in c.fetchall():
		retval2 = {}
		c.execute("SELECT DISTINCT [Operator] FROM statistics WHERE [Operation] = ?", (op[0],))
		for op2 in c.fetchall():
			retval3 = defaultdict(int)
			dt_current = dt_start
			while dt_current < dt_temp:  # datetime.datetime.now():
				dt_future = dt_current + datetime.timedelta(hours=1.)
				c.execute("SELECT [DayMonth],[WeekMonth],[MonthYear] FROM statistics WHERE [HourDay] = ? AND [Operation] = ? AND [Operator] = ? ORDER BY [Id] ASC", (dt_current.hour,op[0],op2[0]))
				for day, week, month in c.fetchall():
					retval3[f'{day},{week},{month}'] += 1
				dt_current = dt_future
			retval2[op2] = sorted(retval3.items(), key=operator.itemgetter(1), reverse=True)


if __name__ == '__main__':
	main()
