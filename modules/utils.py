import re

from time import time
from modules.shared import JANK_TO_ASCII_TABLE, TEXT_AGE, TEXT_AGE_FALSEPOS
from modules.character import Character, GLOBAL_CHARACTER_LIST
from modules.channel import Channel, CHANNELS


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
    buffer = re.sub('[^a-z0-9 \\-\\/]', '', buffer)
    return buffer


def is_written_taboo(s: str) -> bool:
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
    buffer = buffer.lower()
    if is_written_taboo(buffer):
        return True
    # clear all non-char/non-number characters, except dash (for range comp)
    buffer = re.sub('[^a-z0-9 ]', '', buffer)
    exploded: list[str] = re.split('[ ]', buffer)
    for part in exploded:
        if re.match('^[0-9]+$', part):
            age: int = int(part, base=10)
            if age < 18 and age > 5:
                return True
    return False


def get_char(character: str) -> Character | None:
    return GLOBAL_CHARACTER_LIST.get(character, None)


def get_chan(channel: str) -> Channel | None:
    return CHANNELS.get(channel)


def remove_all(character: Character) -> None:
    GLOBAL_CHARACTER_LIST.pop(character.name)
    for channel in CHANNELS:
        get_chan(channel).remove_char(character)
