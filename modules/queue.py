from time import time


class Queue:
    last: float = time()
    throttle: float = 2.0

    def __init__(self, callback, data) -> None:
        self.data = data
        self.callback = callback
        QUEUE.append(self)

    async def run(self) -> None:
        await self.callback(self.data)

    async def cycle() -> None:
        if len(QUEUE) and time() - Queue.last > Queue.throttle:
            await QUEUE.pop().run()


QUEUE: list[Queue] = []
