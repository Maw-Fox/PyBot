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
        BOT_COMMANDS[command_name] = self


BOT_COMMANDS: dict[str, BotCommand] = {}
