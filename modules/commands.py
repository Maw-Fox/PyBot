import sys as system
from time import time

from modules.utils import cat
from modules.command import BotCommand, BOT_COMMANDS
from modules.socket import Output
from modules.constants import PRUNE_INSTANCE_DURATION


class HPUser:
    def __init__(
        self,
        id: str,
        hp_id: str = 'Person',
        hp: int = 100,
        hp_max: int = 100,
        dmg: int = 0
    ):
        self.id = id
        self.hp_id = hp_id
        self.hp = hp
        self.hp_max = hp_max
        self.dmg = dmg
        self.last_interaction = time()
        self.time_deletion = round(time()) + PRUNE_INSTANCE_DURATION


hp_users: list[HPUser] = []


def get_params(s: str, n_params: int) -> str:
    exploded = s.split(' ')
    params: list[str] = []

    for idx in range(n_params):
        if idx == n_params - 1:
            params.append(' '.join(exploded[idx:]))
            break
        params.append(exploded[idx])

    return params


def get_output(args) -> Output:
    if not args['channel']:
        return Output(recipient=args['from'])
    else:
        return Output(channel=args['channel'])


def propagate_commands() -> None:
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


instances: list[dict] = []
instances_last_active: list[int] = []


propagate_commands()
