import asyncio
import datetime
import importlib
import io
import traceback
from difflib import get_close_matches
from pathlib import Path

import DiscordUtils
import aiohttp
import asyncpg
import discord
import spotipy
from spotipy import SpotifyClientCredentials

import cfg
from bot.context_class import NyaNyaContext
from bot.help_class import Nya_Nya_Help
from bot.utils.constants import COGS, STATIC_COGS, IGNORED, COG_DIR
from bot.utils.errors import *
from bot.utils.functions_classes import intents, NyaNyaCogs, CodeCounter, codeblock, NyaEmbed


class Nya_Nya(commands.AutoShardedBot):
    """
    custom shard bot class. OwO
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.session: aiohttp.ClientSession = aiohttp.ClientSession()
        self.start_time = datetime.datetime.now()
        self.vote = cfg.VOTE
        self.support = cfg.SUPPORT
        self.default_emoji = cfg.DEFAULT_EMOJI
        self.cog_manager = NyaNyaCogs(self, COGS, STATIC_COGS, IGNORED, COG_DIR)
        self.directory = str(Path(__file__).parent)
        self.loc = CodeCounter()
        self.loc.count(self.directory)

        self.auth_manager = SpotifyClientCredentials(client_id=self.cfg.SPOTIFY_ID,
                                                     client_secret=self.cfg.SPOTIFY_SECTRET)
        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)

        self.load_webhook()

        super().__init__(command_prefix=self._get_prefix,
                         intents=intents(),
                         activity=discord.Game(name=f"{self.cfg.MAIN_PREFIX}help"),
                         description="IT JUST WORKS\nwell it doesn\'t,... STFU please",
                         owner_ids=self.cfg.OWNERS,
                         case_insensitive=True,
                         strip_after_prefix=True,
                         help_command=Nya_Nya_Help())

        self.loop.create_task(self.__ainit__())

        self.tracker = DiscordUtils.InviteTracker(self)

        self.wavelink_reload = False

    async def log_to_db(self):
        query = "INSERT INTO guilds(id) VALUES ($1)"
        query2 = "INSERT INTO users(id, name, discriminator) VALUES ($1, $2, $3)"
        query3 = "INSERT INTO users_in_guilds(guild_id, user_id) VALUES ($1, $2)"

        for guild in self.guilds:
            try:
                await self.pdb.execute(query, guild.id)
            except asyncpg.UniqueViolationError:
                pass

            for member in guild.members:
                try:
                    await self.pdb.execute(query2, member.id, member.name, int(member.discriminator))
                except asyncpg.UniqueViolationError:
                    pass
                try:
                    await self.pdb.execute(query3, guild.id, member.id)
                except asyncpg.UniqueViolationError:
                    pass

    async def __ainit__(self):
        self.pdb: asyncpg.Pool = await asyncpg.create_pool(**self.cfg.DB_CREDENTIALS)
        with open("database/db.sql", "r") as f:
            file = f.read()
        await self.pdb.execute(file)

        await self.wait_until_ready()

        self.invite = discord.utils.oauth_url(self.user.id, discord.Permissions(8))  # TODO change permisions etc.
        self.owner_user = self.get_user(self.owner_ids[0])
        await self.log_to_db()

    def reload(self):
        self.cfg = importlib.reload(cfg)
        self.wavelink_reload = True
        self.load_webhook()

    def load_webhook(self):
        try:
            self.error_webhook = discord.Webhook.from_url(self.cfg.ERROR_WEBHOOK_URL,
                                                          adapter=discord.AsyncWebhookAdapter(self.session))
        except:
            pass
        try:
            self.report_webhook = discord.Webhook.from_url(self.cfg.REPORT_WEBHOOK_URL,
                                                           adapter=discord.AsyncWebhookAdapter(self.session))
        except:
            pass

    async def on_ready(self):
        """
        Bot is ready to run.
        """
        self.invite = discord.utils.oauth_url(self.user.id, discord.Permissions(8))  # TODO change permisions etc.
        print(f"[*] LOADED {self.latency * 1000:.2f} ms")
        await self.log_to_db()


    async def on_connect(self):
        """
        Connection established to discord.
        """
        print("[*] CONNECTED")

    async def on_message_edit(self, before, after):
        if before != after:  # prevents double invocation ex.: (when u send spotify url it edits message and adds custom embed)
            await self.process_commands(after)

    def run(self):
        """
        Run bot.
        """
        self.add_check(self._blacklist)
        self.load_extension("jishaku")
        self.get_cog("Jishaku").emoji = "👨‍💻"

        for cog in COGS:
            self.load_extension(f"bot.cogs.{cog}")

        super().run(self.cfg.TOKEN)

    async def get_context(self, message, *, cls=None):
        """
        Uses custom context instead default.
        """
        return await super().get_context(message, cls=cls or NyaNyaContext)

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
                await self.error_webhook.send(f'{error}\nIgnoring exception in command {ctx.command}:')
                await self.error_webhook.send(file=discord.File(io.StringIO(error_text), filename="error.py"))
            except:
                raise error

    async def _blacklist(self, ctx: NyaNyaContext):
        """
        Check if user is blacklisted.
        """
        bans = [x[0] for x in await self.pdb.fetch("SELECT id FROM users where banned = true")]
        user = ctx.author.id in bans

        if ctx.guild:
            bans2 = [x[0] for x in await self.pdb.fetch("SELECT id FROM guilds where banned = true")]
            guild = ctx.guild.id in bans2
        else:
            guild = False

        if (user or guild) and not ctx.author.id in self.owner_ids:
            return False
        else:
            return True

    async def _get_prefix(self, bot, msg):
        """
        Get prefix from db.
        """
        if msg.guild:
            guild_prefixes = (x[0] for x in
                              await self.pdb.fetch("SELECT prefix FROM prefixes where guild_id = $1", msg.guild.id) if
                              x is not None)
        else:
            guild_prefixes = ()

        return commands.when_mentioned_or(*guild_prefixes, self.cfg.MAIN_PREFIX)(self, msg)

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

        commandz = self.commands
        if ctx.author.id not in self.owner_ids:
            filtered = await ctx.filter_commands(commandz, sort=True)
        else:
            filtered = commandz

        commandz = map(get_name, filtered)
        matches = tuple(map(self.get_command, get_close_matches(ctx.invoked_with, commandz, 3)))
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
                reaction, member = await self.wait_for('reaction_add', timeout=10, check=check)
            except asyncio.TimeoutError:
                await message.delete()
                return

            await message.delete()

            ind = reactions.index(reaction.emoji)

            new_ctx = await self.get_context(new_com(matches[ind].name), cls=type(ctx))
            await self.invoke(new_ctx)

class NyaCog(commands.Cog):
    ...
