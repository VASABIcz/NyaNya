from discord.ext import commands


class BadSpotify(commands.CommandError):
    ...


class ExpiredApiKey(commands.CommandError):
    ...


class NoMoreSongsInCache(commands.CommandError):
    ...


class NothingPlaying(commands.CommandError):
    ...


class ForbidentoRemovePlaying(commands.CommandError):
    ...


class NotConnected(commands.CommandError):
    ...


class OutOfbounds(commands.CommandError):
    def __init__(self, message=None, *args):
        if message is not None:
            m = f"Index \"{message}\" is out of bounds"
            super().__init__(m, *args)
        else:
            super().__init__(*args)


class ItemNotFound(commands.CommandError):
    def __init__(self, message=None, *args):
        if message is not None:
            m = f"Item Not Found: \"{message}\""
            super().__init__(m, *args)
        else:
            super().__init__(*args)
