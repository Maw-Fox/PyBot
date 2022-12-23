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
