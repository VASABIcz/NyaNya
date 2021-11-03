#!/usr/bin/env python3.9

import os
import sys

import cfg
from bot.bot_class import Nya_Nya
from bot.utils.functions_classes import Unbuffered

if os.name != "nt":
    import uvloop

    uvloop.install()

os.environ["JISHAKU_HIDE"] = "true"  # hides jishaku from help


def main():
    """
    Run the bot.
    """
    # no need for sleep task will ensure that we connect
    # logging.basicConfig(level=logging.DEBUG)
    sys.stdout, sys.stderr, sys.stdin = Unbuffered(sys.stdout), Unbuffered(sys.stderr), Unbuffered(sys.stdin)

    bot = Nya_Nya(cfg)

    bot.run()


if __name__ == "__main__":
    main()
