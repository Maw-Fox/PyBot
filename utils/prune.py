import argparse
import requests
import sys
import os

from pathlib import Path
from hashlib import md5
from time import time

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


def log() -> None:
    if sys.platform.startswith('win'):
        os.system('cls')
    else:
        os.system('clear')
    sys.displayhook(''.join(Verify.disp))


def get_exists() -> dict[str, tuple[str, str, int, int]]:
    obj: dict[str, tuple[str, str, int, int]] = {}
    f = open(PATH, 'r', encoding='utf-8')
    lines: list[str] = f.read().split('\n')
    for line in lines:
        name, extension, last_verified, count = line.split(',')
        obj[name] = (name, extension, int(last_verified), int(count))
    return obj


class Verify:
    HASH_404: str = 'c9e84fc18b21d3cb955340909c5b369c'
    next: float = time() + 1.0
    __step: int = 0
    exists: dict[str, tuple[str, str, int, int]] = get_exists()
    pruned: int = 0
    disp: list[str] = [
        'Prunin\' ',
        ''
    ]

    def __init__(self, name: str, mime: str, t: int, count: int):
        self.check: str = name.lower()
        self.mime: str = mime
        self.t: int = t
        self.count: int = count
        queue.append(self.do)

    def do(self) -> None:
        Verify.itr()
        if ARGS.days and self.t < MAX_T:
            return
        response = requests.get(
            f'https://static.f-list.net/images/eicon/{self.check}.gif'
        )

        file_hash: str = md5(
            response.content, usedforsecurity=False
        ).hexdigest()

        if file_hash == Verify.HASH_404:
            Verify.exists.pop(self.check)
            Verify.pruned += 1
            return

        Verify.disp[1] = f'{len(queue)} more files...'
        log()

        mime: str = response.headers.get('content-type')
        mime = mime.split('/')[1]
        Verify.exists[self.check] = (
            self.check,
            mime,
            int(time()),
            int(self.count)
        )

    def itr() -> int:
        Verify.__step += 1


queue: list[Verify] = []

for name in Verify.exists:
    Verify(
        name,
        Verify.exists[name][1],
        Verify.exists[name][2],
        Verify.exists[name][3]
    )

for item in queue.copy():
    item()
    queue.pop()


def finish() -> None:
    print(f'Pruning complete! Pruned {Verify.pruned} items!')
    buffer: str = ''
    f = open(PATH, 'w', encoding='utf-8')
    Verify.exists = dict(
        sorted(Verify.exists.items(), key=lambda x: x[0])
    )
    for name in Verify.exists:
        name, ext, last, count = Verify.exists[name]
        buffer += f'{name},{ext},{last},{count}\n'
    f.write(buffer[:-1])
    f.close()


finish()
