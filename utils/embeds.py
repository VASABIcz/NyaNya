import datetime
import time

# from bot.context_class import NyaNyaContext
from utils.constants import URL_REGEX
from utils.functions_classes import codeblock, NyaEmbed


def play_embed(ctx, queue: int, data: list) -> NyaEmbed:
    m, s = divmod(data[4], 60)
    h, m = divmod(m, 60)
    duration = f'{h:d}:{m:02d}:{s:02d}'
    embed = NyaEmbed(title=data[1],
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


def info_embed(ctx, name: str, data: dict, thumbnail: str = None) -> NyaEmbed:
    embed = NyaEmbed(title=name, timestamp=datetime.datetime.utcfromtimestamp(time.time()))

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
    embed = NyaEmbed(title=js['title'], url=js['url'], timestamp=datetime.datetime.now())
    embed.set_image(url=js['url'])
    embed.set_footer(text=f"⬆️ {js['ups']}")
    return embed


def error_embed(error) -> NyaEmbed:
    embed = NyaEmbed(title="ERROR", description=f"```ini\n[{error}]```")
    return embed


def exception_embed(exception) -> NyaEmbed:
    embed = NyaEmbed(title="EXCEPTION", description=f"```ini\n[{exception}]```")
    return embed


def market_embed(values):
    values = values[0]
    embed = NyaEmbed(title=values['name'], description="",
                     url="https://tarkov-market.com/item/" + values['market_url'])
    embed.set_thumbnail(url=values['icon'])
    embed.add_field(name="Market", value=f"[here](https://tarkov-market.com/item/{values['market_url']})", inline=True)
    embed.add_field(name="Wiki", value=f"[here]({values['wiki_url']})", inline=True)
    embed.add_field(name="Price", value=f"```{values['price']}₽```", inline=False)
    return embed


def search_embed(values):
    embed = NyaEmbed(title='Results', description="")
    for value in values:
        embed.add_field(name=f"{value['name']}",
                        value=f"```{value['price']}₽```\n[wiki link]({value['wiki_url']}) | [market link](https://tarkov-market.com/item/{value['market_url']})",
                        inline=False)
    return embed


def calculator_embed(expresion, result):
    return NyaEmbed(title="Result", description=f"```{expresion} = {result}```")


def std_embed(title, desc, type="py"):
    return NyaEmbed(title=title, description=codeblock(desc, type))


def cogman_embed(data):
    embed = NyaEmbed(title="Results")
    for x in data:
        embed.add_field(name=x[0], value=x[1], inline=False)

    return embed


def pretty_list(data, title=""):
    embed = NyaEmbed(title=title, description=codeblock("\"" + "\" | \"".join(data) + "\"", "py"))

    return embed


def loc_embed(code, docs, empty):
    embed = NyaEmbed(title="")  # **Lines of code counter**
    embed.add_field(name="**Code**", value=codeblock(f"{code} lines", 'py'), inline=False)
    embed.add_field(name="**Docs**", value=codeblock(f"{docs} lines", 'py'), inline=False)
    embed.add_field(name="**Empty**", value=codeblock(f"{empty} lines", 'py'), inline=False)

    return embed
