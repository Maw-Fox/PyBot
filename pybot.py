import asyncio
import json
import requests
import re
import os

from time import time
from websockets.client import connect
from modules.config import CONFIG
from modules.auth import AUTH
from modules.utils import cat
from modules.shared import JANK_TO_ASCII_TABLE, SIMILARITY_TESTS, WRITTEN_AGES

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
                print(f'[{int(time())}]:INBOUND<< ', code, data)
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
                    print(f'[{int(time())}]:WEB/ERR<< {str(error)}')

    async def close(self) -> None:
        await self.current.close()


class Response:
    async def ERR(data) -> None:
        print(f'[{int(time())}]:ERR/ANY<< {json.dumps(data)}')

    async def ORS(data) -> None:
        for i in data['channels']:
            cur_ch: dict = data['channels'][i]
            CHANNELS[cur_ch['name']] = Channel(**cur_ch)

    async def ICH(data) -> None:
        channel: str = data['channel']

        if not CHANNELS.get(channel):
            CHANNELS[data['channel']] = Channel(data['channel'])

        channel_inst: Channel = CHANNELS[data['channel']]

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

        if not CHANNELS.get(channel):
            CHANNELS[channel] = Channel(channel)

        channel_inst: Channel = CHANNELS[channel]
        channel_inst.add_user(character)

        if not BOT_STATES['yeetus'].get(channel):
            return

        response = requests.post(
            'https://www.f-list.net/json/api/character-data.php',
            data=params
        )

        response = json.loads(response.text)

        print(f'[{int(time())}]:JCH/DBG<< ', json.dumps(response['infotags']))

        vis: str = response['infotags'].get('64')
        age: str = response['infotags'].get('1')
        vis_valid: bool = False
        age_valid: bool = False

        parameters: dict[str, str] = {
            'channel': channel,
            'character': character
        }

        if age_tester(age) or age_tester(vis):
            print(
                cat(
                    f'[{int(time())}]:JCH/DBG>> Kicked {character},',
                    f' age:{age}, visual:{vis}'
                )
            )
            return

        # print(f'[{int(time())}]:JCH/DBG<< OPS:', CHANNELS[channel].ops)
#        try:
#            CHANNELS[channel].ops.index(CONFIG.bot_name)
#        except ValueError as err:
#            print(err)
#            return
        # print(age, vis)
        if age_valid:
            age = int(age, base=10)
            if age > 5 and age < 18:
                print(
                    cat(
                        f'[{int(time())}]:JCH/DBG>> Kicked {character},',
                        f' age:{age}, visual:{vis}'
                    )
                )
                return await SOCKET.send('CKU', parameters)

        if vis_valid:
            vis = int(vis, base=10)
            if vis > 5 and vis < 18:
                print(
                    cat(
                        f'[{int(time())}]:JCH/DBG>> Kicked {character},',
                        f' age:{age}, visual:{vis}'
                    )
                )
                return await SOCKET.send('CKU', parameters)

    async def SYS(data) -> None:
        print(f'[{int(time())}]:SYS/DAT<<', data)
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

        # print(f'[{int(time())}]:MSG/DBG<< ARGS:', extras)
        if not channel_inst.ops.get(character):
            return

        # print(f'[{int(time())}]:MSG/DBG<< CMD:', command)

        if not BOT_COMMANDS.get(command):
            return
#            return await output.send(
#                f'Unknown command "[b]{command}[/b]".'
#                # ', type \'[i]!help[/i]\' for a list of commands.'
#            )

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
        print(
            f'[{int(time())}]:SEN/PRI>> TS:',
            time() - Queue.last,
            Queue.throttle
        )
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
        print(
            f'[{int(time())}]:SEN/CHA>> TS:',
            time() - Queue.last,
            Queue.throttle
        )
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


# Yeah, nice try nerds. :)
def jank_to_ascii(sanitize_me: str) -> str:
    buffer: str = sanitize_me
    # cycle through ascii table, do substitutions.
    for to_rep in JANK_TO_ASCII_TABLE:
        to_sub: str = JANK_TO_ASCII_TABLE[to_rep]
        buffer = re.sub(f'[{to_sub}]', to_rep, buffer)
    # clean out the non-ascii characters
    buffer = re.sub('[^a-z0-9]', '', buffer)
    return buffer


def is_written_taboo(s: str) -> bool:
    for age in WRITTEN_AGES:
        if age in s:
            return True
    return False


def age_tester(test_me: str) -> bool:
    buffer: str = re.sub('[^a-zA-Z0-9]', '', test_me)
    buffer = jank_to_ascii(test_me)
    buffer = buffer.lower()
    if is_written_taboo(buffer):
        return True
    if re.match('^[0-9]+$', buffer):
        age: int = int(buffer, base=10)
        if age < 18 and age > 5:
            return True
    return False


def test_tester() -> None:
    for string in SIMILARITY_TESTS:
        if age_tester(string):
            print('age tester test passed!')
        else:
            print('age tester test failed.')


def propagate_commands() -> None:
    async def yeetus(args) -> None:
        channel: str = args['channel']
        channel_inst: Channel = CHANNELS[channel]
        by: str = args['from']

        if not channel:
            return

        output = Output(channel=channel)

        if not (
            channel_inst.ops.get(by) or channel_inst.ops.get(CONFIG.bot_name)
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
