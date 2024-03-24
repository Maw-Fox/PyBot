from time import time
from modules.utils import log


class Queue:
    last: float = time()
    no_throttle_last: float = time()
    sub_last: float = time()
    throttle: float = 2.0
    sub_throttle: float = 2.0
    next_log: int = 0

    def __init__(self, callback, data, queue: int = 0) -> None:
        self.data = data
        self.callback = callback
        if queue:
            if queue == 1:
                return SUB_QUEUE.append(self)
            if queue == 2:
                return NO_THROTTLE.append(self)
        QUEUE.append(self)

    async def run(self) -> None:
        await self.callback(self.data)

    async def cycle() -> None:
        t: float = time()
        if len(QUEUE) and t - Queue.last > Queue.throttle:
            await QUEUE.pop(0).run()
        if len(SUB_QUEUE) and t - Queue.sub_last > Queue.sub_throttle:
            Queue.sub_last = t
            await SUB_QUEUE.pop(0).run()
        if len(NO_THROTTLE) and t - Queue.no_throttle_last > 0.4:
            Queue.no_throttle_last = t
            Queue.next_log = (Queue.next_log + 1) % 100
            if not Queue.next_log:
                log('QNT/UPD', f'length:{len(NO_THROTTLE)}')
            await NO_THROTTLE.pop(0).run()


QUEUE: list[Queue] = []
SUB_QUEUE: list[Queue] = []
NO_THROTTLE: list[Queue] = []
