import requests
import json
from time import time, sleep

from modules.config import CONFIG

AUTH_DURATION: int = 60 * 12
URL_API_GET_TICKET: str = 'https://www.f-list.net/json/getApiTicket.php'


class Auth:
    auth_key: str = None
    __valid_until: int = None

    def __init__(self) -> None:
        self.__get_new_auth_ticket()

    def check_ticket(self) -> None:
        t: int = int(time())
        if t > self.__valid_until:
            self.__get_new_auth_ticket()

    def __get_new_auth_ticket(self) -> None:
        params = {
            'account': CONFIG.account_name,
            'password': CONFIG.account_password
        }
        response = requests.post(URL_API_GET_TICKET, params=params)
        if response.status_code == 200:
            response_parsed = json.loads(response.text)
            try:
                if not hasattr(response_parsed, 'error'):
                    self.auth_key = response_parsed['ticket']
                    self.__valid_until = int(time()) + AUTH_DURATION
                    print(self.auth_key)
            except KeyError:
                print('Invalid credentials?')
                exit(0)
        else:
            print(f'Error getting ticket, code: {response.status_code}')
            sleep(1)
            self.__get_new_auth_ticket()


AUTH: Auth = Auth()
