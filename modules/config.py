import sys as system
import os
import json
import hashlib
import hmac

from modules.constants import PATH_CWD, ARGS


class Config:
    def __init__(
        self,
        username: str,
        password: str,
        client_name: str,
        client_version: str,
        retry_interval: int,
        bot_name: str,
        joined_channels: list[str],
        key: str = ''
    ) -> None:
        self.account_name = username
        self.account_password = password
        self.client_name = client_name
        self.client_version = client_version
        self.retry_interval = retry_interval
        self.bot_name = bot_name
        self.joined_channels = joined_channels
        if ARGS.make_creds:
            key: bytes = hashlib.new('sha256').digest()
            pw: bytes = bytes(password, 'UTF-8')
            byte_seq: list = []
            for byte in pw:
                for byte_2 in key:
                    byte ^= byte_2
                byte_seq.append(byte)

            pw_encoded: bytes = bytes(byte_seq)

            f = open('creds.json', 'w', encoding='UTF-8')
            f.write(
                json.dumps(
                    {
                        'username': username,
                        'password': pw_encoded.hex(),
                        'key': key.hex()
                    },
                    indent=2
                )
            )
            f.close()
            return

        if key:
            key: bytes = bytes.fromhex(key)
            pw: bytes = bytes.fromhex(password)
            byte_seq: list = []
            sorted(key, reverse=True)
            for byte in pw:
                for byte_2 in key:
                    byte ^= byte_2
                byte_seq.append(byte)
            self.account_password = bytes(byte_seq).decode('UTF-8')


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
    if ARGS.username and ARGS.password:
        return {
            'username': ARGS.username,
            'password': ARGS.password
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
