import requests
from time import time, perf_counter
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


class IconCache:
    def __init__(self, items: dict[str, DbRow]):
        self.valid: dict[str, DbRow] = items
        self.exclusive: dict[str, list[str]] = {}
        for key in items:
            self.exclusive[key] = []
        self.alp: list[DbRow] = list(items.values())
        self.pop: list[DbRow] = list(items.values())
        self.ver: list[DbRow] = list(items.values())
        self.alp.sort(key=lambda x: x[0])
        self.ver.sort(key=lambda x: x[2])

    def add(self, item: DbRow) -> None:
        self.valid[item[0]] = item
        self.exclusive[item[0]] = []
        self.alp.append(item)
        self.pop.append(item)
        self.ver.append(item)

    def remove(self, item: DbRow) -> None:
        self.valid.pop(item[0])
        self.exclusive.pop(item[0])
        self.alp.pop(self.alp.index(item))
        self.pop.pop(self.pop.index(item))
        self.ver.pop(self.ver.index(item))

    def update(self, item: DbRow) -> None:
        self.alp[self.alp.index(item)] = item
        self.pop[self.pop.index(item)] = item
        self.ver[self.ver.index(item)] = item

    def incr(self, item: DbRow) -> None:
        item[3] += 1

    def sort(self) -> None:
        ns_start: int = perf_counter()
        self.alp.sort(key=lambda x: x[0])
        self.pop = sorted(
            self.alp.copy(),
            key=lambda x: x[3],
            reverse=True
        )
        self.ver.sort(key=lambda x: x[2])
        ns_finish: int = perf_counter()
        log('IDB/SRT', f'took {ns_finish - ns_start} s')


class Icon:
    HASH404: str = 'c9e84fc18b21d3cb955340909c5b369c'
    save: float = time() + 1200.0
    blacklist: list[str] = _build_blacklist()
    db: IconCache = IconCache(_build_db())

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
        mime = response.headers.get('content-type')
        mime = mime.split('/')[1]
        Icon.db.valid[check][1] = mime
        Icon.db.valid[check][2] = int(time())
        Icon.db.update(Icon.db.valid[check])
        return True

    @staticmethod
    async def check_valid(icon: str):
        if not Icon.is_valid(icon):
            Icon.db.remove(Icon.db.valid[icon])
            log('IDB/RMV', icon)

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
        Icon.db.add([self.check, mime, int(time()), 1])

    @staticmethod
    def cycle(force: bool = False) -> None:
        t: float = time()
        if t > Icon.save or force:
            log('IDB/SAV', f'NEW_DB_SIZE: {len(Icon.db.pop)}')
            Icon.save = t + 1200.0
            Icon.db.sort()
            f = open('data/eicon_db.csv', 'w', encoding='utf-8')
            f.write(
                '\n'.join(
                    [f'{w},{x},{y},{z}' for w, x, y, z in Icon.db.pop]
                )
            )
            f.close()
        if not len(queue):
            return
        queue.pop(0).do()


queue: list[Icon] = []
