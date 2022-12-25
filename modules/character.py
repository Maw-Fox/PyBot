from time import time

from modules.shared import PRUNE_INSTANCE_DURATION


class Character:
    def __init__(
        self,
        name: str,
        gender: str = 'None',
        status: str = 0,
        status_message: str = ''
    ) -> None:
        self.name: str = name
        self.gender: str = gender
        self.status: str = status
        self.status_message: str = status_message
        GLOBAL_CHARACTER_LIST[name] = self

    def remove(self) -> None:
        GLOBAL_CHARACTER_LIST.pop(self.name)


class HPUser:
    def __init__(
        self,
        name: str,
        hp_name: str = 'Person',
        hp: int = 100,
        hp_max: int = 100,
        dmg: int = 0
    ) -> None:
        self.name: str = name
        self.hp_name: str = hp_name
        self.hp: int = hp
        self.hp_max: int = hp_max
        self.dmg: int = dmg
        self.last_interaction: float = time()
        self.time_deletion: float = time() + PRUNE_INSTANCE_DURATION


HP_USERS: dict[str, HPUser] = {}
GLOBAL_CHARACTER_LIST: dict[str, Character] = {}
