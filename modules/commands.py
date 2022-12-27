class BotCommand():
    def __init__(
        self,
        command_name: str,
        solver,
        help: str,
        state: dict[str, bool] = None
    ) -> None:
        self.command_name: str = command_name
        self.solver = solver
        self.help: str = help
        self.state: dict = state or {}
        BOT_COMMANDS[command_name] = self


BOT_COMMANDS: dict[str, BotCommand] = {}
