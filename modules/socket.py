import json
import requests
import re

from urllib.parse import quote
from time import time
from websockets.client import connect
from modules.config import CONFIG
from modules.auth import AUTH
from modules.command import BotCommand, BOT_COMMANDS, BOT_STATES
from modules.channel import Channel, CHANNELS, remove_from_all_channels
from modules.utils import cat
from modules.constants import WS_URI, URL_PROFILE_API, URL_CHARACTER


class Queue:
    last: float = time()
    throttle: float = 2.0

    def __init__(self, callback, data) -> None:
        self.data = data
        self.callback = callback
        queue.append(self)

    async def run(self) -> None:
        await self.callback(self.data)

    async def cycle() -> None:
        if len(queue) and time() - Queue.last > Queue.throttle:
            await queue.pop().run()


queue: list[Queue] = []


class Socket:
    def __init__(self) -> None:
        self.current = None
        self.initialized = False

    async def read(self, code, data) -> None:
        if hasattr(Response, code):
            print(f'[{int(time())}]: ', code, data)
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
                        # Check ticket timer with every PIN
                        # +GC
                        AUTH.check_ticket()
                    await self.read(code, data)
                except Exception as error:
                    print(str(error))

    async def close(self) -> None:
        await self.current.close()


class Response:
    async def ERR(data) -> None:
        print(f'ERR: {json.dumps(data)}')

    async def ORS(data) -> None:
        for i in data['channels']:
            channel_inst = Channel(**data['channels'][i])
            CHANNELS[channel_inst.channel] = channel_inst

    async def ICH(data) -> None:
        if hasattr(CHANNELS, data['channel']):
            channel_inst: Channel = CHANNELS[data['channel']]
        else:
            channel_inst: Channel = Channel(data['channel'])
            CHANNELS[data['channel']] = channel_inst
        channel: str = channel_inst.channel

        parameters: str = json.dumps(
            {
                'channel': channel
            }
        )

        Queue(
            SOCKET.current.send,
            f'COL {parameters}'
        )

        for user in data['users']:
            channel_inst.add_user(user['identity'])

    async def JCH(data) -> None:
        character: str = data['character']['identity']
        channel: str = data['channel']

        params = {
            'account': CONFIG.account_name,
            'ticket': AUTH.auth_key,
            'name': character,
        }

        if hasattr(CHANNELS, channel):
            channel_inst: Channel = CHANNELS[channel]
        else:
            channel_inst: Channel = Channel(channel)
            CHANNELS[channel] = channel_inst

        channel_inst.add_user(character)

        if not BOT_STATES['yeetus'][channel]:
            return

        response = requests.post(
            'https://www.f-list.net/json/api/character-data.php',
            data=params
        )
        response = json.loads(response.text)

        vis: str = response['infotags'].get('64')
        age: str = response['infotags'].get('1')

        age_valid: re.Match = re.match('^[0-9]+$', age)
        vis_valid: re.Match = re.match('^[0-9]+$', vis)

        parameters: dict[str, str] = {
            'channel': channel,
            'character': character
        }
        print(parameters)
#        print(CHANNELS[channel].ops)
#        try:
#            CHANNELS[channel].ops.index(CONFIG.bot_name)
#        except ValueError as err:
#            print(err)
#            return
        print(age, vis)
        if age_valid:
            age = int(age, base=10)
            if age > 0 and age < 18:
                return await SOCKET.send('CKU', parameters)

        if vis_valid:
            vis = int(vis, base=10)
            if vis > 0 and vis < 18:
                return await SOCKET.send('CKU', parameters)

    async def SYS(data) -> None:
        print(data)
        if data['message'] and 'Channel moderator' in data['message']:
            channel_inst: Channel = CHANNELS[data['channel']]
            msg: str = data['message']
            msg = msg[msg.find(': ') + 2:]
            msg = msg.replace(' ', '')
            op_list: list[str] = msg.split(',')

            for op in op_list:
                CHANNELS[channel_inst.channel].ops.append(op)

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
                'I am a [b]bot[/b] and not a real person.'
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

        if not BOT_COMMANDS[command]:
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
        output = Output(channel=channel)

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

        print(extras)

        try:
            channel_inst.ops.index(character)
        except ValueError:
            return
        print(command)

        if not BOT_COMMANDS[command]:
            return
#            return await output.send(
#                f'Unknown command "[b]{command}[/b]".'
#                # ', type \'[i]!help[/i]\' for a list of commands.'
#            )

        await BOT_COMMANDS[command].solver(extras)


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
        print(time() - Queue.last, Queue.throttle)
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


def propagate_commands() -> None:
    async def yeetus(args) -> None:
        channel: str = args['channel']
        by: str = args['from']

        if not channel:
            return

        output = Output(channel=channel)

        channel_inst: Channel = CHANNELS[channel]
        try:
            channel_inst.ops.index(by)
        except ValueError:
            return

        if not BOT_STATES['yeetus'][channel]:
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


SOCKET: Socket = Socket()
