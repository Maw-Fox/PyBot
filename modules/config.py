import sys as system
import os
import json

from modules.constants import PATH_CWD, ARGS_USERNAME, ARGS_PASSWORD


class Config:
    def __init__(
        self,
        account_name: str,
        account_password: str,
        client_name: str,
        client_version: str,
        retry_interval: int,
        bot_name: str,
        joined_channels: list[str]
    ) -> None:
        self.account_name = account_name
        self.account_password = account_password
        self.client_name = client_name
        self.client_version = client_version
        self.retry_interval = retry_interval
        self.bot_name = bot_name
        self.joined_channels = joined_channels


def get_config():
    if os.path.exists(os.path.join(PATH_CWD, 'config.json')):
        file = open(
            os.path.join(PATH_CWD, 'config.json'),
            'r',
            encoding='UTF-8'
        )
        return json.load(file)
    else:
        system.exit('No config.json exists.')


def get_credentials():
    if ARGS_USERNAME:
        return {
            'account_name': ARGS_USERNAME,
            'account_password': ARGS_PASSWORD
        }
    if os.path.exists(os.path.join(PATH_CWD, 'creds.json')):
        file = open(
            os.path.join(PATH_CWD, 'creds.json'),
            'r',
            encoding='UTF-8'
        )
        return json.load(file)
    else:
        system.exit('No creds.json exists.')


CONFIG: Config = Config(**get_config(), **get_credentials())
