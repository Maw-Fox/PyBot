import re
import unicodedata as unicode

from time import time
from math import floor
from modules.shared import JANK_TO_ASCII_TABLE, TEXT_AGE, TEXT_AGE_FALSEPOS
from modules.character import Character, GLOBAL_CHARACTER_LIST
from modules.channel import Channel, CHANNELS
from modules.log import ModLog, MOD_LOGS


def log(scope: str, *args, suffix: str = '', io: int = 1) -> None:
    io_s: str = '<< ' if io else '>> '
    suffix_s: str = f' {suffix} ' if suffix else suffix
    print(f'[{int(time())}]:{scope}{io_s}{suffix_s}', *args)


def jank_to_ascii(sanitize_me: str) -> str:
    buffer: str = sanitize_me
    # cycle through ascii table, do substitutions.
    for to_rep in JANK_TO_ASCII_TABLE:
        to_sub: str = JANK_TO_ASCII_TABLE[to_rep]
        buffer = re.sub(f'[{to_sub}]', to_rep, buffer)
    # clean out the non-ascii characters, except space and dash
    buffer = re.sub('[^a-zA-Z0-9 \\-\\/]', '', buffer)
    return buffer


WRITTEN_EXCL: re.Pattern = re.compile(
    '((twent|thirt|fort|fift|sixt|sevent|eight|ninet)[y]?[ -]+' +
    '(six|seven|eight|nine|ten)|(six|seven|eight|nine|ten)[ -]+' +
    '(hundred|thousand))'
)


def is_written_taboo(s: str) -> bool:
    exclude: re.Match = re.search(WRITTEN_EXCL, s)
    if exclude:
        return False
    exploded: list[str] = re.split('[^a-z0-9]', s)
    for age in TEXT_AGE_FALSEPOS:
        for part in exploded:
            if age == part:
                return True
    for age in TEXT_AGE:
        if age in s:
            return True
    return False


def age_tester(test_me: str) -> bool:
    if not test_me:
        return False
    buffer: str = jank_to_ascii(test_me)
    buffer = unicode.normalize('NFKD', buffer)
    buffer = buffer.lower()
    if is_written_taboo(buffer):
        return True
    # clear all non-char/non-number characters, except dash (for range comp)
    buffer = re.sub('[^a-z0-9 -/]', '', buffer)
    buffer = buffer.replace('/', '-')
    exploded: list[str] = buffer.split(' ')
    for idx in range(len(exploded)):
        part: str = exploded[idx]
        try:
            exploded.index('-', idx)
            is_minimum: bool = True
        except ValueError:
            is_minimum: bool = False

        if not is_minimum and re.match('^[0-9]+$', part):
            age: int = int(part, base=10)
            if age < 18 and age > 5:
                return True
    buffer = buffer.replace(' ', '')
    exploded = buffer.split('-')
    first_age: bool = True
    for idx in range(len(exploded)):
        part: str = exploded[idx]
        is_age: re.Match = re.match('^[0-9]+$', part)
        if not is_age:
            continue
        if first_age:
            first_age = False
            continue
        age: int = int(part, base=10)
        if age < 18 and age > 5:
            return True
    return False


def get_char(character: str) -> Character | None:
    return GLOBAL_CHARACTER_LIST.get(character, Character(character))


def get_chan(channel: str) -> Channel:
    return CHANNELS.get(channel) or Channel(channel)


def remove_all(character: Character) -> None:
    GLOBAL_CHARACTER_LIST.pop(character.name)
    for channel in CHANNELS:
        get_chan(channel).remove_char(character)


def get_logs(n_items: int = 10) -> list[ModLog]:
    return MOD_LOGS[:n_items]


def get_time_str(t: int) -> str:
    time_diff: int = int(time()) - t
    time_days: int = floor(time_diff / 86400)
    time_hours: int = floor((time_diff % 86400) / 3600)
    time_minutes: int = floor((time_diff % 3600) / 60)
    time_seconds: int = floor(time_diff % 60)
    time_string: str = ''
    time_string += f'{time_days} day(s), ' if time_days else ''
    time_string += f'{time_hours} hour(s), ' if time_hours else ''
    time_string += f'{time_minutes} minute(s), ' if time_minutes else ''
    time_string += f'{time_seconds} second(s), ' if time_seconds else ''
    return time_string[:len(time_string) - 2]
