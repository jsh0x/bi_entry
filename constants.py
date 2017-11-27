import re

# - - - - - - - - - - - - - - - - - - - - REGEX - - - - - - - - - - - - - - - - - - - - -
REGEX_USER_SESSION_LIMIT = re.compile(r"session count limit")
REGEX_PASSWORD_EXPIRE = re.compile(r"password will expire")
REGEX_INVALID_LOGIN = re.compile(r"user ?name.*password.*invalid")
REGEX_REPLACE_SESSION = re.compile(r"(?im)session .* user '(?P<user>\w+)' .* already exists(?s:.*)[\n\r](?P<question>.+\?)")
REGEX_WINDOW_MENU_FORM_NAME = re.compile(r"^\d+ (?P<name>[\w* ?]+\w*) .*")
REGEX_ROW_NUMBER = re.compile(r"^Row (?P<row_number>\d+)")
REGEX_SAVE_CHANGES = re.compile(r"save your changes to")
REGEX_CREDIT_HOLD = re.compile(r".*Credit Hold is Yes.*\[Customer: *(?P<customer>\d+)\].*")
REGEX_NEGATIVE_ITEM = re.compile(r"On Hand is -(?P<quantity>\d+)\.0+.*\[Item: (?P<item>\d+-\d{2}-\d{5}-\d+)\].*\[Location: (?P<location>[a-zA-Z0-9_-]+)\]")
REGEX_SQL_DATE = re.compile(r"(?P<year>\d{4})[/-](?P<month>[01]\d)[/-](?P<day>[0-3]\d)")
REGEX_SQL_TIME = re.compile(r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})(?:\.(?P<microsecond>\d+))?")
REGEX_BUILD = re.compile(r"(?P<prefix>[A-Z]{2,3})-(?P<build>\d{3}(?P<carrier>[VS])?)(?:-(?P<suffix>M|DEMO|R|T))?")
REGEX_BUILD_ALT = re.compile(r"(?P<prefix>[A-Z]{2,3})-(?P<build>(?P<carrier>\d)\d{3})(?:-(?P<suffix>M|DEMO|R|T))?")
REGEX_RESOLUTION = re.compile(r"(?P<general>\d+),(?P<specific>\d+)")
REGEX_NUMERIC_RANGES = re.compile(r"(\d{1,2})-(\d{1,2})|(\d{1,2})")
part_number_regex = re.compile(r"\d-\d{2}-\d{5}-\d")  # FIXME: UNIT TEST THIS FOR CONSISTENCY
row_number_regex = re.compile(r"^Row (?P<row_number>\d+)")
# - - - - - - - - - - - - - - - - - - - - COMMON  - - - - - - - - - - - - - - - - - - - -
# noinspection SpellCheckingInspection
# language=RegExp
SYTELINE_WINDOW_TITLE = r'Infor ERP SL \(EM\).*'

# FIXME: 110 = Verizon, 110S = Sprint

verizon_only = {'100'}
numeric_carriers = {'200', '206'}
alphabetic_carriers = {'600', '110', '625', '680', '800', '825'}
cellular_builds = verizon_only | numeric_carriers | alphabetic_carriers
carrier_dict = {'V': 'Verizon', 'S': 'Sprint', 3: 'Verizon', 4: 'Sprint', 2: None, None: 'Verizon'}
unit_type_dict = {'M': 'Monitoring', 'R': 'Refurb', 'T': 'Trial', 'DEMO': 'Demo'}

WHITE = (255, 255, 255)

DB_TABLE = 'PyComm'
TRANSACTION_STATUS = 'Queued'
SCRAP_STATUS = 'Scrap'
REASON_STATUS = 'Reason'

# Original column order:
# Posted, Bill Hold, Partner, Dept, Trans Date, SRO, Line#, Oper#, Trans Type, Item, Quantity, Customer Item, U/M, Item Description, Warehouse, Location, Lot, Impact Inventory, Billing Code, Matl Cost

# The quick brown fox jumps over the lazy dog.
