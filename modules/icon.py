import requests
from time import time
from hashlib import md5
from modules.typedefs import DbRow
from modules.utils import log


def _build_blacklist() -> list[str]:
    f = open('data/blacklist.csv', 'r', encoding='utf-8')
    return f.read()[:-1].split('\n')


def _build_db() -> dict[str, DbRow]:
    obj: dict[str, DbRow] = {}
    f = open('data/eicon_db.csv', 'r', encoding='utf-8')
    lines: list[str] = str(f.read()).split('\n')
    f.close()
    for line in lines:
        name, extension, last_verified, uses = line.split(',')
        obj[name] = [name, extension, int(last_verified), int(uses)]
    return obj


class Icon:
    HASH404: str = 'c9e84fc18b21d3cb955340909c5b369c'
    save: float = time() + 600.0
    db: dict[str, DbRow] = _build_db()
    blacklist: list[str] = _build_blacklist()

    def __init__(self, check: str):
        self.check: str = check.lower()
        queue.append(self)

    @staticmethod
    def is_valid(check: str) -> bool:
        response = requests.get(
            f'https://static.f-list.net/images/eicon/{check}.gif'
        )
        file_hash: str = md5(
            response.content, usedforsecurity=False
        ).hexdigest()

        if file_hash == Icon.HASH404:
            return False
        return True

    def do(self) -> None:
        for blacklisted in Icon.blacklist:
            if blacklisted in self.check:
                continue

        response = requests.get(
            f'https://static.f-list.net/images/eicon/{self.check}.gif'
        )
        file_hash: str = md5(
            response.content, usedforsecurity=False
        ).hexdigest()

        if file_hash == Icon.HASH404:
            return

        mime: str = response.headers.get('content-type')
        mime = mime.split('/')[1]
        log(
            'IDB/ADD',
            f'SAV:T{int(int(time()) - Icon.save)}  >>',
            f'{self.check}.{mime}'
        )
        Icon.db[self.check] = [self.check, mime, int(time()), 1]

    @staticmethod
    def cycle(force: bool = False) -> None:
        t: float = time()
        if t > Icon.save or force:
            log('IDB/SAV', f'NEW_DB_SIZE: {len(Icon.db)}')
            Icon.save = t + 600.0
            # Sort by alphanumeric
            Icon.db: dict[str, list[str | int]] = dict(
                sorted(
                    Icon.db.items(),
                    key=lambda x: x[0]
                )
            )
            # Popularity sort, the primary sort category
            Icon.db: dict[str, list[str | int]] = dict(
                sorted(
                    Icon.db.items(),
                    key=lambda x: x[1][3],
                    reverse=True
                )
            )
            f = open('data/eicon_db.csv', 'w', encoding='utf-8')
            f.write(
                '\n'.join(
                    [f'{w},{x},{y},{z}' for w, x, y, z in Icon.db.values()]
                )
            )
            f.close()
        if not len(queue):
            return
        queue.pop(0).do()


queue: list[Icon] = []
