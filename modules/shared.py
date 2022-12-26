import argparse
import json

from time import time

UPTIME: int = int(time())
COMMAND_TIMEOUT: int = 60 * 5

PARSER = argparse.ArgumentParser(
    prog='PyBot',
    description='A F-Chat bot framework running in Python.',
    allow_abbrev=False,
    add_help=True
)
PARSER.add_argument(
    '--username',
    '--user',
    dest='username',
    default=None,
    required=False,
    type=str,
    help='Your account username. An alternative to creds.json.'
)
PARSER.add_argument(
    '--password',
    '--pass',
    dest='password',
    default=None,
    required=False,
    type=str,
    help='Your account password. An alternative to creds.json.'
)
PARSER.add_argument(
    '--nophrase',
    '--skip',
    dest='skip_phrase',
    action='store_true',
    help='Skip the setting of the passphrase.'
)
ARGS = PARSER.parse_args()

PRUNE_INSTANCE_DURATION: int = 60 * 60 * 24

# charcode (ascii) contains a list of similar characters
# just in case people try to get clever and bypass the
# age check.
TEXT_AGE_FALSEPOS: list[str] = [
    'six',
    'seven',
    'eight',
    'nine',
    'ten'
]

TEXT_AGE: list[str] = [
    'eleven',
    'twelve',
    'thirteen',
    'fourteen',
    'fifteen',
    'sixteen',
    'seventeen'
]

__f = open('src/conversion_tables.json', 'r', encoding='UTF-8')
JANK_TO_ASCII_TABLE: dict[str, str] = json.load(__f)
__f.close()
