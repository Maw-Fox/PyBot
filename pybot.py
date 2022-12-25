import asyncio
import json
import requests
import re
import os

from time import time
from websockets.client import connect
from modules.config import CONFIG
from modules.auth import AUTH
from modules.user import User, GLOBAL_USER_LIST
from modules.utils import cat, log, age_tester

BOT_STATES: dict[str, dict] = {}
URL_DOMAIN: str = 'https://www.f-list.net'
URL_PROFILE_API: str = f'{URL_DOMAIN}/json/api/character-data.php'
WS_URI: str = 'wss://chat.f-list.net/chat2'
PATH_CWD: str = os.getcwd()

GLOBAL_OPS: list[str] = []


class Channel:
    def __init__(
        self,
        name: str
    ) -> None:
        self.channel = name
        self.title = name
        self.users: dict[str, bool] = {}
        self.ops: dict[str, bool] = {}

    def remove_user(self, user: str) -> None:
        if not self.users.get(user):
            return
        self.users.pop(user)

    def add_user(self, user: str) -> None:
        self.users[user] = True

    def add_op(self, user: str) -> None:
        self.ops[user] = True

    def remove_op(self, user: str) -> None:
        self.ops.pop(user)


CHANNELS: dict[str, Channel] = {}


class Queue:
    last: float = time()
    throttle: float = 2.0

    def __init__(self, callback, data) -> None:
        self.data = data
        self.callback = callback
        QUEUE.append(self)

    async def run(self) -> None:
        await self.callback(self.data)

    async def cycle() -> None:
        if len(QUEUE) and time() - Queue.last > Queue.throttle:
            await QUEUE.pop().run()


QUEUE: list[Queue] = []


class Socket:
    def __init__(self) -> None:
        self.current = None
        self.initialized = False

    async def read(self, code, data) -> None:
        if hasattr(Response, code):
            if code != 'FLN':
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
            channel_data: dict = data['channels'][i]
            CHANNELS[channel_data['name']] = Channel(**channel_data)

    async def ICH(data) -> None:
        channel: str = data['channel']

        if not CHANNELS.get(channel):
            CHANNELS[data['channel']] = Channel(data['channel'])

        channel_inst: Channel = CHANNELS[data['channel']]

        Queue(
            SOCKET.current.send,
            f'COL ' + json.dumps({'channel': channel})
        )

        for user in data['users']:
            channel_inst.add_user(user['identity'])

    async def JCH(data) -> None:
        character: str = data['character']['identity']
        channel: str = data['channel']

        if not CHANNELS.get(channel):
            CHANNELS[channel] = Channel(channel)

        channel_inst: Channel = CHANNELS[channel]
        channel_inst.add_user(character)

        # if not BOT_STATES['yeetus'].get(channel):
        #    return
        # '0.0.0.0:80' http/https
        # Mozilla/5.0 (Windows NT 10.0; Win64; x64;
        # rv:106.0) Gecko/20100101 Firefox/106.0
        headers = {
            'User-Agent': cat(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; ',
                'rv:106.0) Gecko/20100101 Firefox/106.0'
            ),
            'Referrer': 'https://chat.f-list.net'
        }

        response = requests.post(
            'https://www.f-list.net/json/api/character-data.php',
            data={
                'account': CONFIG.account_name,
                'ticket': AUTH.auth_key,
                'name': character,
            },
            headers={
                'User-Agent': cat(
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; ',
                    'rv:106.0) Gecko/20100101 Firefox/106.0'
                ),
                'Referrer': 'https://chat.f-list.net'
            },
            proxies={
                'http': '0.0.0.0:80',
                'https': '0.0.0.0:80'
            }
        )
        response = json.loads(response.text)
        log('JCH/DBG', response)
        vis: str = response['infotags'].get('64', '')
        age: str = response['infotags'].get('1', '')
        bad_age: bool = age_tester(age)
        bad_vis: bool = age_tester(vis)

        if bad_age or bad_vis:
            age = f'[{age}]' if bad_age else age
            vis = f'[{vis}]' if bad_vis else vis

            log('JCH/DBG', f'Kick {character}, age:{age}, visual:{vis}', io=0)
