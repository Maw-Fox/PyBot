import asyncio
import json
import requests
import os
import re

import modules.hungry as H
from time import time
from math import floor
from websockets.client import connect
from functools import singledispatch as default
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
                        H.Game.check_save(t)
                        if t - CHECK['last'] > CHECK['every']:
                            CHECK['last'] = t
                            for char in KILLS_LAST.copy():
                                ts: int = KILLS_LAST[char]
                                if ts < t - CHECK['clear']:
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

        if not chan.states.get('yeetus', True):
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
            message=message[1:],
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
            'logs', 'yeetus', 'yeeted', '[b]help[/b]'
        ]) + '\n'
        '   [b]Hungry Game:[/b]\n      ' +
        '   '.join([
            'hungry', 'create', 'buy', '[s]target[/s]', '[s]badge[/s]',
            '[s]challenge[/s]', 'sheet', '[s]action[/s]', 'perks',
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
    async def refund(
        by: Character,
        **kwargs
    ) -> None:
        time_stamp: int = int(time())
        output: Output = Output(recipient=by)
        char: H.GameCharacter = H.Game.get_character(by.name)
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
        level: int = char.level
        char.strength = 4
        char.agility = 4
        char.vitality = 4
        char.stat_alloc = 10 + level
        char.perk_alloc = floor(level / 2)
        char.ability_alloc = floor(level / 4)
        for name in char.perks.copy():
            perk: H.CharacterPerk = char.perks[name]
            if perk.perkiary[name].get('cost'):
                perk.remove()
                char.remove_perk(name)
        for name in char.abilities.copy():
            char.abilities[name].remove()
            char.remove_ability(name)
            char.add_ability(name, 1)
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
            char: H.GameCharacter = H.Game.get_character(by.name)
            if not char:
                return await output.send(
                    '[b]Hungry Game[/b]: You don\'t have a character.'
                )
            return await output.send(
                '[b]Hungry Game[/b]:' + H.UI.sheet(char)
            )
        char: H.GameCharacter | None = H.Game.get_character(character)
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
        ability_obj: dict | None = H.CharacterAbility.abiliary.get(ability)
        output: Output = Output(recipient=by)
        if not ability:
            return await output.send(
                '[b]Hungry Game[/b]: List of currently available abilities:' +
                '\n' + '   '.join([x for x in H.CharacterAbility.abiliary]) +
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
        perk_obj: dict | None = H.CharacterPerk.perkiary.get(perk)
        output: Output = Output(recipient=by)
        if not perk:
            perks: list[str] = []
            for x in H.CharacterPerk.perkiary:
                if H.CharacterPerk.perkiary[x].get('cost'):
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
        char: H.GameCharacter = H.Game.get_character(by.name)

        if char:
            return await output.send(
                '[b]Error[/b]: Already have a character under this name!'
            )

        char = H.GameCharacter = H.GameCharacter(
            name=by.name
        )
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
        help: str = Command.help.get(sub_command)
        if not help:
            return await output.send(
                Command.help['help']
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
        char: H.GameCharacter = H.Game.get_character(by.name)
        valid_stat: dict[str, bool] = {
            'strength': True,
            'agility': True,
            'vitality': True
        }

        if upgrade == 'stat':
            if not valid_stat.get(selection):
                return await output.send(
                    '[b]Error[/b]: No such stat exists.'
                )
            if amount > char.stat_alloc:
                return await output.send(
                    '[b]Error[/b]: You do not have enough stat points to ' +
                    f'allocate {amount} stat points. Have: ' +
                    f'{char.stat_alloc}.'
                )
            stat: int = getattr(char, selection)
            setattr(
                char,
                selection,
                stat + amount
            )
            char.stat_alloc -= amount
            return await output.send(
                u'[b]Success[/b]: \U0001f4b2 Purchase successful. \U0001f4b2'
            )
        elif upgrade == 'perk':
            current_perk: H.CharacterPerk = char.perks.get(selection)
            name: str = selection
            selection: dict = H.CharacterPerk.perkiary.get(selection)
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
            if cost > char.perk_alloc:
                return await output.send(
                    '[b]Error[/b]: You do not have enough perk points to ' +
                    f'allocate {amount} perk points. Have: ' +
                    f'{char.perk_alloc}.'
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
            char.perk_alloc -= cost
            return await output.send(
                u'[b]Success[/b]: \U0001f4b2 Purchase successful. \U0001f4b2'
            )
        else:
            current_ability: H.CharacterAbility = char.abilities.get(selection)
            name: str = selection
            selection: dict = H.CharacterAbility.abiliary.get(selection)
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
            if cost > char.ability_alloc:
                return await output.send(
                    '[b]Error[/b]: You do not have enough ability points to ' +
                    f'allocate {amount} ability points. Have: ' +
                    f'{char.ability_alloc}.'
                )
            if current_ability:
                level = current_ability.level
                if current_ability.level + amount > selection.get('max_level'):
                    return await output.send(
                        '[b]Error[/b]: Amount of levels to purchase over ' +
                        'the ability\'s max level.'
                    )
                char.remove_ability(name)
            char.add_ability(name, level + amount)
            char.ability_alloc -= cost
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
