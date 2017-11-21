import logging

from common import PuppetMaster
from constants import SYTELINE_WINDOW_TITLE

log = logging.getLogger(__name__)

starting_forms = {'User Information'}

def run(self: PuppetMaster.Puppet):
	app = self.app
	print(app)
	app.verify_form('User Information')
	sl_win = app.win32.window(title_re=SYTELINE_WINDOW_TITLE)
	sl_uia = app.uia.window(title_re=SYTELINE_WINDOW_TITLE)
	print(app)
	uid = sl_win.UserID.texts()[0]
	print(uid)
	print(app.get_user())
	print(uid == app.get_user())



