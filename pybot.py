import asyncio
import json
import requests
import os
import re

import modules.hungry as H
from hashlib import md5
from time import time
from math import floor
from websockets.client import connect
from modules.config import CONFIG
from modules.auth import AUTH
from modules.channel import Channel
from modules.character import Character
from modules.utils import log, age_tester, get_char, get_chan, remove_all
from modules.queue import Queue
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
    'every': 300,
    'clear': 300
}


def get_exists() -> dict[str, list[str | int]]:
    obj: dict[str, list[str | int]] = {}
    f = open('data/eicon_db.csv', 'r', encoding='utf-8')
    lines: list[str] = f.read().split('\n')
    for line in lines:
        name, extension, last_verified, uses = line.split(',')
        obj[name] = [name, extension, int(last_verified), int(uses)]
    return obj


class Verify:
    HASH_404: str = 'c9e84fc18b21d3cb955340909c5b369c'
    queue: list = []
    save: float = time() + 3600.0
    exists: dict[str, list[str | int]] = get_exists()

    def __init__(self, check: str):
        self.check: str = check.lower()
        Verify.queue.append(self)

    def do(self) -> None:
        response = requests.get(
            f'https://static.f-list.net/images/eicon/{self.check}.gif'
        )

        file_hash: str = md5(
            response.content, usedforsecurity=False
        ).hexdigest()

        if file_hash == Verify.HASH_404:
            # This file is a 404 redirect.
            return

        mime: str = response.headers.get('content-type')
        mime = mime.split('/')[1]
        log(
            'IDB/ADD',
            f'SAV:T{int(int(time()) - Verify.save)}  >>',
            f'{self.check}.{mime}'
        )
        Verify.exists[self.check] = [self.check, mime, int(time()), 1]

    @staticmethod
    def cycle(force: bool = False) -> None:
        t: float = time()
        if t > Verify.save or force:
            log('IDB/SAV', f'NEW_DB_SIZE: {len(Verify.exists)}')
            Verify.save = t + 3600.0
            # Sort by alphabetical first as a secondary sort
            # for the upcomming popularity sort
            Verify.exists: dict[str, list[str | int]] = dict(
                sorted(
                    Verify.exists.items(),
                    key=lambda x: x[0]
                )
            )
            # Popularity sort, the primary sort category
            Verify.exists: dict[str, list[str | int]] = dict(
                sorted(
                    Verify.exists.items(),
                    key=lambda x: x[1][3],
                    reverse=True
                )
            )
        f = open('data/eicon_db.csv', 'w', encoding='utf-8')
        f.write(
            '\n'.join(
                [f'{w},{x},{y},{z}' for w, x, y, z in Verify.exists.values()]
            )
        )
        f.close()
        if not len(Verify.queue):
            return
        Verify.queue.pop(0).do()


