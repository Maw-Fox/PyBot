from time import time


class ModAction:
    def __init__(self, cname: str):
        self.last_actions: list[float] = []
        self.name: str = cname

    @staticmethod
    def get(cname: str):
        history: ModAction | None = __characters.get(cname, None)
        if not history:
            return ModAction(cname)
        return history

    @property
    def characters():
        return __characters

    @property
    def cumulative(self) -> int:
        t: float = time()
        act_sum: int = 0
        if len(self.last_actions):
            for act_t in self.last_actions:
                if act_t + 3600.0 > t:
                    act_sum += 1
        return act_sum


__characters: dict[str, ModAction] = {}
