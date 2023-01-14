import requests
from time import time, perf_counter_ns
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
        self.alp: dict[str, DbRow] = items.copy()
        self.pop: dict[str, DbRow] = items.copy()
        self.ver: dict[str, DbRow] = items.copy()

        self.alpha = dict(
            sorted(self.alp.items(), key=lambda x: x[0])
        )
        self.verified = dict(
            sorted(self.ver.items(), key=lambda x: x[1][2])
        )

    def add(self, item: DbRow) -> None:
        self.alp[item[0]] = item
        self.pop[item[0]] = item
        self.ver[item[0]] = item

    def remove(self, item: str) -> None:
        self.alp.pop(item)
        self.pop.pop(item)
        self.ver.pop(item)

    def sort(self) -> None:
        ns_start: int = perf_counter_ns()
        self.alp = dict(
            sorted(
                self.alp.items(),
                key=lambda x: x[0]
            )
        )
        self.pop = dict(
            sorted(
                self.pop.items(),
                key=lambda x: x[1][3]
            )
        )
        self.ver = dict(
            sorted(
                self.ver.items(),
                key=lambda x: x[1][2]
            )
        )
        ns_finish: int = perf_counter_ns()
        log('SRT/PRO', f'took {ns_finish - ns_start} nanoseconds')


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
                    [f'{w},{x},{y},{z}' for w, x, y, z in Icon.db.pop.values()]
                )
            )
            f.close()
        if not len(queue):
            return
        queue.pop(0).do()


queue: list[Icon] = []
