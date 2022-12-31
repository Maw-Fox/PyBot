import asyncio
import json
import requests
import os
import re

from time import time, asctime, localtime
from math import floor
from websockets.client import connect
from functools import singledispatch as default
from modules.config import CONFIG
from modules.auth import AUTH
from modules.channel import Channel
from modules.character import Character
from modules.utils import log, age_tester, get_char, get_chan, remove_all
from modules.queue import Queue
from modules.commands import BotCommand, BOT_COMMANDS
from modules.shared import UPTIME, COMMAND_TIMEOUT
from modules.log import ModLog, MOD_LOGS

URL_DOMAIN: str = 'https://www.f-list.net'
URL_PROFILE_API: str = f'{URL_DOMAIN}/json/api/character-data.php'
WS_URI: str = 'wss://chat.f-list.net/chat2'
PATH_CWD: str = os.getcwd()

KILLS: dict[Character, int] = {}
KILLS_LAST: dict[Character, int] = {}
CHECK: dict[str, int] = {
    'last': 1,
    'every': 60,
    'clear': 300
}


class Socket:
    def __init__(self) -> None:
        self.current = None
        self.initialized: bool = False

    async def read(self, code, data) -> None:
        ign: dict[str, int] = {
            'FLN': 1, 'LIS': 1, 'NLN': 1, 'PIN': 1
        }
        if hasattr(Response, code):
            if not ign.get(code, 0):
                log('INBOUND', code, data)
            await getattr(Response, code)(data)

    async def send(self, code: str, message: str = '') -> None:
        if message:
            message = f' {json.dumps(message)}'
        await self.current.send(f'{code}{message}')

    async def start(self):
        self.identity = {
            'method': 'ticket',
            'account': CONFIG.account_name,
            'ticket': AUTH.auth_key,
            'character': CONFIG.bot_name,
            'cname': CONFIG.client_name,
            'cversion': CONFIG.client_version
        }
        async with connect(
            WS_URI
        ) as websocket:
            self.current = websocket
            await websocket.send(f'IDN {json.dumps(self.identity)}')
            async for message in websocket:
                try:
                    code = message[:3]
                    data = message[4:]

                    await Queue.cycle()
                    if not self.initialized:
                        for channel in CONFIG.joined_channels:
                            parameters = json.dumps({
                                'channel': channel
                            })
                            Channel(channel)
                            await websocket.send(
                                f'JCH {parameters}'
                            )

                        self.initialized = True
                    if data:
                        data = json.loads(data)
                    else:
                        t: int = int(time())
                        AUTH.check_ticket()
                        if t - CHECK['last'] > CHECK['every']:
                            CHECK['last'] = t
                            for char in KILLS_LAST.copy():
                                ts: int = KILLS_LAST[char]
                                if t - ts > CHECK['clear']:
                                    KILLS_LAST.pop(char)
                    await self.read(code, data)
                except Exception as error:
                    log('WEB/ERR', str(error))

    async def close(self) -> None:
        await self.current.close()


def get_time_str(t: int) -> str:
    time_diff: int = int(time()) - t
    time_days: int = floor(time_diff / 86400)
    time_hours: int = floor((time_diff % 86400) / 3600)
    time_minutes: int = floor((time_diff % 3600) / 60)
    time_seconds: int = floor(time_diff % 60)
    time_string: str = ''
    time_string += f'{time_days} day(s), ' if time_days else ''
    time_string += f'{time_hours} hour(s), ' if time_hours else ''
    time_string += f'{time_minutes} minute(s), ' if time_minutes else ''
    time_string += f'{time_seconds} second(s), ' if time_seconds else ''
    return time_string[:len(time_string) - 2]


