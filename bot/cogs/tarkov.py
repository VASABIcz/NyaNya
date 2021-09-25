import base64 as b64
from json import loads
from urllib.parse import unquote

from discord.ext import commands

from bot.bot_class import Nya_Nya
from utils.embeds import market_embed, search_embed
from utils.errors import ItemNotFound


class Tarkov(commands.Cog):
    def __init__(self, bot: Nya_Nya):
        self.emoji = "🔫"
        self.bot = bot
        self.session = self.bot.session
        self.url = "https://tarkov-market.com/api/items"
        self.limit = 1
        self.lang = 'en'
        self.sort = 'change24'
        self.sort_direction = 'desc'

    @commands.command(name="market", aliases=["m"])
    async def get_item(self, ctx, *, query):
        """Gets price and info about tarkov market."""
        await ctx.send(embed=market_embed(await self.api_get(query)))

    @commands.command(name="marketsearch", aliases=["ms"])
    async def search_market(self, ctx, *, query):
        """Gets price and info about tarkov market."""
        await ctx.send(embed=search_embed(await self.api_get(query, limit=10)))

    async def api_get(self, query: str, limit=1):
        params = {}
        params['limit'] = limit
        params['search'] = query
        params['lang'] = self.lang
        params['sort'] = self.sort
        params['sort_direction'] = self.sort_direction

        response = await self.session.get(self.url, params=params)
        text = await response.json()
        try:
            text = unquote(str(b64.b64decode(text['items'])))[2:][:-1]
            text = loads(text[:text.find("{") + 1] + text[text.find("uid") - 1:])
        except:
            raise ItemNotFound(query)

        result = [
            {'name': text['enName'], 'icon': text['wikiImg'], 'market_url': text['url'], 'wiki_url': text['wikiUrl'],
             'price': text['price']} for text in text]

        return result


def setup(bot):
    bot.add_cog(Tarkov(bot))
