from time import time

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


HP_USERS: list[HPUser] = []