class Response:
    async def ERR(data) -> None:
        log('ERR/ANY', json.dumps(data))

    async def ORS(data) -> None:
        for i in data['channels']:
            c_data: dict = data['channels'][i]
            if not get_chan(data['channels'][i].name):
                Channel(**c_data)

    async def LIS(data) -> None:
        # data array -> name, gender, status, status msg
        for c_data in data['characters']:
            Character(
                c_data[0],
                c_data[1].lower(),
                c_data[2],
                c_data[3]
            )

    async def ICH(data) -> None:
        chan: Channel = get_chan(data['channel'])

        for c_data in data['users']:
            chan.add_char(get_char(c_data['identity']))

    async def COL(data) -> None:
        chan: Channel = get_chan(data['channel'])
        for char_str in data['oplist']:
            if not char_str:
                continue

            chan.add_op(char_str)

    async def JCH(data) -> None:
        char: Character = get_char(data['character']['identity'])
        chan: Channel = get_chan(data['channel'])

        if not chan:
            chan: Channel = Channel(data['channel'])

        chan.add_char(char)

        if not BOT_COMMANDS['yeetus'].state.get(chan.name, True):
            return

        response = requests.post(
            'https://www.f-list.net/json/api/character-data.php',
            data={
                'account': CONFIG.account_name,
                'ticket': AUTH.auth_key,
                'name': char.name,
            }
        )

        response = json.loads(response.text)

        if not response.get('infotags'):
            log('JCH/DBG', response)
            if 'Invalid ticket.' == response.get('error'):
                AUTH.get_new_auth_ticket()
            return

        vis: str = response['infotags'].get('64', '')
        age: str = response['infotags'].get('1', '')
        bad_age: bool = age_tester(age)
        bad_vis: bool = age_tester(vis)

        log('JCH/DBG', vis, age)

        if bad_age or bad_vis:
            age = f'[{age}]' if bad_age else age
            vis = f'[{vis}]' if bad_vis else vis

            log('JCH/DBG', f'Kick {char.name}, age:{age}, visual:{vis}', io=0)
            KILLS[char] = KILLS.get(char, 0) + 1

            if KILLS_LAST.get(char):
                ModLog(
                    channel=chan.name,
                    type='Age Restriction, repeated',
                    action=f'Timeout [{KILLS[char] * 10} minutes]',
                    character=char.name,
                    reason=f'age: {age}, visual: {vis}',
                    at=int(time())
                )
                return await SOCKET.send(
                    'CTU',
                    {
                        'channel': chan.name,
                        'character': char.name,
                        'length': str((KILLS[char] - 1) * 10)
                    }
                )

            ModLog(
                channel=chan.name,
                type='Age Restriction',
                action='Kick',
                character=char.name,
                reason=f'age: {age}, visual: {vis}',
                at=int(time())
            )

            KILLS_LAST[char] = int(time())

            return await SOCKET.send(
                'CKU',
                {
                    'channel': chan.name,
                    'character': char.name
                }
            )

    async def SYS(data) -> None:
        log('SYS/DAT', data)

    async def FLN(data) -> None:
        remove_all(get_char(data['character']))

    async def NLN(data) -> None:
        Character(
            data['identity'],
            data['gender'],
            data['status']
        )

    async def LCH(data) -> None:
        char: Character = get_char(data['character'])
        get_chan(data['channel']).remove_char(char)

    async def PIN(data) -> None:
        await Output.ping()

    async def PRI(data) -> None:
        message: str = data['message']
        char: Character = get_char(data['character'])
        output: Output = Output(recipient=char)

        if message[:1] != '!':
            return await output.send(
                (
                    'I am a [b]bot[/b] and not a real person.\n\n' +
                    'If you were kicked from [b]Anal Addicts[/b] by this ' +
                    'bot, be certain that your ' +
                    'character\'s [b]age[/b] and [b]visible age[/b] are ' +
                    'set to values and/or ranges that do not dip beneath 18 ' +
                    'years of age!'
                )
            )
        parameters = Parser.parse(
            message=message,
            by=char
        )
        if parameters['error']:
            return await output.send(
                '[b]Error[/b]: ' + parameters['error']
            )
        await getattr(Command, parameters['command'])(
            output=output,
            **parameters
        )

    async def MSG(data) -> None:
        message: str = data['message']
        char: Character = get_char(data['character'])
        chan: Channel = get_chan(data['channel'])
        output: Output = Output(channel=chan)

        if message[:1] != '!':
            return

        message = message[1:]

        parameters = Parser.parse(
            message=message,
            by=char,
            chan=chan
        )
        if (parameters['error']):
            return await output.send(
                '[b]Error[/b]: ' + parameters['error']
            )
        await getattr(Command, parameters['command'])(
            output=output,
            **parameters
        )


