from modules.channel import Channel
from modules.character import Character


class ModLog():
    def __init__(
        self,
        channel: Channel,
        type: str,
        character: str,
        reason: str
    ) -> None:
        self.channel = channel
        self.type: str = type
        self.character: Character = character
        self.reason: str = reason
        MOD_LOGS.insert(0, self)


MOD_LOGS: list[ModLog] = []
