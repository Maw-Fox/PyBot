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


def log(scope: str, *args, suffix: str = '', io: int = 1) -> None:
    io_s: str = '<< ' if io else '>> '
    suffix_s: str = f' {suffix} ' if suffix else suffix
    print(f'[{int(time())}]:{scope}{io_s}{suffix_s}', *args)
