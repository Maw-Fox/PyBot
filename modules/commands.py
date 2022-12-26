class BotCommand():
    def __init__(
        self,
        command_name: str,
        solver,
        help: str,
        state: dict | bool = None
    ) -> None:
        self.command_name: str = command_name
        self.solver = solver
        self.help: str = help
        self.state: dict | bool | None = state
        BOT_COMMANDS[command_name] = self


BOT_COMMANDS: dict[str, BotCommand] = {}
