import os
import argparse

AUTH_DURATION: int = 1800
URL_DOMAIN: str = 'https://f-list.net'
URL_API_GET_TICKET: str = f'{URL_DOMAIN}/json/getApiTicket.php'
PATH_CWD: str = os.getcwd()
PRUNE_INSTANCE_DURATION: int = 60 * 60 * 24
PARSER = argparse.ArgumentParser(
    'PyBot',
    '--username me --password qwerty',
    'A F-Chat bot framework running in Python.',
    add_help=True
)
PARSER.add_argument(
    '--username',
    dest='username',
    default=None,
    required=False,
    type=str,
    help='Your account username. An alternative to creds.json.'
)
PARSER.add_argument(
    '--password',
    dest='password',
    default=None,
    required=False,
    type=str,
    help='Your account password. An alternative to creds.json.'
)
ARGS = PARSER.parse_args()
ARGS_USERNAME = ARGS.username
ARGS_PASSWORD = ARGS.password
