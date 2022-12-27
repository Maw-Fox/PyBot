import asyncio
import json
import requests
import os

from time import time
from math import floor
from websockets.client import connect
from modules.config import CONFIG
from modules.auth import AUTH
from modules.channel import Channel
from modules.character import Character
from modules.utils import log, age_tester, get_char, get_chan, remove_all
from modules.queue import Queue
from modules.commands import BotCommand, BOT_COMMANDS
from modules.shared import UPTIME, COMMAND_TIMEOUT

URL_DOMAIN: str = 'https://www.f-list.net'
URL_PROFILE_API: str = f'{URL_DOMAIN}/json/api/character-data.php'
WS_URI: str = 'wss://chat.f-list.net/chat2'
PATH_CWD: str = os.getcwd()

KILLS: dict[Character, int] = {}


class Socket:
    def __init__(self) -> None:
        self.current = None
        self.initialized: bool = False

    async def read(self, code, data) -> None:
        if hasattr(Response, code):
            if code != 'FLN' and code != 'LIS' and code != 'NLN':
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
                        AUTH.check_ticket()
                    await self.read(code, data)
                except Exception as error:
                    log('WEB/ERR', str(error))

    async def close(self) -> None:
        await self.current.close()


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
            chan.add_op(get_char(char_str))

    async def JCH(data) -> None:
        char: Character = get_char(data['character']['identity'])
        chan: Channel = get_chan(data['channel'])

        if not chan:
            chan: Channel = Channel(data['channel'])

        chan.add_char(char)

        if not BOT_COMMANDS['yeetus'].state.get(chan.name):
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
            return log('JCH/DBG', response)

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
                    'If you were kicked from Anal Addicts, by this bot, ' +
                    'I would suggest not joining on this character again!'
                )
            )

        exploded: list[str] = message[1:].split(' ')
        command: str = exploded[0]
        args: str = ''

        if len(exploded) > 1:
            exploded.pop(0)
            args = ' '.join(exploded)

        extras = {
            'params': args,
            'from': char.name,
            'channel': ''
        }

        if not BOT_COMMANDS.get(command):
            return await output.send(
                f'Unknown command "[b]{command}[/b]", type \'[i]!help[/i]\' ',
                'for a list of commands.'
            )

        await BOT_COMMANDS.get(command).solver(extras)

    async def MSG(data) -> None:
        message: str = data['message']
        char: Character = get_char(data['character'])
        chan: Channel = get_chan(data['channel'])

        if message[:1] != '!':
            return

        exploded: list[str] = message[1:].split(' ')
        command: str = exploded[0]
        args: str = ''

        if len(exploded) > 1:
            exploded.pop(0)
            args = ' '.join(exploded)

        extras = {
            'params': args,
            'from': char.name,
            'channel': chan.name
        }

        if not BOT_COMMANDS.get(command):
            return

        await BOT_COMMANDS.get(command).solver(extras)


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


def propagate_commands() -> None:
    async def yeeted(args) -> None:
        chan: Channel = get_chan(args['channel'])
        output: Output = Output(channel=chan)
        current_time: int = int(time())
        time_diff_state: int = int(time()) - BOT_COMMANDS['yeeted'].state['l']
        time_diff: int = current_time - UPTIME
        time_days: int = floor(time_diff / 86400)
        time_hours: int = floor((time_diff % 86400) / 3600)
        time_minutes: int = floor((time_diff % 3600) / 60)
        time_seconds: int = floor(time_diff % 60)

        unique_kills: int = len(KILLS.keys())
        kills: int = sum(KILLS.values())

        if not chan or time_diff_state < COMMAND_TIMEOUT:
            return

        BOT_COMMANDS['yeeted'].state['l'] = int(time())

        time_string: str = 'within the last [i]'
        time_string += f'{time_days} day(s), ' if time_days else ''
        time_string += f'{time_hours} hour(s), ' if time_hours else ''
        time_string += f'{time_minutes} minute(s), ' if time_minutes else ''
        time_string += f'{time_seconds} second(s), ' if time_seconds else ''
        time_string = time_string[:len(time_string) - 2]
        time_string += '.[/i] [sup]:>~[/sup]'

        await output.send(
            (
                f'I have bounced [b]{unique_kills}[/b] unique character(s) ' +
                f'a total of [b]{kills}[/b] time(s) ' +
                time_string
            )
        )

    cmd = BotCommand(
        'yeeted',
        yeeted,
        'Let me show you my kill count. >:3~',
        state=0
    )

    async def yeetus(args) -> None:
        chan: Channel = get_chan(args['channel'])
        char: Character = get_char(args['from'])

        output: Output = Output(channel=chan)

        if not chan:
            return

        if not (
            chan.ops.get(char)
        ):
            return

        NEW_STATE: bool = not BOT_COMMANDS['yeetus'].state.get(chan.name, None)
        BOT_COMMANDS['yeetus'].state[chan.name] = NEW_STATE

        if NEW_STATE:
            await output.send(
                f'You got it, [b]{char.name}[/b]!' +
                ' Yeet mode [i]engaged[/i].'
            )
        else:
            await output.send(
                f'You got it, [b]{char.name}[/b]!' +
                ' Yeet mode [i]disengaged[/i].'
            )

    BotCommand(
        'yeetus',
        yeetus,
        'Gotta protect the kids from themselves. :>~',
        state={}
    )

    for chan_str in CONFIG.joined_channels:
        cmd.state[chan_str] = False

    """
    async def help(args) -> None:
        output = get_output(args)
        params: str = args['params']
        out_str = '[b]List of available commands:[/b]\n'

        if not params:
            for cmd_name in BOT_COMMANDS:
                command = BOT_COMMANDS[cmd_name]
                out_str += f'[i]{command.command_name}[/i],'

            out_str = out_str[:len(out_str) - 1]
            return await output.send(out_str)

        params: list[str] = get_params(params, 1)
        subcommand: str = params[0]

        if not hasattr(BOT_COMMANDS, args.subcommand):
            return await output.send(out_str)

        await output.send(
            BOT_COMMANDS[subcommand].help
        )

    BotCommand(
        'help',
        help,
        cat(
            'Insert witty joke about recursion here, or the fact I can no ',
            'longer actually help you if you need help about the help ',
            'function itself. :>~'
        )
    )

    async def die(args) -> None:
        output = get_output(args)
        by: str = args['from']
        print('ding')
        if by != 'Kali':
            return await output.send(
                'No u. :>~\n[color=red][b]A C C E S S   D E N I E D',
                '[/b][/color]'
            )

        await output.send(
            '/me dies. [sub]X>~[/sub]'
        )
        system.exit(1)

    BotCommand(
        'die',
        die,
        'Kill the bot. Before you event try: [b]no[/b], you can\'t. :>~'
    )

    async def hp(args) -> None:
        output = get_output(args)

    BotCommand(
        'hp',
        hp,
        'HP bar formatter.'
    )
    """


propagate_commands()


async def main() -> None:
    await SOCKET.start()


if __name__ == '__main__':
    asyncio.run(main())
