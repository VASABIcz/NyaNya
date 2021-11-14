#!/usr/bin/env python3.9
import asyncio
import logging
import os
import sys

import discord

import cfg
from bot.bot_class import Nya_Nya
from bot.utils.functions_classes import Unbuffered

if os.name != "nt":
    import uvloop

    uvloop.install()

os.environ["JISHAKU_HIDE"] = "true"  # hides jishaku from help


class BotInstance:
    def __init__(self, cfg):
        self.cfg = cfg
        self.loop = asyncio.get_event_loop()
        self.closed = False
        self.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        while not self.closed:
            # bc = importlib.reload(bot_class)
            # self.cls = bc.Nya_Nya

            bot = Nya_Nya(self.cfg)

            await bot.run()


async def main():
    logging.basicConfig(level=logging.INFO)
    sys.stdout, sys.stderr, sys.stdin = Unbuffered(sys.stdout), Unbuffered(sys.stderr), Unbuffered(sys.stdin)

    for n, instance in enumerate(cfg.INSTANCES):
        instance.ACTIVITY = discord.Game(name=f"{instance.MAIN_PREFIX}help\ninstance num. {n + 1}")
        BotInstance(instance)

    print("setup done")

    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
