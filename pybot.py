import asyncio
import argparse

from modules.socket import SOCKET


async def main() -> None:
    await SOCKET.start()


if __name__ == '__main__':
    asyncio.run(main())
