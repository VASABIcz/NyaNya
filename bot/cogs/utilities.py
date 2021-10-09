import io
import sys
import time
import typing

import asyncpg
import discord
import expr
import humanize
import psutil
import qrcode
from discord.ext import commands

from bot.bot_class import Nya_Nya
from bot.context_class import NyaNyaContext
from utils.embeds import calculator_embed
from utils.functions_classes import NyaEmbed


class Misc(commands.Cog):
    """Some random commands"""

    def __init__(self, bot: Nya_Nya):
        self.emoji = "🤷"
        self.bot = bot

    @staticmethod
    async def ok(ctx: NyaNyaContext):
        await ctx.message.add_reaction("👌")

    @commands.command(name="ping")
    async def ping(self, ctx: NyaNyaContext):
        """
        Show bot and database latency.
        """
        t = time.time()
        query = "SELECT 1"
        await self.bot.pdb.fetch(query)
        tit = time.time() - t
        await ctx.message.reply(f"API `{self.bot.latency * 1000:.2f}` ms\nDB `{tit * 1000:.2f}` ms")

    @commands.guild_only()
    @commands.command(name="setprefix", aliases=['addprefix', 'apefix', 'newprefix'])
    async def add_prefix(self, ctx: NyaNyaContext, *, prefix):
        """
        Add a custom guild prefix.
        """
        query = "INSERT INTO prefixes(guild_id, prefix) VALUES ($1, $2)"
        try:
            await self.bot.pdb.execute(query, ctx.guild.id, prefix)
        except asyncpg.UniqueViolationError:
            pass

        await ctx.ok()

    @commands.guild_only()
    @commands.command(name="removeprefix", aliases=['delprefix', 'rprefix'])
    async def del_prefix(self, ctx: NyaNyaContext, prefix):
        """
        Remvoe a guild prefix.
        """
        query = "DELETE FROM prefixes WHERE prefix = $1 and guild_id = $2"
        await self.bot.pdb.execute(query, prefix, ctx.guild.id)
        await ctx.ok()

    @commands.guild_only()
    @commands.command(name="prefixlist", aliases=['prefixes'])
    async def prefixlist(self, ctx: NyaNyaContext):
        """
        Show a prefixe's for your guild.
        """
        query = "SELECT prefix FROM prefixes where guild_id = $1"
        prefixes = [x[0] for x in await self.bot.pdb.fetch(query, ctx.guild.id)]
        await ctx.send_list(prefixes, "Prefixes")

    @commands.command(name="calculate", aliases=['calc'])
    async def calculator(self, ctx, *, expresion):
        """Just a simple calculator"""
        result = expr.evaluate(expresion)
        embed = calculator_embed(expresion, result)
        await ctx.send(embed=embed)

    @commands.command()
    async def screenshot(self, ctx, url):
        """Create image from website."""
        async with self.bot.session.get(
                f"https://v2.convertapi.com/convert/web/to/png?Secret=Avb55RKO3PkE0MD5&Url={url}&StoreFile=true&ImageWidth=1920&ImageHeight=1080") as response:
            response = await response.json()
        img = response['Files'][0]['Url']
        embed = NyaEmbed(title="Result")
        embed.set_image(url=img)
        await ctx.send(embed=embed)

    @commands.command(name="info")
    async def info(self, ctx):
        """Sends info about bot."""
        owner = self.bot.get_user(self.bot.owner_ids[0])
        proc = psutil.Process()
        mem = proc.memory_full_info()

        embed = NyaEmbed(title=self.bot.user.name,
                         description=f"**Owner**\n```{owner.name}#{owner.discriminator}```")
        embed.add_field(name="Cpu usage", value=f"```{psutil.cpu_percent(interval=1)}%```")
        embed.add_field(name="Memory usage",
                        value=f"```{humanize.naturalsize(mem.rss)}```")  # humanize.naturalsize(mem.vms), humanize.naturalsize(mem.uss)
        embed.add_field(name="Thread count", value=f"```{proc.num_threads()}```")
        embed.add_field(name="<:python:873580938855063602>Python ver.",
                        value=f"```{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}```")
        embed.add_field(name="<:discordpy:873578526769577985>Discord ver.", value=f"```{discord.__version__}```")
        embed.add_field(name="<:os:873583928794021940>Running on", value=f"```{sys.platform}```")
        embed.add_field(name="<:people:873582832264568883>Guild count", value=f"```{len(self.bot.guilds)}```",
                        inline=False)
        embed.add_field(name="<:people:873582832264568883>Member count", value=f"```{len(self.bot.users)}```")
        embed.add_field(name="<:time:873585658520825876>Started",
                        value=f"```{humanize.naturaltime(self.bot.start_time)}```", inline=False)

        await ctx.send(embed=embed)

        # owner
        # Cpu, Memory, threads
        #   threading.active_count()
        #   cat /sys/class/thermal/thermal_zone*/temp
        # psutil
        # Guilds, Users
        # Uptime

    @commands.command(name="invite")
    async def send_invite(self, ctx):
        """Sends bot invite link."""
        embed = NyaEmbed(title="Invite", url=self.bot.invite)
        await ctx.send(embed=embed)

    @commands.command(name="avatar")
    async def send_icon(self, ctx, target: typing.Union[discord.Member, discord.User]):
        """Sends anyones avatar"""
        embed = NyaEmbed(title="Avatar")
        embed.add_field(name="png", value=f"[link]({target.avatar_url_as(format='png')})")
        embed.add_field(name="jpg", value=f"[link]({target.avatar_url_as(format='jpg')})")
        embed.add_field(name="default", value=f"[link]({target.avatar_url})")
        embed.set_image(url=target.avatar_url)
        await ctx.send(embed=embed)

    @commands.command(name="uptime", aliases=['running'])
    async def send_uptime(self, ctx):
        """Ssends bot uptime."""
        embed = NyaEmbed(title="Started", description=humanize.naturaltime(self.bot.start_time))
        await ctx.send(embed=embed)

    # @commands.is_owner()
    # @commands.command("teste")
    # async def lole(self, ctx, memer: discord.Member):
    #    query = "INSERT INTO users_avatar_log(user_id, avatar) VALUES ($1, $2)"
    #    query2 = "SELECT avatar FROM users_avatar_log WHERE user_id = $1"
    #    icon = memer.avatar_url_as(format="png")
    #    icon = BytesIO(await icon.read())
    #    await self.bot.pdb.execute(query, memer.id, icon.read())
    #    e = await self.bot.pdb.fetchval(query2, memer.id)
    #    xd = await ctx.send(file=discord.File(BytesIO(e), filename="test.png"))
    #    print("d")

    @commands.command(name="qrcode", aliases=['qr'])
    async def gen_qrcode(self, ctx, *, data: str):
        """
        Generates qr code img from text.
        """
        if data:
            img = qrcode.make(data)
            with io.BytesIO() as image_binary:
                img.save(image_binary, 'PNG')
                image_binary.seek(0)

                file = discord.File(image_binary, filename="image.png")
                embed = NyaEmbed(title="QR code")
                embed.set_image(url="attachment://image.png")
                await ctx.send(embed=embed, file=file)
        else:
            pass


def setup(bot):
    bot.add_cog(Misc(bot))
