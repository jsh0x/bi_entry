# coding=utf-8
import logging
from typing import Set

import pywinauto.timings

from _common import PuppetMaster

log = logging.getLogger(__name__)
# TODO: Rework process

default_wait = 15


def Misc_Issue_form_init(self: PuppetMaster.Puppet):
	app = self.app


def run(self: PuppetMaster.Puppet, encountered_forms: Set[str]):
	form_dict = {'Units': Units_form_init, 'Service Order Lines': SRO_Lines_form_init,
				 'SRO Operations': SRO_Operations_form_init, 'SRO Transactions': SRO_Transactions_form_init,
				 'Miscellaneous Issue': Misc_Issue_form_init}
	pywinauto.timings.Timings.Slow()
	for form in encountered_forms:
		form_dict[form](self)
