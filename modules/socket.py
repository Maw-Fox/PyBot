import json
from time import time
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed
from websockets.client import connect

from modules.config import CONFIG
from modules.auth import AUTH
from modules.channel import Channel, CHANNELS, remove_from_all_channels
from modules.command import BOT_COMMANDS
from modules.utils import cat
from modules.constants import WS_URI


class Queue:
    last: float = time()
    throttle: float = 2e3

    def __init__(self, callback, data):
        self.data = data
        self.callback = callback
        queue.append(self)

    async def run(self) -> None:
        queue.pop(queue.index(self))
        await self.callback(**self.data)

    async def cycle() -> None:
        if len(queue) and time() - Queue.last > Queue.throttle:
            queue.pop().run()


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
                        for c in CONFIG.joined_channels:
                            await websocket.send(cat(
                                'JCH ',
                                f'{json.dumps({"channel": c})}'
                            ))
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
            ch = Channel(**data['channels'][i])
            setattr(CHANNELS, ch.channel, ch)

    async def ICH(data) -> None:
        c = Channel(data['channel'])
        CHANNELS[c.channel] = c

        for user in data['users']:
            c.add_user(user['identity'])

    async def JCH(data) -> None:
        CHANNELS[data['channel']].add_user(data['character']['identity'])

    async def FLN(data) -> None:
        remove_from_all_channels(data['character'])

    async def LCH(data) -> None:
        CHANNELS[data['channel']].remove_user(data['character'])

    async def PIN(data) -> None:
        print(json.dumps(CHANNELS))
        print('Pongers')
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
            'sender': character
        }

        print(extras)

        if not BOT_COMMANDS.get(command):
            return await output.send(
                f'Unknown command "[b]{command}[/b]", type \'[i]!help[/i]\' ',
                'for a list of commands.'
            )

        await BOT_COMMANDS.get(command).solver(extras)


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
        if time() - Queue.last < Queue.throttle:
            Queue(self.__send_private, message)
            return

        Queue.last = time()

        message: dict[str, str] = {
            'recipient': self.recipient,
            'message': cat(message)
        }

        await SOCKET.send(f'PRI {json.dumps(message)}')

    async def __send_channel(self, *message) -> None:
        if time() - Queue.last < Queue.throttle:
            Queue(self.__send_channel, message)
            return

        Queue.last = time()

        message: dict[str, str] = {
            'channel': self.channel,
            'message': cat(message)
        }

        await SOCKET.send(f'MSG {json.dumps(message)}')

    async def ping() -> None:
        await SOCKET.send(f'PIN')


SOCKET: Socket = Socket()