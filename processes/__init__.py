"""Make sure the SyteLine Application is currently up and running"""

from processes import renew_password, runthrough, status_report, transact
# from _common import Application, PuppetMaster, is_running
# from config import *
from processes.preprogram.preprogram import Preprogram as preprogram
from processes.reason.reason import Reason as reason
from processes.scrap.scrap import Scrap as scrap

# host.start(application_filepath)
# if is_running(application_filepath):
# 	app = Application.connect(application_filepath)
#
# else:
# 	app = Application.start(application_filepath)
#
# if not app.logged_in:
# 	app.log_in()

# TODO: Initialization
__all__ = ['preprogram', 'reason', 'scrap', 'transact', 'status_report', 'runthrough',
           'renew_password']

'''import tkinter as tk

class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.pack()
        self.create_widgets()

    def create_widgets(self):
        self.hi_there = tk.Button(self)
        self.hi_there["text"] = "Hello World\n(click me)"
        self.hi_there["command"] = self.say_hi
        self.hi_there.pack(side="top")

        self.quit = tk.Button(self, text="QUIT", fg="red",
                              command=root.destroy)
        self.quit.pack(side="bottom")

    def say_hi(self):
        print("hi there, everyone!")

root = tk.Tk()
app = Application(master=root)
app.mainloop()'''
