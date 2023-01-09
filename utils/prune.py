import argparse
import requests

from pathlib import Path
from hashlib import md5
from time import time, sleep

PARSER = argparse.ArgumentParser(
    prog='PyBot Utilities: Prune Icon DB',
    description='A pruning script to remove database entries',
    allow_abbrev=False,
    add_help=True
)

PARSER.add_argument(
    '--days',
    '-d',
    dest='days',
    default=0,
    required=False,
    type=int,
    help=(
        'The number of days in the past from today to skip validation ' +
        'of recently-validated items. This helps make sure that all files ' +
        'remain accessible when searched.'
    )
)

ARGS = PARSER.parse_args()

PATH: str = str(Path('data/eicon_db.csv').resolve())
MAX_T: int = time() - ARGS.days * 86400


def get_exists() -> dict[str, tuple[str, str, int]]:
    obj: dict[str, tuple[str, str, int]] = {}
    f = open(PATH, 'r', encoding='utf-8')
    lines: list[str] = f.read()[:-1].split('\n')
    for line in lines:
        name, extension, last_verified = line.split(',')
        if int(last_verified) > MAX_T:
            continue
        obj[name] = (name, extension, int(last_verified))
    return obj


class Verify:
    HASH_404: str = 'c9e84fc18b21d3cb955340909c5b369c'
    next: float = time() + 1.0
    __step: int = 0
    exists: dict[str, tuple[str, str, int]] = get_exists()

    def __init__(self, check: str):
        self.check: str = check.lower()
        queue.append(self)

    def do(self) -> None:
        Verify.itr()
        response = requests.get(
            f'https://static.f-list.net/images/eicon/{self.check}.gif'
        )

        file_hash: str = md5(
            response.content, usedforsecurity=False
        ).hexdigest()

        if file_hash == Verify.HASH_404:
            Verify.exists.pop(self.check)
            return

        if not Verify.__step % 10:
            print(f'... {len(queue)} remaining...')

        mime: str = response.headers.get('content-type')
        mime = mime.split('/')[1]
        Verify.exists[self.check] = (self.check, mime, int(time()))
        sleep(0.5)
        Verify.step()

    def itr() -> int:
        Verify.__step += 1

    @staticmethod
    def step() -> None:
        if not len(queue):
            print('Pruning complete!')
            buffer: str = ''
            f = open(PATH, 'w', encoding='utf-8')
            Verify.exists = dict(
                sorted(Verify.exists.items(), key=lambda x: x[0])
            )
            for name in Verify.exists:
                name, ext, last = Verify.exists[name]
                buffer += f'{name},{ext},{last}\n'
            f.write(buffer)
            f.close()
        queue.pop(0).do()


queue: list[Verify] = []

for name in Verify.exists:
    Verify(name)

Verify.step()