SOCKET: Socket = Socket()


class Output:
    def __init__(
        self,
        message: str = '',
        recipient: Character | None = None,
        channel: Channel | None = None,
    ) -> None:
        self.message: str = message
        self.channel: Channel | None = channel
        self.recipient: Character | None = recipient

        if recipient:
            self.send = self.__send_private
            return

        self.send = self.__send_channel

    async def __send_private(self, message) -> None:
        log('SEN/PRI', time() - Queue.last, Queue.throttle, suffix='TS:', io=0)
        if time() - Queue.last < Queue.throttle:
            Queue(self.__send_private, message)
            return

        Queue.last = time()

        message: dict[str, str] = {
            'recipient': self.recipient.name,
            'message': message
        }

        await SOCKET.send(f'PRI {json.dumps(message)}')

    async def __send_channel(self, message) -> None:
        log('SEN/MSG', time() - Queue.last, Queue.throttle, suffix='TS:', io=0)
        if time() - Queue.last < Queue.throttle:
            Queue(self.__send_channel, message)
            return

        Queue.last = time()

        message: dict[str, str] = {
            'channel': self.channel.name,
            'message': message
        }

        await SOCKET.send(f'MSG {json.dumps(message)}')

    async def ping() -> None:
        await SOCKET.send(f'PIN')


class Parser:
    templates: dict[str, str | list[dict[str, complex]]] = {
        'buy': [
            {
                'name': 'upgrade',
                'type': str,
                'one_of': {
                    'perk': 1,
                    'stat': 1,
                    'ability': 1
                }
            },
            {
                'name': 'amount',
                'type': int,
                'optional': True
            },
            {
                'name': 'selection',
                'type': str,
                'multi': True
            },
        ],
        'challenge': [
            {
                'name': 'character',
                'type': list,
                'multi': True
            }
        ],
        'help': [
            {
                'name': 'sub_command',
                'type': str
            }
        ],
        'badge': [
            {
                'name': 'badge',
                'type': str,
                'multi': True
            }
        ],
        'sheet': [
            {
                'name': 'character',
                'type': str,
                'last': True
            }
        ],
        'target': [
            {
                'name': 'character',
                'type': str,
                'last': False
            },
            {
                'name': 'ability',
                'type': str,
            }
        ],
        'action': [
            {
                'name': 'action',
                'type': str
            }
        ],
        'yeetus': '',
        'yeeted': '',
        'logs': [
            {
                'name': 'amount',
                'type': int,
                'optional': True
            }
        ]
    }

    @staticmethod
    async def __parse(
        message: str
    ) -> bool | dict[str, str | list[str]]:
        exploded: list[str] = message.split(' ')
        command: str = exploded.pop(0)
        template: list = Parser.templates.get(command)
        built_args: dict[str, str | list[str]] = {
            'command': command
        }
        if not template:
            built_args['error'] = 'Unrecognized command.'
            return built_args
        while True:
            try:
                exploded.remove('')
            except ValueError:
                break
        for idx in range(len(template)):
            buffer: str = ' '.join(exploded)
            arg: dict = template[idx]
            name: str = arg.get('name')
            T = arg.get('type')
            if not buffer and not arg.get('optional'):
                built_args['error'] = (
                    'Missing required parameter "' +
                    arg.name + '".'
                )
                return built_args
            if arg.get('one of'):
                expects: list = arg.get('one of')
                first: str = exploded[0].lower()
                if not expects[first] and not arg.get('optional'):
                    built_args['error'] = (
                        f'Invalid argument "{name}", ' +
                        'must be one of: ' + ', '.join(expects) + '.'
                    )
                    return built_args
                built_args[name] = first
            if arg.get('multi'):
                if T == list:
                    exploded = re.split('[ ]?,[ ]?', buffer)
                    built_args[name] = exploded
                    break
                built_args[name] = buffer
                break
            if T == int and arg.get('optional'):
                if re.match('^[0-9]+$', exploded[0]):
                    built_args[name] = T(exploded.pop(0))
                continue
            if name == 'character':
                if arg.get('last'):
                    built_args[name] = buffer
                    break
                exploded = re.split('[ ]?,[ ]?', buffer)
                character: str = exploded.pop(0)
                built_args[name] = character
                continue
            built_args[name] = exploded.pop(0)
        return built_args

    @staticmethod
    @default
    async def parse(_T):
        raise NotImplemented

    @staticmethod
    @parse.register
    async def parse(
        message: str,
        by: Character
    ) -> complex:
        built = Parser.__parse(message)
        built['by'] = by
        return built

    @staticmethod
    @parse.register
    async def parse(
        message: str,
        by: Character,
        chan: Channel
    ) -> complex:
        built = Parser.__parse(message)
        built['by'] = by
        built['channel'] = chan
        return built


