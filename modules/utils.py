from time import time


def cat(*args: str) -> str:
    out = ''
    for v in args:
        out += v
    return out


def format_hp_bars(
    id: str,
    hp: int,
    hp_max: int,
    dmg: int
) -> str:
    pass


def fmt(scope: str, suf: str = '', io: int = 1) -> None:
    io_s: str = '<< ' if io else '>> '
    suf_s: str = f'{suf} ' if suf else suf
    print(f'[{int(time())}]:{scope}{io_s}{suf_s}')
