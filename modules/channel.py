from modules.character import Character


class Channel:
    def __init__(
        self,
        name: str
    ) -> None:
        self.name: str = name
        self.title: str = name
        self.characters: dict[str, Character] = {}
        self.ops: dict[str, int] = {}
        self.hungry = None
        self.setup: bool = False
        CHANNELS[self.name] = self
        self.states: dict[str, complex] = {}

    def remove_char(self, character: Character) -> None:
        if not self.characters.get(character):
            return
        self.characters.pop(character)

    def add_char(self, character: Character) -> None:
        self.characters[character]: Character = character

    def add_op(self, s_character: str) -> None:
        self.ops[s_character] = 1

    def remove_op(self, s_character: str) -> None:
        self.ops.pop(s_character)

    def is_op(self, s_character: str) -> bool:
        return bool(self.ops.get(s_character))

    def remove(self) -> None:
        CHANNELS.pop(self.name)


CHANNELS: dict[str, Channel] = {}
