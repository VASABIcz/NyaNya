import datetime
import time

import discord

# from bot.context_class import NyaNyaContext
from utils.constants import EMBED_COLOR, URL_REGEX
from utils.functions_classes import codeblock


def play_embed(ctx, queue: int, data: list) -> discord.Embed:
    m, s = divmod(data[4], 60)
    h, m = divmod(m, 60)
    duration = f'{h:d}:{m:02d}:{s:02d}'
    embed = discord.Embed(title=data[1],
                          colour=EMBED_COLOR,
                          url=data[0],
                          timestamp=datetime.datetime.utcfromtimestamp(time.time()))
    embed.set_image(url=data[3])
    embed.set_footer(text=f"requested by {ctx.author}",
                     icon_url=f"{ctx.author.avatar_url}")
    embed.add_field(name="🎵now playing🎵", value=f"**`{data[1]}`**", inline=False)
    embed.add_field(name="📋enqueued📋", value=f"**`{queue}`**`song`", inline=True)
    embed.add_field(name="⏱lenght⏱", value=f"**`{duration}`**", inline=True)
    embed.set_author(name=data[6], url=data[5],
                     icon_url="https://cdn.discordapp.com/avatars/841271270015893535/ccab84cb5b9b3082e874d2c5d8961769.webp?size=1024")
    return embed


def info_embed(ctx, name: str, data: dict, thumbnail: str = None) -> discord.Embed:
    embed = discord.Embed(title=name,
                          colour=EMBED_COLOR,
                          timestamp=datetime.datetime.utcfromtimestamp(time.time()))

    embed.set_footer(text=f"requested by {ctx.author}",
                     icon_url=f"{ctx.author.avatar_url}")

    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    embed.set_author(name="Nya Nya",
                     icon_url="https://cdn.discordapp.com/avatars/841271270015893535/ccab84cb5b9b3082e874d2c5d8961769.webp?size=1024")

    for name, value in data.items():
        url = URL_REGEX.findall(str(value))  # bettet regex kinda wierd this one

        if not url:
            value = codeblock(value)

        embed.add_field(name=name, value=value, inline=False)
    return embed


def picture_embed(js):
    embed = discord.Embed(title=js['title'], url=js['url'], colour=EMBED_COLOR, timestamp=datetime.datetime.now())
    embed.set_image(url=js['url'])
    embed.set_footer(text=f"⬆️ {js['ups']}")
    return embed


def error_embed(error) -> discord.Embed:
    embed = discord.Embed(title="ERROR", description=f"```ini\n[{error}]```", colour=EMBED_COLOR)
    return embed


def exception_embed(exception) -> discord.Embed:
    embed = discord.Embed(title="EXCEPTION", description=f"```ini\n[{exception}]```", colour=EMBED_COLOR)
    return embed


def market_embed(values):
    values = values[0]
    embed = discord.Embed(title=values['name'], description="",
                          url="https://tarkov-market.com/item/" + values['market_url'], colour=EMBED_COLOR)
    embed.set_thumbnail(url=values['icon'])
    embed.add_field(name="Market", value=f"[here](https://tarkov-market.com/item/{values['market_url']})", inline=True)
    embed.add_field(name="Wiki", value=f"[here]({values['wiki_url']})", inline=True)
    embed.add_field(name="Price", value=f"```{values['price']}₽```", inline=False)
    return embed


def search_embed(values):
    embed = discord.Embed(title='Results', description="", colour=EMBED_COLOR)
    for value in values:
        embed.add_field(name=f"{value['name']}",
                        value=f"```{value['price']}₽```\n[wiki link]({value['wiki_url']}) | [market link](https://tarkov-market.com/item/{value['market_url']})",
                        inline=False)
    return embed


def calculator_embed(expresion, result):
    return discord.Embed(title="Result", description=f"```{expresion} = {result}```", colour=EMBED_COLOR)


def std_embed(title, desc, type="py"):
    return discord.Embed(title=title, description=codeblock(desc, type), colour=EMBED_COLOR)


def cogman_embed(data):
    embed = discord.Embed(title="Results", colour=EMBED_COLOR)
    for x in data:
        embed.add_field(name=x[0], value=x[1], inline=False)

    return embed


def pretty_list(data, title=""):
    embed = discord.Embed(title=title, description=codeblock("\"" + "\" | \"".join(data) + "\"", "py"),
                          colour=EMBED_COLOR)

    return embed


def loc_embed(code, docs, empty):
    embed = discord.Embed(title="", colour=EMBED_COLOR)  # **Lines of code counter**
    embed.add_field(name="**Code**", value=codeblock(f"{code} lines", 'py'), inline=False)
    embed.add_field(name="**Docs**", value=codeblock(f"{docs} lines", 'py'), inline=False)
    embed.add_field(name="**Empty**", value=codeblock(f"{empty} lines", 'py'), inline=False)

    return embed
