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
        joined_channels: list[str]
    ) -> None:
        self.account_name = username
        self.account_password = password
        self.client_name = client_name
        self.client_version = client_version
        self.retry_interval = retry_interval
        self.bot_name = bot_name
        self.joined_channels = joined_channels


def do_crypt(passphrase: str, password: str, forward: bool = True) -> bytes:
    key: hashlib._Hash = hashlib.new('sha512', usedforsecurity=True)
    key.update(bytes(passphrase, encoding='UTF-8'))
    bytes_passphrase: bytes = key.digest()
    bytes_list: list[int] = []

    if forward:
        bytes_password: bytes = bytes(password, 'UTF-8')
        for b_idx in range(len(bytes_passphrase)):
            if b_idx >= len(bytes_password):
                bytes_list.append(bytes_passphrase[b_idx])
                continue
            bytes_list.append(
                bytes_passphrase[b_idx] ^ bytes_password[b_idx]
            )
        return bytes(bytes_list)
    else:
        bytes_password: bytes = bytes.fromhex(password)
        for b_idx in range(len(bytes_passphrase)):
            bytes_list.append(
                bytes_passphrase[b_idx] ^ bytes_password[b_idx]
            )
        return bytes(bytes_list)


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
        if not ARGS.skip_phrase:
            passphrase = input('Set a passphrase (leave empty to skip):')
            if passphrase:
                f = open('creds.json', 'w', encoding='UTF-8')
                f.write(json.dumps(
                    {
                        'username': ARGS.username,
                        'password': do_crypt(passphrase, ARGS.password).hex()
                    },
                    indent=2
                ))
                f.close()
        return {
            'username': ARGS.username,
            'password': ARGS.password
        }
    if os.path.exists(os.path.join(PATH_CWD, 'creds.json')):
        passphrase = input('passphrase (q to quit):')
        f = open(
            os.path.join(PATH_CWD, 'creds.json'),
            'r',
            encoding='UTF-8'
        )
        f_data = json.load(f)
        result = do_crypt(passphrase, f_data['password'], False)
        try:
            f_data['password'] = result.decode('UTF-8')
        except Exception as err:
            system.exit('Invalid passphrase.')

        return f_data
    else:
        system.exit('No creds.json exists.')


CONFIG: Config = Config(**get_config(), **get_credentials())
