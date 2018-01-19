#! python3 -W ignore
# coding=utf-8

from core.DataGrid import *
from core.PuppetMasterOLD import *
from core.Timer import *
from core.Unit import *

from core.Application import *
# THINK: New type for type annotating that specifies range of possible return values(for overloading)?
# example 1: arg1 -> string.length(5) | arg2 -> string.length(8)
# example 2: arg1 -> int_range(00, 01, …, 23) | arg2 -> int_range(01, 02, …, 12)

# THINK: New type for type annotating that specifies range of possible argument values(for overloading)?
# example 1: int_range(00, 01, …, 11) -> retval else raise Index/Type/ValueError
# example 2: possible_args('S', 'M') -> retval else raise Index/Type/ValueError

# THINK: Functions within argument, ie str.upper() -> performs upper() on provided argument, ensuring specific case
# TODO: Test possible solution: Decorators, wrapping with

# THINK: Functions within retval, ie int() -> performs int() on provided retval, ensuring specific result
# TODO: Possible solution: Decorators, wrapping with


# TODO: When positional-only arguments are finally added
# PEP 457: https://www.python.org/dev/peps/pep-0457/

# hcursor 65543 == loading
