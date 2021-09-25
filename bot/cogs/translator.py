from discord.ext import commands
from googletrans import Translator

from bot.bot_class import Nya_Nya
from bot.context_class import NyaNyaContext


class Google(commands.Cog):
    def __init__(self, bot: Nya_Nya):
        self.emoji = "🌐"
        self.bot = bot
        self.translator = Translator()

    @commands.command(name="translate")
    async def translator(self, ctx: NyaNyaContext, *, idk):
        result = self.translator.translate(idk)
        await ctx.send(f"translated from: {result.src}\n`{result.text}`")

    @commands.command(name="translateto")
    async def translate_to(self, ctx: NyaNyaContext, dest, *, idk):
        result = self.translator.translate(idk, dest=dest)
        await ctx.send(f"translated from: {result.src}\n`{result.text}`")


def setup(bot):
    bot.add_cog(Google(bot))
