import json
from json import loads, dumps

import aioredis
import discord
from discord.ext import commands

from bot.bot_class import Nya_Nya


class ReactionMenu:
    def __init__(self, redis: aioredis.Redis, bot: Nya_Nya, guild, channel, message=None):
        self.redis = redis
        self.bot = bot
        self.guild: discord.Guild = guild
        self.channel: discord.TextChannel = channel
        self.message = message
        self.running = True
        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        if not self.message:
            await self.generate_message()

        self.task_add = self.bot.loop.create_task(self.reaction_add())
        self.task_remove = self.bot.loop.create_task(self.reaction_remove())
        self.task_terminate = self.bot.loop.create_task(self.terminate_event())

    def check(self, payload):

        if payload.message_id == self.message.id and payload.user_id != self.bot.user.id:
            return True

        return False

    async def reaction_add(self):
        while True:
            payload = await self.bot.wait_for("raw_reaction_add", check=self.check)

            member: discord.Member = payload.member
            emoji = payload.emoji
            if emoji.id:
                emoji = f"<{'a' if emoji.animated else ''}:{emoji.name}:{emoji.id}>"
            else:
                emoji = emoji.name

            roles = await self.redis.hget(self.guild.id, key="roles")
            roles = json.loads(roles)

            role = roles[emoji]
            role = member.guild.get_role(role)

            await member.add_roles(role)

    async def reaction_remove(self):
        while True:
            payload = await self.bot.wait_for("raw_reaction_remove", check=self.check)

            member: discord.Member = self.bot.get_guild(payload.guild_id).get_member(payload.user_id)
            emoji = payload.emoji

            if emoji.id:
                emoji = f"<{'a' if emoji.animated else ''}:{emoji.name}:{emoji.id}>"
            else:
                emoji = emoji.name

            roles = await self.redis.hget(self.guild.id, key="roles")
            roles = json.loads(roles)

            role = roles[emoji]
            role = member.guild.get_role(role)

            await member.remove_roles(role)

    async def terminate_event(self):
        await self.bot.wait_for("raw_message_delete", check=lambda m: m.message_id == self.message.id)
        self.cancel()

    async def generate_message(self):
        roles = await self.redis.hget(self.guild.id, key="roles")
        roles = json.loads(roles)

        message_strings = []

        for emoji, role in roles.items():
            role = self.guild.get_role(role)
            if not role:
                # TODO remove role
                continue

            message_strings.append(f"{emoji} : `{role}`")

        message = "\n".join(message_strings)

        m = await self.channel.send(message)
        self.message = m

        await self.redis.hset(self.guild.id, mapping={"message": m.id})

        for emoji, _ in roles.items():
            try:
                await m.add_reaction(emoji)
            except:
                roles.pop(emoji)
                await self.redis.hset(self.guild.id, key="roles", value=dumps(roles))

    async def regenerate_message(self):
        roles = await self.redis.hget(self.guild.id, key="roles")
        roles = json.loads(roles)
        message_strings = []
        for emoji, role in roles.items():
            role = self.guild.get_role(role)
            if not role:
                # TODO remove role
                continue
            message_strings.append(f"{emoji} : `{role}`")
        message = "\n".join(message_strings)
        m = await self.message.edit(message)

        for emoji, _ in roles.items():
            try:
                await m.add_reaction(emoji)
            except:
                roles.pop(emoji)
                await self.redis.hset(self.guild.id, key="roles", value=dumps(roles))

    def cancel(self):

        self.running = False
        self.task_remove.cancel()
        self.task_add.cancel()
        try:
            self.task_terminate.cancel()
        except:
            pass


class Reactions(commands.Cog):
    """
    Create reaction role meni
    """

    def __init__(self, bot: Nya_Nya):
        self.bot = bot
        self.emoji = "😂"
        self.menus = {}
        self.redis = aioredis.from_url("redis://192.168.6.102", decode_responses=True)
        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()
        keys = await self.redis.keys()

        for key in keys:

            try:
                guild = self.bot.get_guild(int(key))
            except:
                continue
            if not guild:
                # TODO remove guild
                continue

            object: dict = await self.redis.hgetall(guild.id)

            if not object.get("roles") or not int(object.get("enabled")):
                continue

            if not object.get('channel'):
                continue

            channel = guild.get_channel(int(object['channel']))
            if not channel:
                await self.redis.hset(guild.id, mapping={"enabled": 0})
                continue

            if object.get("message"):
                m = await channel.fetch_message(int(object.get("message")))
                if not m:
                    await self.redis.hset(guild.id, mapping={"enabled": 0})
                    continue
            else:
                m = None

            menu = ReactionMenu(redis=self.redis, bot=self.bot, guild=guild, channel=channel, message=m)
            self.menus[guild.id] = menu

    @commands.command()
    async def create_menu(self, ctx):
        roles = await self.redis.hget(ctx.guild.id, key="roles")

        if not roles:
            return await ctx.send("There are no roles specified")

        await self.redis.hset(ctx.guild.id, mapping={"channel": ctx.channel.id, "guild": ctx.guild.id, "enabled": 1})

        menu = ReactionMenu(redis=self.redis, bot=self.bot, guild=ctx.guild, channel=ctx.channel)
        self.menus[ctx.guild.id] = menu

    @commands.command()
    async def move_menu(self, ctx):
        roles = await self.redis.hget(ctx.guild.id, key="roles")

        if not roles:
            return await ctx.send("There are no roles specified")

    @commands.command()
    async def remove_menu(self, ctx):
        object: dict = await self.redis.hgetall(ctx.guild.id)
        m = object.get('message')
        if not m:
            return await ctx.send("there is no running menu")

        await self.redis.hset(ctx.guild.id, key="enabled", value=0)
        await self.redis.hdel(ctx.guild.id, "channel", "message")

        try:
            ch = ctx.guild.get_channel(int(object.get('channel')))
            mes = await ch.fetch_message(int(m))
            await mes.delete()
        except:
            pass  # ignore bcs they manualy removed it

        men = self.menus.pop(ctx.guild.id)
        if men.running:
            men.close()

        await ctx.send("removed menu")

    @commands.command()
    async def regenerate_menu(self, ctx):
        roles = await self.redis.hget(ctx.guild.id, key="roles")

        if not roles:
            return await ctx.send("There are no roles specified")

    @commands.command()
    async def add_value(self, ctx, emoji, role: discord.Role):
        roles = await self.redis.hget(ctx.guild.id, key="roles")
        if roles:
            roles = loads(roles)
        else:
            roles = {}
        # TODO validate emoji
        roles[emoji] = role.id

        await self.redis.hset(ctx.guild.id, mapping={"roles": dumps(roles)})

    @commands.command()
    async def remove_value(self, ctx, emoji):
        roles = await self.redis.hget(ctx.guild.id, key="roles")
        if roles:
            roles = loads(roles)
        else:
            roles = {}

        roles.pop(emoji)

        await self.redis.hset(ctx.guild.id, mapping={"roles": dumps(roles)})

    @commands.command()
    async def clear_values(self, ctx):
        await self.redis.hset(ctx.guild.id, mapping={"roles": dumps({})})


def setup(bot):
    bot.add_cog(Reactions(bot))
