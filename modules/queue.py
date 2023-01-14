from time import time


class Queue:
    last: float = time()
    sub_last: float = time()
    throttle: float = 2.0
    sub_throttle: float = 1.5

    def __init__(self, callback, data, sub_queue: bool = False) -> None:
        self.data = data
        self.callback = callback
        if sub_queue:
            return SUB_QUEUE.append(self)
        QUEUE.append(self)

    async def run(self) -> None:
        await self.callback(self.data)

    async def cycle() -> None:
        t: float = time()
        if len(QUEUE) and t - Queue.last > Queue.throttle:
            Queue.last = t
            await QUEUE.pop().run()
        if len(SUB_QUEUE) and t - Queue.sub_last > Queue.sub_throttle:
            Queue.sub_last = t
            await SUB_QUEUE.pop().run()


QUEUE: list[Queue] = []
SUB_QUEUE: list[Queue] = []
