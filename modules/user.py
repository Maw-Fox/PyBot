from time import time

from modules.shared import PRUNE_INSTANCE_DURATION


class User:
    def __init__(
        self,
        name: str,
        gender: str = 'None',
        bitmask_perms: int = 0,
        enum_status: int = 0,
        status: str = ''
    ) -> None:
        self.name = name
        self.gender = gender
        self.bitmask_perms = bitmask_perms
        self.enum_status = enum_status
        self.status = status
        self.channels: list = []
        GLOBAL_USER_LIST[name] = self

    def remove(self) -> None:
        GLOBAL_USER_LIST.pop(self.name)


class HPUser:
    def __init__(
        self,
        name: str,
        hp_name: str = 'Person',
        hp: int = 100,
        hp_max: int = 100,
        dmg: int = 0
    ) -> None:
        self.id = name
        self.hp_id = hp_name
        self.hp = hp
        self.hp_max = hp_max
        self.dmg = dmg
        self.last_interaction = time()
        self.time_deletion = round(time()) + PRUNE_INSTANCE_DURATION


HP_USERS: dict[str, HPUser] = {}
GLOBAL_USER_LIST: dict[str, User] = {}
