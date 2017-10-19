"""Make sure the SyteLine Application is currently up and running"""

from processes.preprogram.preprogram import Preprogram as preprogram
from processes.reason.reason import Reason as reason
from processes.scrap.scrap import Scrap as scrap
from processes.transact.transact import Transaction as transaction
from config import *
from _common import Application, is_running

if is_running(application_filepath):
	pass

# TODO: Initialization

__all__ = ['preprogram', 'reason', 'scrap', 'transaction']
