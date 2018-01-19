# coding=utf-8
def camelcase_splitter(text: str) -> str:
	return ''.join(y if not (i > 0 and text[i - 1].islower() and text[i].isupper()) else (' ' + y) for i, y in enumerate(text))


def prepare_string(text: str, strip_chars: str = None, *, remove_all_whitespace: bool = False) -> str:  # THINK: Maybe as decorator?
	if text is None:
		return text
	strip_chars = ' ' if strip_chars is None else strip_chars + ' '
	text = text.strip(strip_chars)
	if remove_all_whitespace:
		while ' ' in text:
			text = text.replace(' ', '')
	if not text:
		return None
	return text


def log_friendly_string(text: str) -> str:
	while ('\r' in text) or ('\n' in text) or ('\t' in text):
		text = text.replace('\r', '')
		text = text.replace('\n', '')
		text = text.replace('\t', '')
	else:
		return text


__all__ = ['log_friendly_string', 'prepare_string', 'camelcase_splitter']
