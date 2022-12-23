import sys as system
from time import sleep, time

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


def get_output(args) -> Output:
    if not args['is_channel']:
        return Output(recipient=args['sender'])
    else:
        return Output(channel=args['channel'])


def propagate_commands() -> None:
    async def help(args) -> None:
        output = get_output(args)

        if not hasattr(BOT_COMMANDS, args.subcommand):
            return await output.send('Unknown command.')

        await output.send(
            BOT_COMMANDS[args['subcommand']].help
        )

    BotCommand(
        'help',
        help,
        ['help', 'die', 'hp'],
        cat(
            'Insert witty joke about recursion here, or the fact I can no ',
            'longer actually help you if you need help about the help ',
            'function itself. :>~'
        )
    )

    async def die(args) -> None:
        by: str
        output = get_output(args)

        if not args['is_channel']:
            by = args['sender']
        else:
            by = args['character']

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
        [],
        'Kill the bot. Before you event try: [b]no[/b], you can\'t. :>~'
    )

    async def hp(args) -> None:
        output = get_output(args)

    BotCommand(
        'hp',
        hp,
        [
            'damage',
            'status'
        ],
        'HP bar formatter.'
    )


instances: list[dict] = []
instances_last_active: list[int] = []


propagate_commands()