class Socket:
    def __init__(self) -> None:
        self.current = None
        self.initialized: bool = False

    async def read(self, code, data) -> None:
        watch: dict[str, int] = {}
        if hasattr(Response, code):
            if watch.get(code, 0):
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
                    Verify.cycle()
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
                        t: int = int(time())
                        AUTH.check_ticket()
                        H.Game.check_save(t)
                        if t - CHECK['last'] > CHECK['every']:
                            for char in KILLS_LAST.copy():
                                ts: int = KILLS_LAST[char]
                                if ts < t - CHECK['clear']:
                                    KILLS_LAST.pop(char)
                            CHECK['last'] = t
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
    # user -> {channels, last}
    __CIU: dict[str, dict[str, int | list[str]]] = {}
    requester: str | None = None

    async def CIU(data) -> None:
        character_name: str = data['sender']
        output: Output = Output(recipient=character_name)
        t: int = int(time())
        char_data = Response.__CIU.get(character_name)
        if data['name'].lower()[:3] != 'adh':
            return await output(
                '[b]No.[/b]'
            )
        log('CHA/INV', data['sender'], data['name'])
        if char_data:
            last_t: int = char_data.get('last', t)
            channels: list[str] = char_data.get('channels')
            if data['name'] in channels:
                return await output(
                    'You\'ve tried this already, [b]no means no[/b].'
                )
            if t - last_t < 900:
                return await output(
                    'Please wait at least 15 minutes before attempting to ' +
                    'invite the bot again.'
                )
        Response.requester: str = data['sender']
        return await SOCKET.send(
            'JCH',
            {
                'channel': data['name']
            }
        )

    async def STA(data) -> None:
        if not data['statusmsg']:
            return
        matches: list[tuple[str, str, str]] = re.findall(
            '(\\[eicon\\])([^\\[\\]]+)(\\[/eicon\\])',
            data['statusmsg']
        )
        if not matches:
            return
        for m in matches:
            existing: tuple[str, str, int, int] = Verify.exists.get(m[1])
            if existing:
                existing[3] += 1
                continue
            Verify(m[1])

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

        if Response.requester:
            if chan.is_op(Response.requester):
                Response.requester = None
                return
            await Output(recipient=get_char(Response.requester)).send(
                'You are not an op in this channel and cannot invite the bot.'
            )
            chan.remove()
            Response.requester = None
            return await SOCKET.send(
                'LCH',
                {
                    'channel': chan.name
                }
            )

    async def JCH(data) -> None:
        char: Character = get_char(data['character']['identity'])
        chan: Channel = get_chan(data['channel'])

        chan.add_char(char)

        if not chan.states.get('yeetus', False) and (
            chan.name not in CONFIG.joined_channels
        ):
            return

        response = requests.post(
            'https://www.f-list.net/json/api/character-data.php',
            data={
                'account': CONFIG.account_name,
                'ticket': AUTH.auth_key,
                'name': char.name,
            }
        )

        if response.status_code != 200:
            # log(f'JCH/{response.status_code}')
            return

        response = json.loads(response.text)

        if not response.get('infotags'):
            # log('JCH/DBG', response)
            if 'Invalid ticket.' == response.get('error'):
                AUTH.get_new_auth_ticket()
            return

        vis: str = response['infotags'].get('64', '')
        age: str = response['infotags'].get('1', '')
        bad_age: bool = age_tester(age)
        bad_vis: bool = age_tester(vis)

        # log('JCH/DBG', vis, age)

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
            message=message[1:],
            by=char
        )
        log('PRI/INB', data)
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

        if not getattr(Command, (message[1:].split(' ')[0])):
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
    templates: dict[str, list] = H.DOC['syntax']

    @staticmethod
    def __parse(
        message: str
    ) -> bool | dict[str, str | list[str]]:
        exploded: list[str] = message.split(' ')
        command: str = exploded.pop(0)
        template: list = Parser.templates.get(command)
        built_args: dict[str, str | list[str]] = {
            'command': command,
            'error': ''
        }
        if type(template) != list:
            built_args['error'] = 'Unrecognized command.'
            return built_args

        if not len(template):
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
            if arg.get('prefix'):
                if arg.get('prefix') in exploded[0]:
                    built_args[name] = exploded.pop(0).replace(
                        arg.get('prefix'), ''
                    )
                    continue
                if not arg.get('optional'):
                    built_args['error'] = (
                        'Missing required parameter "' +
                        arg['name'] + '".'
                    )
                    break
                continue
            if not buffer and not arg.get('optional'):
                built_args['error'] = (
                    'Missing required parameter "' +
                    arg['name'] + '".'
                )
                return built_args
            if not buffer and arg.get('optional'):
                continue
            if arg.get('one of'):
                expects: list = arg.get('one of')
                first: str = exploded[0].lower()
                if first not in expects and not arg.get('optional'):
                    built_args['error'] = (
                        f'Invalid argument "{name}", ' +
                        'must be one of: ' + ', '.join(expects) + '.'
                    )
                    return built_args
                if first not in expects:
                    built_args[name] = ''
                    continue
                built_args[name] = first
            if arg.get('multi'):
                if T == 'list':
                    exploded = re.split('[ ]?,[ ]?', buffer)
                    built_args[name] = exploded
                    break
                built_args[name] = buffer
                break
            if T == "int" and arg.get('optional'):
                if re.match('^[0-9]+$', exploded[0]):
                    built_args[name] = max(int(exploded.pop(0)), 0)
                continue
            if name == 'character':
                if arg.get('last'):
                    built_args[name] = buffer
                    break
                exploded = re.split('[ ]?,[ ]?', buffer)
                character: str = exploded.pop(0)
                built_args[name] = character
                continue
            if not len(exploded):
                break
            built_args[name] = exploded.pop(0)
        return built_args

    @staticmethod
    def parse(
        message: str,
        by: Character,
        chan: Channel | None = None
    ) -> complex:
        built = Parser.__parse(message)
        built['by'] = by
        if chan:
            built['channel'] = chan
        return built


