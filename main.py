#!/usr/bin/env python3.9

import asyncio
import sys

import postgres

import cfg
from bot.bot_class import Nya_Nya
from utils.functions_classes import Unbuffered

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass  # it looks like ur on windows no speedy asyncio for u m8


def db_setup():
    db = postgres.Postgres(url=cfg.DB_URL)
    with open("database/db.sql", "r") as f:
        file = f.read()

    db.run(file)


def main():
    """
    Run the bot.
    """
    # logging.basicConfig(level=logging.DEBUG)
    db_setup()

    sys.stdout, sys.stderr, sys.stdin = Unbuffered(sys.stdout), Unbuffered(sys.stderr), Unbuffered(sys.stdin)

    bot = Nya_Nya(cfg)

    bot.run()


if __name__ == "__main__":
    main()
