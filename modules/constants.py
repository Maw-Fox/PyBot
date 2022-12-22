import os
import argparse

from modules.utils import cat

AUTH_DURATION: int = 1800
URL_DOMAIN: str = 'https://f-list.net'
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
    '--makecreds',
    '--creds',
    dest='make_creds',
    action='store_true',
    help=cat(
        'While inputting username and password',
        ' (via either command args or creds.json), ',
        'also create/modify a creds.json with a ',
        'randomly generated SHA-256 key so that credentials',
        ' aren\'t stored as plaintext.'
    )
)
ARGS = PARSER.parse_args()
