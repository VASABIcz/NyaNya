from discord.ext import commands


class BadSpotify(commands.CommandError):
    pass


class ExpiredApiKey(commands.CommandError):
    pass


class ItemNotFound(commands.CommandError):
    def __init__(self, message=None, *args):
        if message is not None:
            m = f"Item Not Found: \"{message}\""
            super().__init__(m, *args)
        else:
            super().__init__(*args)
