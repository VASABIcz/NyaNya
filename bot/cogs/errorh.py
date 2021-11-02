import asyncio
import io
import traceback
from difflib import get_close_matches

import discord

from bot.bot_class import Nya_Nya
from bot.context_class import NyaNyaContext
from bot.utils.errors import *
from bot.utils.functions_classes import NyaEmbed, codeblock


class ErrorHandler(commands.Cog):
    """Handle exceptions"""

    def __init__(self, bot: Nya_Nya):
        self.bot = bot
        self.emoji = "🤓"

    @commands.Cog.listener()
    async def on_command_error(self, ctx: NyaNyaContext, error):
        """
        Error handling class.
        """
        if isinstance(error, commands.errors.CheckFailure):
            error = getattr(error, 'original', error)
            if isinstance(error, commands.errors.NSFWChannelRequired):
                await ctx.send_exception(error)

        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send_exception(error)

        elif isinstance(error, commands.errors.CommandNotFound):
            await self.did_you_meant(ctx)

        elif isinstance(error, commands.errors.CommandOnCooldown):
            await ctx.send_exception(error)

        elif isinstance(error, commands.errors.NoPrivateMessage):
            await ctx.send_exception(error)

        elif isinstance(error, BadSpotify):
            await ctx.send_exception(error)

        elif isinstance(error, ItemNotFound):
            await ctx.send_exception(error)

        elif isinstance(error, NothingPlaying):
            await ctx.send_exception("Nothing is playing right now")

        elif isinstance(error, NoMoreSongsInCache):
            await ctx.send_exception("No more items stored in revrt cache")

        elif isinstance(error, OutOfbounds):
            await ctx.send_exception(error)

        elif isinstance(error, ForbidentoRemovePlaying):
            await ctx.send_exception("Cant remove currently playing")

        elif isinstance(error, NotConnected):
            await ctx.send_exception('No channel to join. Please either specify a valid channel or join one.')

        else:
            await ctx.send_error(error)

            error_text = "".join([line for line in
                                  traceback.TracebackException(type(error), error, error.__traceback__).format(
                                      chain=True)]).replace("``", "`\u200b`")
            try:
                await self.bot.error_webhook.send(f'{error}\nIgnoring exception in command {ctx.command}:')
                await self.bot.error_webhook.send(file=discord.File(io.StringIO(error_text), filename="error.py"))
            except:
                raise error

    async def did_you_meant(self, ctx):
        def get_name(command):
            return command.name

        def new_com(com: str) -> discord.Message:
            content = ctx.message.content
            content = content.strip(ctx.prefix).strip(" ")
            content = content.split(" ")
            content[0] = com
            ctx.message.content = ctx.prefix + " ".join(content)

            return ctx.message

        commandz = self.bot.commands
        if ctx.author.id not in self.bot.owner_ids:
            filtered = await ctx.filter_commands(commandz, sort=True)
        else:
            filtered = commandz

        commandz = map(get_name, filtered)
        matches = tuple(map(self.bot.get_command, get_close_matches(ctx.invoked_with, commandz, 3)))
        if not matches:
            return

        embed = NyaEmbed(title="Did you meant?")
        for x, command in enumerate(matches):
            embed.add_field(name=f"> **{x + 1}.**", value=codeblock(
                f"<{command.name}{' ' + command.cog.qualified_name if command.cog else ''}>", "md"))

        message = await ctx.send(embed=embed)

        def check(reaction, member):
            if reaction.message.id != message.id:
                return False

            if ctx.author == member:
                return True
            else:
                return False

        reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]

        for x in range(len(matches)):
            await message.add_reaction(reactions[x])

        for _ in range(1):
            try:
                reaction, member = await self.bot.wait_for('reaction_add', timeout=10, check=check)
            except asyncio.TimeoutError:
                await message.delete()
                return

            await message.delete()

            ind = reactions.index(reaction.emoji)

            new_ctx = await self.bot.get_context(new_com(matches[ind].name), cls=type(ctx))
            await self.bot.invoke(new_ctx)


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
