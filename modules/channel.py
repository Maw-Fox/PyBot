from modules.character import Character


class Channel:
    def __init__(
        self,
        name: str
    ) -> None:
        self.name: str = name
        self.title: str = name
        self.characters: dict[str, Character] = {}
        self.ops: dict[str, Character] = {}
        CHANNELS[self.name] = self

    def remove_char(self, character: Character) -> None:
        if not self.characters.get(character):
            return
        self.characters.pop(character)

    def add_char(self, character: Character) -> None:
        self.characters[character]: Character = character

    def add_op(self, character: Character) -> None:
        self.ops[character] = character

    def remove_op(self, character: Character) -> None:
        self.ops.pop(character)


CHANNELS: dict[str, Channel] = {}
