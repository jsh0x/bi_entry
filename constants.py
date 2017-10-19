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
REGEX_BUILD = re.compile(r"(?P<prefix>[A-Z]{2})-(?P<build>\d{3}(?P<carrier>[VS])?)(?:-(?P<suffix>M|DEMO|R|T))?")
REGEX_BUILD_ALT = re.compile(r"(?P<prefix>[A-Z]{2})-(?P<build>(?P<carrier>\d)\d{3})(?:-(?P<suffix>M|DEMO|R|T))?")
REGEX_RESOLUTION = re.compile(r"(?P<general>\d+),(?P<specific>\d+)")
REGEX_NUMERIC_RANGES = re.compile(r"(\d{1,2})-(\d{1,2})|(\d{1,2})")

# - - - - - - - - - - - - - - - - - - - - COMMON  - - - - - - - - - - - - - - - - - - - -
# noinspection SpellCheckingInspection
# language=RegExp
SYTELINE_WINDOW_TITLE = r'Infor ERP SL \(EM\).*'

CELLULAR_BUILDS = ('EX-600-M', 'EX-625S-M', 'EX-600-T', 'EX-600', 'EX-625-M', 'EX-600-DEMO', 'EX-600S', 'EX-600S-DEMO', 'EX-600V-M',
                   'EX-600V', 'EX-680V-M', 'EX-600V-DEMO', 'EX-680V', 'EX-680S', 'EX-680V-DEMO', 'EX-600V-R', 'EX-680S-M', 'HG-2200-M',
                   'CL-4206-DEMO', 'CL-3206-T', 'CL-3206', 'CL-4206', 'CL-4206', 'CL-3206-DEMO', 'CL-4206-M', 'CL-3206-M', 'HB-110',
                   'HB-110-DEMO', 'HB-110-M', 'HB-110S-DEMO', 'HB-110S-M', 'HB-110S', 'LC-800V-M', 'LC-800S-M', 'LC-825S-M', 'LC-800V-DEMO',
                   'LC-825V-M', 'LC-825V-DEMO', 'LC-825V', 'LC-825S', 'LC-825S-DEMO', 'LC-800S-DEMO')

# noinspection SpellCheckingInspection
SUFFIX_DICT = {'M': 'Monitoring', 'R': 'Refurb',
               'T': 'Trial', 'DEMO': 'Demo', '-': 'Direct'}

CARRIER_DICT = {'V': 'Verizon', 'S': 'Sprint', '-': None,
                '3': 'Verizon', '4': 'Sprint', '2': None}
