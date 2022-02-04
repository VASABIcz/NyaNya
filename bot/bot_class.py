import asyncio
import datetime

import aiohttp
import aioredis
import async_timeout
import discord

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
        self.prefixes = aioredis.from_url(self.cfg.REDIS_PREFIXES, decode_responses=True)

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
        # TODO in future add this functionality to reaction menu

        async def bok(ctx):
            self.dispatch("after_invoke", ctx)

        self._after_invoke = bok

        await self.wait_until_ready()

        self.instance_name = self.encod

        self.invite = discord.utils.oauth_url(self.user.id, discord.Permissions(8))  # TODO change permisions etc.
        self.owner_user = self.get_user(self.owner_ids[0])

        self._setuped.set()


    @property
    def encod(self):
        table = {"0": "a", "1": "b", "2": "c", "3": "d", "4": "e", "5": "f", "6": "g", "7": "h", "8": "i", "9": "j"}
        s = ""
        for i in str(self.user.id):
            s += table[i]

        return s

    async def prefixess(self, guild_id):
        return await self.prefixes.smembers(f'{self.instance_name}_{guild_id}')

    async def on_ready(self):
        """
        Bot is ready to run.
        """
        print(f"[*] LOADED {self.latency * 1000:.2f} ms")
        guild: discord.Guild = self.get_guild(793508687729786880)
        ch: discord.TextChannel = guild.channels[0]
        x = await ch.create_invite()
        print(x)
        # await self.log_to_db()

    async def on_connect(self):
        """
        Connection established to discord.
        """
        print("[*] CONNECTED")

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