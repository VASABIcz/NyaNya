import asyncio
import datetime

import aiohttp
import aioredis
import async_timeout
import asyncpg
import discord
import spotipy
from spotipy import SpotifyClientCredentials

from bot.context_class import NyaNyaContext
from bot.help_class import Nya_Nya_Help
from bot.utils.constants import COGS, STATIC_COGS, IGNORED, COG_DIR
from bot.utils.errors import *
from bot.utils.functions_classes import intents, NyaNyaCogs


class Nya_Nya(commands.AutoShardedBot):
    """
    custom shard bot class. OwO
    """
    def __init__(self, cfg):
        self.start_time = datetime.datetime.now()
        self.cfg = cfg
        self.vote = cfg.VOTE
        self.support = cfg.SUPPORT
        self.default_emoji = cfg.DEFAULT_EMOJI
        self.session = aiohttp.ClientSession()
        self.load_webhook()
        self.cog_manager = NyaNyaCogs(self, COGS, STATIC_COGS, IGNORED, COG_DIR)
        self._setuped = asyncio.Event()
        self.auth_manager = SpotifyClientCredentials(client_id=self.cfg.SPOTIFY_ID,
                                                     client_secret=self.cfg.SPOTIFY_SECTRET)
        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
        # self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(self.cfg.MONGO)
        self.prefixes = aioredis.from_url(self.cfg.REDIS_PREFIXES, decode_responses=True)
        self.wavelink_reload = False

        super().__init__(command_prefix=self._get_prefix,
                         intents=intents(),
                         activity=self.cfg.ACTIVITY if hasattr(self.cfg, 'ACTIVITY') else discord.Game(
                             name=f"{self.cfg.MAIN_PREFIX}help"),
                         description="IT JUST WORKS\nwell it doesn't,... STFU please",
                         owner_ids=self.cfg.OWNERS,
                         case_insensitive=True,
                         strip_after_prefix=True,
                         help_command=Nya_Nya_Help())

        self.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        # self.pdb: asyncpg.Pool = await asyncpg.create_pool(**self.cfg.DB_CREDENTIALS)
        # await self.pdb.execute(sql_template.GLOBAL)  # execute initial db query

        # TODO in future add this functionality to reaction menu

        async def bok(ctx):
            self.dispatch("after_invoke", ctx)

        self._after_invoke = bok

        await self.wait_until_ready()

        self.instance_name = self.encod

        # await self.pdb.execute(sql_template.INSTANCE.format(id=self.instance_name))

        self.invite = discord.utils.oauth_url(self.user.id, discord.Permissions(8))  # TODO change permisions etc.
        self.owner_user = self.get_user(self.owner_ids[0])

        self._setuped.set()

        # await self.log_to_db()

    @property
    def encod(self):
        table = {"0": "a", "1": "b", "2": "c", "3": "d", "4": "e", "5": "f", "6": "g", "7": "h", "8": "i", "9": "j"}
        s = ""
        for i in str(self.user.id):
            s += table[i]

        return s

    # @property
    # async def user_bans(self) -> list:
    #     return [x[0] for x in await self.pdb.fetch("SELECT id FROM users where banned = true")]
    #
    # @property
    # async def guild_bans(self) -> list:
    #     return [x[0] for x in await self.pdb.fetch("SELECT id FROM guilds where banned = true")]
    #
    # @property
    # async def bans(self):
    #     return [x[0] for x in await self.pdb.fetch(
    #         "SELECT id FROM users where banned = true UNION SELECT id FROM guilds where banned = true")]

    async def prefixess(self, guild_id):
        return await self.prefixes.smembers(f'{self.instance_name}_{guild_id}')

    async def on_ready(self):
        """
        Bot is ready to run.
        """
        print(f"[*] LOADED {self.latency * 1000:.2f} ms")
        # await self.log_to_db()

    async def on_connect(self):
        """
        Connection established to discord.
        """
        print("[*] CONNECTED")

    async def on_message_edit(self, before, after):
        if before.content != after.content and self._blacklist(after):
            # prevents double invocation ex.: (when u send spotify url it edits message and adds embed)
            await self.process_commands(after)

    async def run(self):
        """
        Run bot.
        """
        # self.add_check(self._blacklist)
        self.load_extension("jishaku")
        self.get_cog("Jishaku").emoji = "👨‍💻"

        for cog in COGS:
            self.load_extension(f"bot.cogs.{cog}")

        await self.start(self.cfg.TOKEN)

    async def get_context(self, message, *, cls=None):
        """
        Uses custom context instead default.
        """
        return await super().get_context(message, cls=cls or NyaNyaContext)

    async def _blacklist(self, ctx):
        """
        Check if user is blacklisted.
        """
        bans = await self.bans
        if (ctx.author.id in bans or ctx.guild.id in bans) and ctx.author.id not in self.owner_ids:
            return False
        else:
            return True

    async def wait_until_setuped(self):
        await self._setuped.wait()

    async def _get_prefix(self, bot, msg):
        """
        Get prefix from db.
        """
        await self.wait_until_setuped()
        if msg.guild:
            try:
                async with async_timeout.timeout(0.05):  # 50ms normal query takes about 1ms
                    guild_prefixes = await self.prefixess(msg.guild.id)
            except asyncio.TimeoutError:
                guild_prefixes = ()
        else:
            guild_prefixes = ()

        return commands.when_mentioned_or(*guild_prefixes, self.cfg.MAIN_PREFIX)(self, msg)

    async def add_prefix(self, ctx, prefix):
        await self.prefixes.sadd(f'{self.instance_name}_{ctx.guild.id}', prefix)

    async def remove_prefix(self, ctx, prefix):
        await self.prefixes.srem(f'{self.instance_name}_{ctx.guild.id}', prefix)

    def load_webhook(self):
        a = discord.AsyncWebhookAdapter(self.session)
        try:
            self.error_webhook = discord.Webhook.from_url(self.cfg.ERROR_WEBHOOK_URL, adapter=a)
        except Exception:
            ...
        try:
            self.report_webhook = discord.Webhook.from_url(self.cfg.REPORT_WEBHOOK_URL, adapter=a)
        except Exception:
            ...

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
