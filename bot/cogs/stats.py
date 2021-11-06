from discord.ext import commands, tasks

from bot.utils.functions_classes import codeblock


class LogCom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stats = {}
        self.total = 0
        self.clear_stats.start()

    @commands.Cog.listener("on_after_invoke")
    async def after_invoke(self, ctx):
        n = ctx.command.name

        if n in self.stats:
            self.stats[n] += 1
        else:
            self.stats[n] = 1

        self.total += 1

    def cog_unload(self):
        self.clear_stats.cancel()

    @tasks.loop(minutes=60.0)
    async def clear_stats(self):
        self.stats = {}
        self.total = 0

    @commands.command()
    async def stats(self, ctx):
        await ctx.send(f"{codeblock(self.stats)}\n{codeblock(self.total)}")


def setup(bot):
    bot.add_cog(LogCom(bot))
