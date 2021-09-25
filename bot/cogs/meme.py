from discord.ext import commands

from bot.bot_class import Nya_Nya
from bot.context_class import NyaNyaContext
from utils.embeds import picture_embed


class Memes(commands.Cog):
    """
    Want some memes? Here they are. (:
    """

    def __init__(self, bot: Nya_Nya):
        self.bot = bot
        self.emoji = "😂"

    @commands.command(aliases=['reddit', 'subreddit', 'findmeme'])
    async def fromsubreddit(self, ctx: NyaNyaContext, *, imp: str):
        """
        send a hot post from subreddit
        """
        async with self.bot.session.get(f'https://meme-api.herokuapp.com/gimme/{imp}') as response:
            js = await response.json()

        await ctx.send(embed=picture_embed(js))

    @commands.command(name="meme", aliases=['mem'])
    async def _meme(self, ctx: NyaNyaContext):
        """
        send meme from memes sureddit
        """
        async with self.bot.session.get(f'https://meme-api.herokuapp.com/gimme/memes') as response:
            js = await response.json()

        await ctx.send(embed=picture_embed(js))

    @commands.command(name="me_irl", aliases=['meirl', 'irl'])
    async def _me_irl(self, ctx: NyaNyaContext):
        """
        send meme from me_irl sureddit
        """
        async with self.bot.session.get(f'https://meme-api.herokuapp.com/gimme/me_irl') as response:
            js = await response.json()

        await ctx.send(embed=picture_embed(js))


def setup(bot):
    bot.add_cog(Memes(bot))