#            return await SOCKET.send(
#                'CKU',
#                {
#                    'channel': channel,
#                    'character': character
#                }
#            )

    async def SYS(data) -> None:
        log('SYS/DAT', data)
        if data['message'] and 'Channel moderator' in data['message']:
            channel_inst: Channel = CHANNELS[data['channel']]
            msg: str = data['message']
            msg = msg[msg.find(': ') + 2:]
            msg = msg.replace(' ', '')
            op_list: list[str] = msg.split(',')

            for op in op_list:
                channel_inst.ops[op] = True

    async def FLN(data) -> None:
        remove_from_all_channels(data['character'])

    async def LCH(data) -> None:
        CHANNELS[data['channel']].remove_user(data['character'])

    async def PIN(data) -> None:
        await Output.ping()

    async def PRI(data) -> None:
        message: str = data['message']
        character: str = data['character']
        output = Output(recipient=character)

        if message[:1] != '!':
            return await output.send(
                cat(
                    'I am a [b]bot[/b] and not a real person.\n\n'
                    'If you were kicked from Anal Addicts, by this bot, ',
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
            'from': character,
            'channel': ''
        }

        if not BOT_COMMANDS.get(command):
            return await output.send(
                f'Unknown command "[b]{command}[/b]", type \'[i]!help[/i]\' ',
                'for a list of commands.'
            )

        await BOT_COMMANDS[command].solver(extras)

    async def MSG(data) -> None:
        message: str = data['message']
        character: str = data['character']
        channel = data['channel']
        channel_inst: Channel = CHANNELS[channel]

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
            'from': character,
            'channel': channel
        }

        if not channel_inst.ops.get(character):
            return

        if not BOT_COMMANDS.get(command):
            return

        await BOT_COMMANDS[command].solver(extras)


SOCKET: Socket = Socket()


class BotCommand():
    def __init__(
        self,
        command_name: str,
        solver,
        help: str
    ) -> None:
        self.command_name = command_name
        self.solver = solver
        self.help = help


BOT_COMMANDS: dict[str, BotCommand] = {}


class Output:
    def __init__(
        self,
        message: str = '',
        recipient: str = None,
        channel: str = None,
    ) -> None:
        self.message = message
        self.channel = channel
        self.recipient = recipient

        if recipient:
            self.send = self.__send_private
            return

        self.send = self.__send_channel

    async def __send_private(self, *message) -> None:
        log('SEN/PRI', time() - Queue.last, Queue.throttle, suffix='TS:', io=0)
        if time() - Queue.last < Queue.throttle:
            Queue(self.__send_private, message)
            return

        Queue.last = time()

        message: dict[str, str] = {
            'recipient': self.recipient,
            'message': cat(*message)
        }

        await SOCKET.send(f'PRI {json.dumps(message)}')

    async def __send_channel(self, *message) -> None:
        log('SEN/MSG', time() - Queue.last, Queue.throttle, suffix='TS:', io=0)
        if time() - Queue.last < Queue.throttle:
            Queue(self.__send_channel, message)
            return

        Queue.last = time()

        message: dict[str, str] = {
            'channel': self.channel,
            'message': cat(*message)
        }

        await SOCKET.send(f'MSG {json.dumps(message)}')

    async def ping() -> None:
        await SOCKET.send(f'PIN')


def remove_from_all_channels(user: str) -> None:
    for c_name in CHANNELS:
        CHANNELS[c_name].remove_user(user)


def propagate_commands() -> None:
    async def yeetus(args) -> None:
        channel: str = args['channel']
        channel_inst: Channel = CHANNELS[channel]
        by: str = args['from']

        if not channel:
            return

        output = Output(channel=channel)

        if not (
            channel_inst.ops.get(by) and channel_inst.ops.get(CONFIG.bot_name)
        ):
            return

        if not BOT_STATES['yeetus'].get(channel):
            BOT_STATES['yeetus'][channel] = False

        NEW_STATE: bool = not BOT_STATES['yeetus'][channel]
        BOT_STATES['yeetus'][channel] = NEW_STATE

        if NEW_STATE:
            await output.send(
                f'You got it, [b]{by}[/b]!',
                ' Yeet mode [i]engaged[/i].'
            )
        else:
            await output.send(
                f'You got it, [b]{by}[/b]!',
                ' Yeet mode [i]disengaged[/i].'
            )

    cmd = BotCommand(
        'yeetus',
        yeetus,
        'Gotta protect the kids from themselves. :>~'
    )
    BOT_COMMANDS['yeetus'] = cmd
    BOT_STATES['yeetus'] = {}

    for channel in CONFIG.joined_channels:
        BOT_STATES['yeetus'][channel] = False

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
