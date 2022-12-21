import sys as system
from time import sleep

from modules.utils import cat
from modules.command import BotCommand, BOT_COMMANDS
from modules.socket import Output


def propagate_commands() -> None:
    async def help(args) -> None:
        if not args['is_channel']:
            output = Output(recipient=args['sender'])

        if not hasattr(BOT_COMMANDS, args.subcommand):
            return await output.send('Unknown command.')

        await output.send(
            BOT_COMMANDS[args['subcommand']].help
        )

    BotCommand(
        'help',
        help,
        ['help'],
        cat(
            'Insert witty joke about recursion here, or the fact I can no ',
            'longer actually help you if you need help about the help ',
            'function itself. :>~'
        )
    )

    async def die(args) -> None:
        if not args['is_channel']:
            output = Output(recipient=args['sender'])

        if args['sender'] != 'Kali':
            return await output.send(
                'No u. :>~\n[color=red][b]A C C E S S   D E N I E D',
                '[/b][/color]'
            )

        if not hasattr(args, 'is_channel'):
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

    async def bouncer(args) -> None:
        sleep(1)


instances: list[dict] = []
instances_last_active: list[int] = []


propagate_commands()
