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
    bytes_password: bytes

    if forward:
        bytes_password = bytes(password, 'UTF-8')
    else:
        bytes_password = bytes.fromhex(password)

    for b_idx in range(len(bytes_passphrase)):
        if forward and b_idx >= len(bytes_password):
            bytes_list.append(bytes_passphrase[b_idx])
            continue
        bytes_list.append(
            bytes_passphrase[b_idx] ^ bytes_password[b_idx]
        )

    return bytes(bytes_list)


def get_config() -> dict[str, str | int]:
    if os.path.exists('config.json'):
        file = open(
            'config.json',
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
    if os.path.exists('creds.json'):
        passphrase = input('passphrase:')
        f = open(
            'creds.json',
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
            f = open('creds.json', 'w', encoding='UTF-8')
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
