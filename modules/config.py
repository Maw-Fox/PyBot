import sys as system
import os
import json
import hashlib

from modules.shared import ARGS


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
        self.account_name: str = username
        self.account_password: str = password
        self.client_name: str = client_name
        self.client_version: str = client_version
        self.retry_interval: int = retry_interval
        self.bot_name: str = bot_name
        self.joined_channels: list[str] = joined_channels


def do_crypt(phrase: str, pw: str, forward: bool = True, _t='sha512') -> bytes:
    key: hashlib._Hash = hashlib.new(_t, usedforsecurity=True)
    key.update(bytes(phrase, encoding='UTF-8'))
    bytes_passphrase: bytes = key.digest()
    bytes_list: list[int] = []
    bytes_password: bytes

    if forward:
        bytes_password = bytes(pw, 'UTF-8')
    else:
        bytes_password = bytes.fromhex(pw)

    for b_idx in range(len(bytes_passphrase)):
        if forward and b_idx >= len(bytes_password):
            bytes_list.append(bytes_passphrase[b_idx])
            continue
        bytes_list.append(
            bytes_passphrase[b_idx] ^ bytes_password[b_idx]
        )

    return bytes(bytes_list)


def get_config() -> dict[str, str | int]:
    if os.path.exists('data/config.json'):
        file = open(
            'data/config.json',
            'r',
            encoding='UTF-8'
        )
        return json.load(file)
    else:
        system.exit('No config.json exists.')


def get_credentials() -> dict[str, str]:
    if ARGS.username and ARGS.password:
        if not ARGS.skip_phrase:
            passphrase = input('Set a passphrase (leave empty to skip):')
            if passphrase:
                f = open('data/creds.json', 'w', encoding='UTF-8')
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
    if os.path.exists('data/creds.json'):
        passphrase = input('passphrase:')
        f = open(
            'data/creds.json',
            'r',
            encoding='UTF-8'
        )
        f_data = json.load(f)
        result = do_crypt(passphrase, f_data['password'], False)
        try:
            f_data['password'] = result.decode('UTF-8')
        except Exception:
            system.exit('Invalid passphrase.')

        return f_data
    else:
        print('creds.json doesn\'t exist or username and password not set.')
        print('Running first-time credential setup...')
        username = input('Account name:')
        password = input('Password:')
        passphrase = input('Passphrase (empty to skip):')
        if not username or not password:
            system.exit('Password or account name is invalid, aborting...')
        if passphrase:
            f = open('data/creds.json', 'w', encoding='UTF-8')
            f.write(
                json.dumps(
                    {
                        'username': username,
                        'password': do_crypt(passphrase, password).hex()
                    },
                    indent=2
                )
            )
            f.close()
        return {
            'username': username,
            'password': password
        }


CONFIG: Config = Config(**get_config(), **get_credentials())
