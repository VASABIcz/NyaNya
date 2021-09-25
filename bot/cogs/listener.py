from io import BytesIO

import asyncpg
import discord
from discord.ext import commands

from bot.bot_class import Nya_Nya


class Listener(commands.Cog):
    """Used to log in db"""

    def __init__(self, bot: Nya_Nya):
        self.bot = bot


    @commands.Cog.listener("on_member_join")
    async def log_member_join(self, member: discord.Member):
        query2 = "INSERT INTO users(id, name, discriminator) VALUES ($1, $2, $3)"
        query3 = "INSERT INTO users_in_guilds(guild_id, user_id) VALUES ($1, $2)"
        query1 = "UPDATE users_in_guilds SET joined = true WHERE guild_id = $1 and user_id = $2"
        try:
            await self.bot.pdb.execute(query2, member.id, member.name, int(member.discriminator))
        except asyncpg.UniqueViolationError:
            pass
        try:
            await self.bot.pdb.execute(query3, member.guild.id, member.id)
        except asyncpg.UniqueViolationError:
            await self.bot.pdb.execute(query1, member.guild.id, member.id)

        inviter = await self.bot.tracker.fetch_inviter(member)
        if inviter:
            print(inviter)
            await self.bot.report_webhook.send(f"{inviter}")

    @commands.Cog.listener("on_member_remove")
    async def log_member_leave(self, member):
        query3 = "UPDATE users_in_guilds SET joined = false WHERE guild_id = $1 and user_id = $2"
        await self.bot.pdb.execute(query3, member.guild.id, member.id)

    @commands.Cog.listener("on_guild_join")
    async def log_guild_join(self, guild):
        query = "INSERT INTO guilds(id) VALUES ($1)"
        query4 = "UPDATE guilds SET joined = true WHERE id = $1"
        query2 = "INSERT INTO users(id, name, discriminator) VALUES ($1, $2, $3)"
        query3 = "INSERT INTO users_in_guilds(guild_id, user_id) VALUES ($1, $2)"
        query5 = "UPDATE users_in_guilds SET joined = true WHERE guild_id = $1 and user_id = $2"
        query6 = "UPDATE users_in_guilds SET joined = false WHERE guild_id = $1"

        await self.bot.pdb.execute(query6, guild.id)

        try:
            await self.bot.pdb.execute(query, guild.id)
        except asyncpg.UniqueViolationError:
            await self.bot.pdb.execute(query4, guild.id)
        for member in guild.members:
            try:
                await self.bot.pdb.execute(query2, member.id, member.name, int(member.discriminator))
            except asyncpg.UniqueViolationError:
                pass
            try:
                await self.bot.pdb.execute(query3, guild.id, member.id)
            except asyncpg.UniqueViolationError:
                await self.bot.pdb.execute(query5, guild.id, member.id)

        # Known bug when bot joins guild and left, users betwean that time will be still counted as joined
        # 1. solution wehn bot lefts all users will be treated as left
        # 2. when bot joins guild make all members left and then make them joined # I think this will be better
        # coud actualy keep track of people who left when bot was still in guild (query6)
        await self.bot.report_webhook.send(f"Bot joined: ```{guild.id}```")

    @commands.Cog.listener("on_guild_remove")
    async def log_guild_leave(self, guild):
        query4 = "UPDATE guilds SET joined = false WHERE id = $1"

        await self.bot.pdb.execute(query4, guild.id)

        await self.bot.report_webhook.send(f"Bot left: ```{guild.id}```")

    @commands.Cog.listener("on_guild_update")
    async def log_guild_update(self, before, after):
        ...
        # name,

    @commands.Cog.listener("on_user_update")
    async def log_user_update(self, before: discord.User, after: discord.User):
        query = "INSERT INTO users_avatar_log(user_id, avatar) VALUES ($1, $2)"

        if before.avatar != after.avatar:
            icon = after.avatar_url
            icon = BytesIO(await icon.read())
            await self.bot.pdb.execute(query, before.id, icon.read())

        # e = await self.bot.pdb.fetchval(query2, memer.id)
        # await ctx.send(file=discord.File(BytesIO(e), filename="test.png"))

        # neme, avatar, discriminator

    # async def cog_before_invoke(self, ctx):  # cog_after_invoke maybe
    #    await self.log_to_db()

    # async def bot_check_once(self, ctx):
    #     await self.log_to_db()


def setup(bot: Nya_Nya):
    bot.add_cog(Listener(bot))
