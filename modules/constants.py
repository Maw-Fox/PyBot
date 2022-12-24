import os
import argparse

from modules.utils import cat

AUTH_DURATION: int = 1800
URL_DOMAIN: str = 'https://f-list.net'
URL_CHARACTER: str = f'{URL_DOMAIN}/c/'
URL_API_GET_TICKET: str = f'{URL_DOMAIN}/json/getApiTicket.php'
WS_URI: str = 'wss://chat.f-list.net/chat2'
PATH_CWD: str = os.getcwd()
PRUNE_INSTANCE_DURATION: int = 60 * 60 * 24
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
GLOBAL_OPS: list[str] = []