class Command:
    doc: dict[str, str] = H.DOC['help']

    doc['help'] = (
        '[b]Help:[/b] a list off commands are below, type "!help command" ' +
        'to see more information regarding these commands.\n' +
        '   [b]General:[/b]\n      ' +
        '   '.join([
            'logs', 'yeetus', 'yeeted', '[b]help[/b]', 'eicon'
        ]) + '\n'
        '   [b]Hungry Game:[/b]\n      ' +
        '   '.join([
            'hungry', 'create', 'buy', 'target', 'badge',
            'challenge', 'sheet', 'action', 'perks',
            'abilities', 'refund'
        ]) + '\n'
    )

    @staticmethod
    def __append_thing_info(thing_obj: dict) -> str:
        t_s: str = '\n   [b]Type[/b]\n      '
        t: str = thing_obj.get('type', '')
        h_s: str = '\n   [b]How[/b]:\n      '
        h: str = thing_obj.get('how', '')
        n_s: str = '\n   [b]Notes[/b]:\n      '
        n: str = thing_obj.get('notes', '')
        p_s: str = '\n    [b]Perks[/b]:\n      '
        p: str = thing_obj.get('perks', '')
        b_s: str = '\n   [b]Badge[/b]: '
        b: str = thing_obj.get('badge', '')
        ml_s: str = '\n   [b]Max Level[/b]: '
        ml: str = str(thing_obj.get('max_level', ''))
        c_s: str = '\n   [b]Cost[/b]: '
        c: str = str(thing_obj.get('cost', ''))
        return (
            (t_s + t if t else '') +
            (h_s + h if h else '') +
            (n_s + n if n else '') +
            (p_s + p if p else '') +
            (c_s + c if c else '') +
            (ml_s + ml if ml else '') +
            (b_s + b if b else '')
        )

    @staticmethod
    async def action(
        by: Character,
        action: str,
        channel: Channel,
        **kwargs
    ) -> None:
        action = action.lower()
        output_error: Output = Output(recipient=by)
        targets: list[H.Pred | H.Prey] = []
        char: H.Character = channel.hungry.get_ingame(by.name)
        game: H.Game = channel.hungry
        if not char:
            return await output_error.send(
                '[b]Hungry Game[/b]: You\'re not in this game!'
            )
        ability: H.Ability = char.abilities.get(action.lower())
        if not ability:
            return await output_error.send(
                '[b]Hungry Game[/b]: Invalid ability!'
            )
        if not game:
            return await output_error.send(
                '[b]Hungry Game[/b]: No ongoing game in this channel!'
            )
        if game.turn != char:
            return await output_error.send(
                '[b]Hungry Game[/b]: It\'s not your turn!'
            )
        if action == 'attack':
            if type(char) == H.Pred:
                for p in game.prey:
                    if p.deceased:
                        continue
                    targets.append(p)
            else:
                targets.append(game.pred)
        else:
            targets.append(char)
        await game.use_ability(char, ability, targets)

    @staticmethod
    async def target(
        by: Character,
        channel: Channel,
        ability: str,
        character: list[str],
        **kwargs
    ) -> None:
        ability = ability.lower()
        output_error: Output = Output(recipient=by)
        targets: list[H.Pred | H.Prey] = []
        char: H.Character = channel.hungry.get_ingame(by.name)
        game: H.Game = channel.hungry
        if not char:
            return await output_error.send(
                '[b]Hungry Game[/b]: You\'re not in this game!'
            )
        ability: H.Ability = char.abilities.get(ability.lower())
        if not ability:
            return await output_error.send(
                '[b]Hungry Game[/b]: Invalid ability!'
            )
        if not game:
            return await output_error.send(
                '[b]Hungry Game[/b]: No ongoing game in this channel!'
            )
        if game.turn != char:
            return await output_error.send(
                '[b]Hungry Game[/b]: It\'s not your turn!'
            )
        game.use_ability(char, ability, targets)

    @staticmethod
    async def accept(
        by: Character,
        **kwargs
    ) -> None:
        output: Output = Output(recipient=by)
        char: H.Character = H.Game.get_character(by.name)
        if not char:
            return await output.send(
                '[b]Hungry Game[/b]: You don\'t have a character sheet.'
            )
        setup: H.Setup = H.Setup.get_instance_by_prey(char)
        if not setup:
            return await output.send(
                '[b]Hungry Game[/b]: You\'re not being challenged.'
            )
        await output.send(
            '[b]Hungry Game[/b]: You accepted the challenge.'
        )
        setup.add_consent(char)
        if not len(setup.need_consent):
            game: H.Game = H.Game(
                setup.pred,
                setup.prey,
                setup.channel,
                setup.output
            )
            setup.channel.setup = False
            await H.UI.draw_game_start(game)

    @staticmethod
    async def decline(
        by: Character,
        **kwargs
    ) -> None:
        output: Output = Output(recipient=by)
        char: H.Character = H.Game.get_character(by.name)
        if not char:
            return await output.send(
                '[b]Hungry Game[/b]: You don\'t have a character sheet.'
            )
        setup: H.Setup = H.Setup.get_instance_by_prey(char)
        if not setup:
            return await output.send(
                '[b]Hungry Game[/b]: You\'re not being challenged.'
            )
        setup.no_consent()
        await output.send(
            '[b]Hungry Game[/b]: You declined the challenge.'
        )
        await setup.output.send(
            '[b]Hungry Game[/b]: [color=red]Failed![/color] ' +
            f'"{char.proper_name}" declined the challenge.'
        )

    @staticmethod
    async def challenge(
        by: Character,
        character: list[str],
        channel: Channel,
        output: Output,
        **kwargs
    ) -> None:
        pred_output: Output = Output(recipient=by)
        prey: list[H.Prey] = H.Game.get_character(character)
        pred: H.Pred = H.Game.get_character(by.name)
        if not channel:
            return await output.send(
                '[b]Hungry Game[/b]: [color=red]Failed![/color]' +
                ' You must use this command in a channel.'
            )
        if channel.name in CONFIG.joined_channels:
            return await pred_output.send(
                '[b]Hungry Game[/b]: [color=red]Failed![/color]' +
                ' Not in an appropriate channel.'
            )
        if channel.hungry:
            return await output.send(
                '[b]Hungry Game[/b]: [color=red]Failed![/color]' +
                ' A game is already in session!'
            )
        for idx in range(len(prey)):
            p: H.Prey | None = prey[idx]
            p_name: str = character[idx]
            if not p:
                return await output.send(
                    '[b]Hungry Game[/b]: [color=red]Failed![/color] ' +
                    f'\"{p_name}\" doesn\'t have a character sheet.'
                )
        for p in prey:
            await Output(recipient=get_char(p.proper_name)).send(
                f'[b]Hungry Game[/b]: {pred.proper_name} has challenged you' +
                ' to a game of [b]Hungry Game[/b] in the '
                f'"{channel.title}" channel! Type "[i][b]!accept[/b][/i]"' +
                ' to accept the challenge, or "[i][b]!decline[/b][/i]"' +
                ' to decline the challenge!'
            )

        H.Setup(
            pred=pred,
            prey=prey,
            channel=channel,
            output=output
        )

    @staticmethod
    async def badge(
        by: Character,
        perk: str = '',
        **kwargs
    ) -> None:
        perk = perk.lower()
        output: Output = Output(recipient=by)
        char: H.Character = H.Game.get_character(by.name)

        if not char.perks.get(perk):
            return await output.send(
                f'[b]Hungry Game[/b]: You don\'t have the \"{perk}\" perk.'
            )
        if not char.perks[perk].get('badge'):
            return await output.send(
                f'[b]Hungry Game[/b]: The \"{perk}\" perk isn\'t an ' +
                'acheivement/milestone perk.'
            )
        char.badge = char.perks[perk]['badge']
        return await output.send(
            f'[b]Hungry Game[/b]: Success! Badge set!'
        )

    @staticmethod
    async def refund(
        by: Character,
        **kwargs
    ) -> None:
        time_stamp: int = int(time())
        output: Output = Output(recipient=by)
        char: H.Character = H.Game.get_character(by.name)
        if not char:
            return await output.send(
                '[b]Hungry Game[/b]: You don\'t have a character to refund.'
            )
        if time_stamp - char.desires_refund > 300:
            char.desires_refund = int(time())
            return await output.send(
                '[b]Hungry Game[/b]: Type this command again to confirm ' +
                'you want to refund all your spent points.'
            )
        char.str = 4
        char.agi = 4
        char.vit = 4
        char.spent_stat = 0
        char.spent_perk = 0
        char.spent_ability = 0
        for name in char.perks.copy():
            perk: H.Perk = char.perks[name]
            if perk.perkiary[name].get('cost'):
                perk.remove()
                char.remove_perk(name)
        for name in char.abilities.copy():
            ability: H.Ability = char.abilities[name]
            ability.remove()
            char.abilities.pop(name)
        for name in ['attack', 'heal', 'rest', 'defend']:
            char.abilities[name] = H.Ability(
                name,
                1,
                char
            )
        return await output.send(
            '[b]Hungry Game[/b]: Refund complete!'
        )

    @staticmethod
    async def sheet(
        by: Character,
        character: str = '',
        **kwargs
    ) -> None:
        character: str = character
        output: Output = Output(recipient=by)
        if not character:
            char: H.Character = H.Game.get_character(by.name)
            if not char:
                return await output.send(
                    '[b]Hungry Game[/b]: You don\'t have a character.'
                )
            return await output.send(
                '[b]Hungry Game[/b]:' + H.UI.sheet(char)
            )
        char: H.Character | None = H.Game.get_character(character)
        if not char:
            return await output.send(
                f'[b]Hungry Game[/b]: Unknown character "{character}".'
            )
        return await output.send(
            f'[b]Hungry Game[/b]:' + H.UI.sheet(char)
        )

    @staticmethod
    async def abilities(
        by: Character,
        ability: str = '',
        **kwargs
    ) -> None:
        ability: str = ability.lower()
        ability_obj: dict | None = H.Ability.abiliary.get(ability)
        output: Output = Output(recipient=by)
        if not ability:
            return await output.send(
                '[b]Hungry Game[/b]: List of currently available abilities:' +
                '\n' + '   '.join([x for x in H.Ability.abiliary]) +
                '\n[sub]Remember to use "[i]!abilities name[/i]" for ' +
                'more info![/sub]'
            )
        if not ability_obj:
            return await output.send(
                '[b]Error[/b]: No such ability exists.'
            )
        return await output.send(
            f'[b]Hungry Game[/b]: Ability info for "{ability}":' +
            Command.__append_thing_info(ability_obj)
        )

    @staticmethod
    async def perks(
        by: Character,
        perk: str = '',
        **kwargs
    ) -> None:
        perk: str = perk.lower()
        perk_obj: dict | None = H.Perk.perkiary.get(perk)
        output: Output = Output(recipient=by)
        if not perk:
            perks: list[str] = []
            for x in H.Perk.perkiary:
                if H.Perk.perkiary[x].get('cost'):
                    perks.append(u'\U0001f4b2' + x)
                else:
                    perks.append(u'\u2b50' + x)
            perks = sorted(perks)
            return await output.send(
                '[b]Hungry Game[/b]: List of currently available perks:\n' +
                '   '.join(perks)
            )
        if not perk_obj:
            return await output.send(
                '[b]Error[/b]: No such perk exists.'
            )
        return await output.send(
            f'[b]Hungry Game[/b]: Perk info for "{perk}":' +
            Command.__append_thing_info(perk_obj)
        )

    @staticmethod
    async def create(
        by: Character,
        **kwargs
    ) -> None:
        output: Output = Output(
            recipient=by
        )
        char: H.Character = H.Game.get_character(by.name)

        if char:
            return await output.send(
                '[b]Error[/b]: Already have a character under this name!'
            )

        char = H.Character = H.Character(
            name=by.name
        )

        H.Game.add_character(char.name, char)

        out_str: str = H.UI.sheet(character=char)
        return await output.send(
            f'{out_str}\nYou have created a new character for ' +
            '[b]Hungry Game[/b]!\nIn order to allocate points ' +
            'and read the rules, check the "[i]!help[/i] hungry" command!'
        )

    @staticmethod
    async def help(
        by: Character,
        sub_command: str = '',
        **kwargs
    ) -> None:
        output: Output = Output(recipient=by)
        help: str = Command.doc.get(sub_command)
        if not help:
            return await output.send(
                Command.doc['help']
            )
        return await output.send(
            help
        )

    async def buy(
        by: Character,
        upgrade: str = '',
        selection: str = '',
        amount: int = 1,
        **kwargs
    ) -> None:
        output: Output = Output(
            recipient=by
        )
        upgrade: str = upgrade.lower()
        selection: str = selection.lower()
        char: H.Character = H.Game.get_character(by.name)
        valid_stat: dict[str, bool] = {
            'strength': True,
            'agility': True,
            'vitality': True
        }
        sp, pp, ap = char.get_unspent()

        if upgrade == 'stat':
            if not valid_stat.get(selection):
                return await output.send(
                    '[b]Error[/b]: No such stat exists.'
                )
            if amount > sp:
                return await output.send(
                    '[b]Error[/b]: You do not have enough stat points to ' +
                    f'allocate {amount} stat points. Have: ' +
                    f'{sp}.'
                )
            stat: int = getattr(char, selection)
            setattr(
                char,
                selection,
                stat + amount
            )
            char.spent_stat += amount
            return await output.send(
                u'[b]Success[/b]: \U0001f4b2 Purchase successful. \U0001f4b2'
            )
        elif upgrade == 'perk':
            current_perk: H.Perk = char.perks.get(selection)
            name: str = selection
            selection: dict = H.Perk.perkiary.get(selection)
            level: int = 0
            if not selection:
                return await output.send(
                    '[b]Error[/b]: No such perk exists.'
                )
            if not selection.get('cost'):
                return await output.send(
                    '[b]Error[/b]: Perk is not purchasable.'
                )
            cost: int = selection.get('cost') * amount
            if cost > pp:
                return await output.send(
                    '[b]Error[/b]: You do not have enough perk points to ' +
                    f'allocate {amount} perk points. Have: ' +
                    f'{pp}.'
                )
            if current_perk:
                level = current_perk.level
                if current_perk.level + amount > selection.get('max_level'):
                    return await output.send(
                        '[b]Error[/b]: Amount of levels to purchase over ' +
                        'the perk\'s max level.'
                    )
                char.remove_perk(name)
            char.add_perk(name, level + amount)
            char.spent_perk += cost
            return await output.send(
                u'[b]Success[/b]: \U0001f4b2 Purchase successful. \U0001f4b2'
            )
        else:
            current_ability: H.Ability = char.abilities.get(selection)
            name: str = selection
            selection: dict = H.Ability.abiliary.get(selection)
            level: int = 0
            if not selection:
                return await output.send(
                    '[b]Error[/b]: No such ability exists.'
                )
            if not selection.get('cost'):
                return await output.send(
                    '[b]Error[/b]: Ability is not purchasable.'
                )
            cost: int = selection.get('cost') * amount
            if cost > ap:
                return await output.send(
                    '[b]Error[/b]: You do not have enough ability points to ' +
                    f'allocate {amount} ability points. Have: ' +
                    f'{ap}.'
                )
            if current_ability:
                level = current_ability.level
                if current_ability.level + amount > selection.get('max_level'):
                    return await output.send(
                        '[b]Error[/b]: Amount of levels to purchase over ' +
                        'the ability\'s max level.'
                    )
                current_ability.remove()
            char.abilities[name] = H.Ability(
                name,
                current_ability.level + amount,
                char,
                current_ability.cooldown
            )
            char.spent_ability += cost
            return await output.send(
                u'[b]Success[/b]: \U0001f4b2 Purchase successful. \U0001f4b2'
            )

    @staticmethod
    async def logs(
        output: Output,
        by: Character,
        amount: int = 10,
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

    @staticmethod
    async def yeeted(
        channel: Channel,
        output: Output,
        **kwargs
    ) -> None:
        time_last: int = channel.states.get('last', 0)
        time_diff_state: int = int(time()) - time_last

        unique_kills: int = len(KILLS.keys())
        kills: int = sum(KILLS.values())

        if not channel or time_diff_state < COMMAND_TIMEOUT:
            return

        channel.states['last'] = int(time())

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

    @staticmethod
    async def eicon(
        by: Character,
        flags: str = '',
        page: int = 0,
        filetype: str = '',
        search: str = '',
        **kwargs
    ) -> None:
        filetype = filetype.lower()
        search = search.lower()
        output: Output = Output(recipient=by)
        result: list[str] = []
        result_t: list[int] = []
        names: list[str] = list(Verify.exists.keys())
        T_MAX: int = 2000
        page: int = page if page and page > 0 else 1
        out_str: str = 'results'
        sort_t, sort_r = 't' in flags, 'r' in flags

        if sort_r:
            names.reverse()

        for name in names:
            mime: str = Verify.exists[name][1]
            if search in name or not search:
                if filetype and filetype != mime:
                    continue
                if len(result) + 1 > T_MAX * page:
                    out_str += f' [page: {page}]'
                    break
                result.append(name)
                result_t.append(Verify.exists[name][2])
        if sort_t:
            result = sorted(
                result,
                key=lambda x: result_t[result.index(x)],
                reverse=sort_r
            )
        if len(result) > T_MAX * (page - 1):
            result = result[T_MAX * (page - 1):]
            result_t = result_t[T_MAX * (page - 1):]
        else:
            return await output.send(
                f'[b]Error:[/b] No results for the search ' +
                f'parameters [[b]page:[/b] {page}, ' +
                '[b]flags:[/b] ' + (flags or 'no-flags') + ', ' +
                '[b]type:[/b] ' + (filetype or 'any') + ', '
                f'[b]search:[/b] {search}].'
            )

        out_str = (
            f'[b]{len(result)} {out_str}:[/b] '
        )

        await output.send(
            f'{out_str}\n[spoiler]' +
            ''.join([f'[eicon]{x}[/eicon]' for x in result]) +
            '[/spoiler]'
        )

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

    @staticmethod
    async def force_save(
        by: Character,
        output: Output,
        **kwargs
    ) -> None:
        if by.name == "Kali":
            Verify.cycle(True)
            return await output.send(
                'Yep. ~<:'
            )
        await output.send(
            'Nope. ~<:'
        )


async def main() -> None:
    await SOCKET.start()


if __name__ == '__main__':
    asyncio.run(main())
