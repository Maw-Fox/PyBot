from time import time


class ModAction:
    def __init__(self, cname: str):
        self.last_actions: list[float] = [time()]
        self.name: str = cname
        characters[cname] = self

    def get(cname: str):
        history: ModAction | None = characters.get(cname, None)
        if not history:
            return ModAction(cname)
        history.last_actions.append(time())
        return history

    def cumulative(self) -> int:
        t: float = time()
        act_sum: int = -1
        if len(self.last_actions):
            for act_t in self.last_actions:
                if act_t + 3600.0 > t:
                    act_sum += 1
        return act_sum


characters: dict[str, ModAction] = {}