class Command:
    states: dict = {
        'yeeted': 0
    }

    logs_help: str = 'A log of moderation actions that the bot has taken.'

    @staticmethod
    async def logs(
        amount: int,
        output: Output,
        by: Character,
        **kwargs
    ) -> None:
        chan: Channel = get_chan('ADH-04ef230936a847d576fa')
        out_str: str = '[spoiler]'

        if not chan.is_op(by.name):
            return

        logs: list[ModLog] = MOD_LOGS[:amount]
        amount = len(logs)

        for idx in range(amount):
            act: ModLog = logs[idx]
            out_str += f'[b]{idx}:[/b] target: [user]{act.character}[/user]\n'
            out_str += f'    type: [b]{act.type}[/b]\n'
            out_str += f'    action: [b]{act.action}[/b]\n'
            out_str += f'    when: [i]{get_time_str(act.at)} ago[/i]\n'
            out_str += f'    reason: [i]{act.reason}[/i]\n'

        out_str = out_str[:len(out_str) - 1] + '[/spoiler]'

        await output.send(
            (
                f'Log for the last [b]{amount}[/b] moderation actions:\n' +
                out_str
            )
        )

    yeeted_help: str = 'Let me show you my kill count. >:3~'

    @staticmethod
    async def yeeted(
        chan: Channel,
        output: Output,
        **kwargs
    ) -> None:
        time_last: int = chan.states.get('last', 0)
        time_diff_state: int = int(time()) - time_last

        unique_kills: int = len(KILLS.keys())
        kills: int = sum(KILLS.values())

        if not chan or time_diff_state < COMMAND_TIMEOUT:
            return

        chan.states['last'] = int(time())

        time_string: str = 'within the last [i]'
        time_string += get_time_str(UPTIME)
        time_string += '.[/i] [sup]:>~[/sup]'

        await output.send(
            (
                f'I have bounced [b]{unique_kills}[/b] unique character(s) ' +
                f'a total of [b]{kills}[/b] time(s) ' +
                time_string
            )
        )

    yeetus_help: str = 'Gotta protect the kids from themselves. :>~'

    @staticmethod
    async def yeetus(
        by: Character,
        chan: Channel,
        output: Output
    ) -> None:

        if not chan:
            return

        if not chan.is_op(by.name):
            return

        NEW_STATE: bool = not chan.states.get('yeetus', True)
        chan.states['yeetus'] = NEW_STATE

        if NEW_STATE:
            await output.send(
                f'You got it, [b]{by.name}[/b]!' +
                ' Yeet mode [i]engaged[/i].'
            )
        else:
            await output.send(
                f'You got it, [b]{by.name}[/b]!' +
                ' Yeet mode [i]disengaged[/i].'
            )


async def main() -> None:
    await SOCKET.start()


if __name__ == '__main__':
    asyncio.run(main())
