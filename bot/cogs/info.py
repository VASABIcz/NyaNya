import discord
from discord.ext import commands

from bot.bot_class import Nya_Nya
from bot.context_class import NyaNyaContext
from bot.utils.embeds import info_embed


class Info(commands.Cog):
    """utility extincion"""

    def __init__(self, bot: Nya_Nya):
        self.bot = bot
        self.emoji = "🤓"

    @commands.command(name="member")
    async def member_info(self, ctx: NyaNyaContext, member: discord.Member):
        """sends some info about member"""

        data = {"NAME:": member.name, "ID:": member.id, "CREATED AT:": member.created_at,
                "JOINED AT:": member.joined_at}
        await ctx.reply(embed=info_embed(ctx, "member", data, member.avatar_url))

    @commands.command(name="emoji")
    async def emoji_info(self, ctx: NyaNyaContext, emoji: discord.Emoji):
        """sends some info about guild emoji"""
        data = {"NAME:": emoji.name, "ID:": emoji.id, "URL:": f"[{emoji.url}]({emoji.url})",
                "CREATED AT:": emoji.created_at, "CREATOR:": emoji.user}
        await ctx.reply(embed=info_embed(ctx, "emoji", data, emoji.url))

    @commands.command(name="channel")
    async def channel_info(self, ctx: NyaNyaContext, channel):
        """sends some info about channel"""

        try:
            id = channel.strip("<>#")
            channel = self.bot.get_channel(int(id))
        except:
            return

        if str(channel.type) == "text":
            data = {"NAME:": channel.name, "ID:": channel.id, "CREATED AT:": channel.created_at, "TYPE:": channel.type,
                    "TOPIC:": channel.topic, "NSFW:": channel.nsfw}
        else:
            data = {"NAME:": channel.name, "ID:": channel.id, "CREATED AT:": channel.created_at, "TYPE:": channel.type,
                    "BITRATE:": channel.bitrate}

        await ctx.reply(embed=info_embed(ctx, "channel", data))


def setup(bot):
    bot.add_cog(Info(bot))
