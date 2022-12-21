def cat(*args: str) -> str:
    out = ''
    for v in args:
        out += v
    return out
