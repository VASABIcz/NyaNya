import asyncio
import copy
import os
import signal
import sys
import time
import typing
from typing import *

import discord
import textdistance
from discord.ext import commands
from jishaku.shell import ShellReader

from bot.bot_class import Nya_Nya
from bot.context_class import NyaNyaContext
from bot.utils.embeds import std_embed, cogman_embed
from bot.utils.functions_classes import codeblock, CodeConveter, NyaEmbed


class GlobalChannel(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return await commands.TextChannelConverter().convert(ctx, argument)
        except commands.BadArgument:
            # Not found... so fall back to ID + global lookup
            try:
                channel_id = int(argument, base=10)
            except ValueError:
                raise commands.BadArgument(f'Could not find a channel by ID {argument!r}.')
            else:
                channel = ctx.bot.get_channel(channel_id)
                if channel is None:
                    raise commands.BadArgument(f'Could not find a channel by ID {argument!r}.')
                return


class Admin(commands.Cog):
    """mostly developer utility"""

    def __init__(self, bot: Nya_Nya):
        self.emoji = "💻"
        self.bot = bot

    @commands.is_owner()
    @commands.command(name="unload", hidden=True)
    async def unload(self, ctx: NyaNyaContext, *, cogs: str = "all"):
        """
        Unload a cog.
        """
        data = []
        unloadable_cogs = self.bot.cog_manager.unloadable
        cogs = " ".join(unloadable_cogs) if cogs == "all" else cogs

        for cog in cogs.split(" "):
            tim = time.time()
            if cog in unloadable_cogs:
                self.bot.unload_extension(f"bot.cogs.{cog}")
                data.append((f"**✅ {cog}**", codeblock(f" in {round(time.time() - tim, 3)}s")))
            else:
                data.append((f"**❌ {cog}**", codeblock(f" in {round(time.time() - tim, 3)}s")))

            await ctx.send(embed=cogman_embed(data))

    @commands.is_owner()
    @commands.command(name="reload", hidden=True)
    async def reload(self, ctx: NyaNyaContext, *, cogs: str = "all"):
        """
        Reload a cog.
        """
        reloadable_cogs = self.bot.cog_manager.reloadable
        cogs = " ".join(reloadable_cogs) if cogs == "all" else cogs
        data = []

        for cog in cogs.split(" "):
            tim = time.time()
            if cog in reloadable_cogs:
                self.bot.reload_extension(f"bot.cogs.{cog}")
                data.append((f"**✅ {cog}**", codeblock(f" in {round(time.time() - tim, 3)}s")))
            else:
                data.append((f"**❌ {cog}**", codeblock(f" in {round(time.time() - tim, 3)}s")))

        await ctx.send(embed=cogman_embed(data))

    @commands.is_owner()
    @commands.command(name="load", hidden=True)
    async def load(self, ctx: NyaNyaContext, *, cogs: str = "all"):
        """
        Load a cog.
        """
        loadable_cogs = self.bot.cog_manager.loadable
        cogs = " ".join(loadable_cogs) if cogs == "all" else cogs
        data = []

        for cog in cogs.split(" "):
            tim = time.time()
            if cog in loadable_cogs:
                self.bot.load_extension(f"bot.cogs.{cog}")
                data.append((f"**✅ {cog}**", codeblock(f" in {round(time.time() - tim, 3)}s")))
            else:
                data.append((f"**❌ {cog}**", codeblock(f" in {round(time.time() - tim, 3)}s")))

        await ctx.send(embed=cogman_embed(data))

    @commands.is_owner()
    @commands.command(name="cogs", hidden=True)
    async def _cogs(self, ctx: NyaNyaContext):
        """
        List a loaded extincions.
        """
        await ctx.send_list(self.bot.cog_manager.reloadable, "Cogs")

    @commands.is_owner()
    @commands.command(name="presence", hidden=True)
    async def change_presence(self, ctx: NyaNyaContext, *, presence):
        """
        Change a bot status.
        """
        await self.bot.change_presence(activity=discord.Game(name=presence))
        await ctx.ok()

    @commands.is_owner()
    @commands.command(name="kill", hidden=True)
    async def kill(self, ctx: NyaNyaContext):
        """
        !!FORCE SHUTDOWN!!
        """
        await self.bot.pdb.close()
        await self.bot.session.close()
        os.kill(os.getpid(), signal.SIGTERM)

    @commands.is_owner()
    @commands.command(name="error", hidden=True)
    async def make_error(self, ctx: NyaNyaContext):
        """
        Raise a exception for testing porpuses.
        """
        raise discord.DiscordException("GUD")

    @commands.is_owner()
    @commands.command(name="update", hidden=True)
    async def git_update(self, ctx: NyaNyaContext):
        """Simple update command."""
        proc = await asyncio.create_subprocess_shell(f'git pull origin master', stdout=asyncio.subprocess.PIPE,
                                                     stderr=asyncio.subprocess.PIPE)

        stdout, stderr = await proc.communicate()

        if stdout:
            await ctx.send(embed=std_embed("Stdout", stdout.decode()))
        if stderr:
            await ctx.send(embed=std_embed("Stderr", stderr.decode()))

        with ShellReader('pip3 install -r requirements.txt') as reader:
            data = ""
            async for line in reader:
                data += "\n" + line

            await ctx.send_pages(data)

        os.execl(sys.executable, 'python3', 'main.py', *sys.argv[1:])

    @commands.is_owner()
    @commands.command(name="restart", hidden=True)
    async def restart(self, ctx: NyaNyaContext):
        """Simple restart command"""
        os.execl(sys.executable, 'python3', 'main.py', *sys.argv[1:])

    @commands.is_owner()
    @commands.command(name="pull", hidden=True)
    async def git_pull(self, ctx: NyaNyaContext):
        """Downloads newest bot version"""
        proc = await asyncio.create_subprocess_shell('git pull origin master', stdout=asyncio.subprocess.PIPE,
                                                     stderr=asyncio.subprocess.PIPE)

        stdout, stderr = await proc.communicate()

        if stdout:
            await ctx.send(embed=std_embed("Stdout", stdout.decode()))
        if stderr:
            await ctx.send(embed=std_embed("Stderr", stderr.decode()))

        with ShellReader('pip3 install -r requirements.txt') as reader:
            data = ""
            async for line in reader:
                data += "\n" + line

            await ctx.send_pages(data, max=2000)

    @commands.is_owner()
    @commands.command(name="ban", hidden=True)
    async def ban_command(self, ctx, target: typing.Union[discord.User, discord.Guild]):
        """
        Bans a user or guild.
        """
        if isinstance(target, discord.Guild):
            query = "UPDATE guilds SET banned = true WHERE id = $1"
            await self.bot.pdb.execute(query, target.id)
        else:
            query = "UPDATE users SET banned = true WHERE id = $1"
            await self.bot.pdb.execute(query, target.id)

    @commands.is_owner()
    @commands.command(name="unban", hidden=True)
    async def unban_command(self, ctx: NyaNyaContext, target: typing.Union[discord.User, discord.Guild]):
        """
        Unbans a user or guild.
        """
        if isinstance(target, discord.Guild):
            query = "UPDATE guilds SET banned = false WHERE id = $1"
            await self.bot.pdb.execute(query, target.id)
        else:
            query = "UPDATE users SET banned = false WHERE id = $1"
            await self.bot.pdb.execute(query, target.id)
        await ctx.send()

    @commands.command(name="bans")
    async def bans(self, ctx: NyaNyaContext):
        """
        Show a list of banned users and guilds.
        """
        query = "SELECT id FROM users where banned = true"
        query2 = "SELECT id FROM guilds where banned = true"
        user_bans = [str(x[0]) for x in await self.bot.pdb.fetch(query)]
        guild_bans = [str(x[0]) for x in await self.bot.pdb.fetch(query2)]
        embed = NyaEmbed(title="Bans")
        embed.add_field(name="**User bans:**", value="\n".join(user_bans if user_bans else ("None",)))
        embed.add_field(name="**Guild bans:**", value="\n".join(guild_bans if guild_bans else ("None",)))
        await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.command(name="codetest", hidden=True)
    async def test_conveter(self, ctx: NyaNyaContext, *, data=""):
        code = await CodeConveter().convert(ctx, data)

        await ctx.send_pages(code.text, cb_language=code.language)

    @commands.is_owner()
    @commands.command(name="query", hidden=True)
    async def cust_conv(self, ctx: NyaNyaContext, query):
        # cache = ctx.guild._state.member_cache_flags.joined#
        # members = await ctx.guild.query_members(argument, limit=100, cache=cache)
        # members
        # await ctx.send(str(members))
        members = self.bot.users
        query = query  # .lower()

        results = [textdistance.damerau_levenshtein.similarity(query, x.name) for x in members]
        match = members[max(range(len(results)), key=results.__getitem__)]
        await ctx.send(str(match))

    @commands.command(hidden=True, aliases=["su"])
    async def sudo(self, ctx, channel: Optional[GlobalChannel], who: Union[discord.Member, discord.User], *,
                   command: str):
        """Run a command as another user optionally in another channel."""
        msg = copy.copy(ctx.message)
        channel = channel or ctx.channel
        msg.channel = channel
        msg.author = who
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        await self.bot.invoke(new_ctx)

    @commands.is_owner()
    @commands.command(hidden=True)
    async def testemb(self, ctx: NyaNyaContext, *, e):
        embed = NyaEmbed(title=e)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Admin(bot))
