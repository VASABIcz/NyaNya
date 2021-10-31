import re

EMBED_COLOR = [0x4d0034, 0xEBA2DC, 0xec64a3, 0xc46489]

COGS = ["image", "info", "meme", "translator", "utilities", "tarkov", "admin", "listener", "musix", "lolapi"]

STATIC_COGS = ["admin"]

IGNORED = ["Jishaku"]

COG_DIR = "bot.cogs."

LOL_REGIONS = {"BR1": "BR", "EUN1": "EUNE", "EUW1": "EUW", "JP1": "JP", "KR": "KR", "LA1": "LAN", "LA2": "LAS",
               "NA  1": "NA", "OC1": "OCE", "TR1": "TR", "RU": "RU"}

URL_REGEX = re.compile(
    r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&/=]*)")  # dif regex