import asyncio
import datetime
import io
import traceback
from difflib import get_close_matches
from math import floor
from pathlib import Path

import DiscordUtils
import aiohttp
import aiosqlite
import asyncpg
import discord
import spotipy
from spotipy import SpotifyClientCredentials

from bot.context_class import NyaNyaContext
from bot.help_class import Nya_Nya_Help
from utils.constants import COGS, STATIC_COGS, EMBED_COLOR
from utils.errors import *
from utils.functions_classes import intents, NyaNyaCogs, CodeCounter, run_in_executor, codeblock


class Nya_Nya(commands.AutoShardedBot):
    """
    custom shard bot class. OwO
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.session: aiohttp.ClientSession = aiohttp.ClientSession()
        self.start_time = datetime.datetime.now()
        self.vote = 'https://top.gg'  # TODO top.gg url
        self.support = 'https://discord.com'  # TODO support server idk
        self.default_emoji = "❓"
        self.cog_manager = NyaNyaCogs(self, COGS, STATIC_COGS)
        self.directory = str(Path(__file__).parent)
        self.voice_states = {}

        self.loc = CodeCounter()
        self.loc.count(self.directory)

        self.auth_manager = SpotifyClientCredentials(client_id=self.cfg.SPOTIFY_ID,
                                                     client_secret=self.cfg.SPOTIFY_SECTRET)
        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)

        try:
            self.error_webhook = discord.Webhook.from_url(cfg.ERROR_WEBHOOK_URL,
                                                          adapter=discord.AsyncWebhookAdapter(self.session))
        except:
            pass
        try:
            self.report_webhook = discord.Webhook.from_url(cfg.REPORT_WEBHOOK_URL,
                                                           adapter=discord.AsyncWebhookAdapter(self.session))
        except:
            pass

        super().__init__(command_prefix=self._get_prefix,
                         intents=intents(),
                         activity=discord.Game(name=f"{self.cfg.MAIN_PREFIX}help"),
                         description="IT JUST WORKS\nwell it doesn\'t,... STFU please",
                         owner_ids=self.cfg.OWNERS,
                         case_insensitive=True,
                         strip_after_prefix=True,
                         help_command=Nya_Nya_Help())

        self.loop.run_until_complete(self.__ainit_())

        self.tracker = DiscordUtils.InviteTracker(self)

    async def log_to_db(self):
        query = "INSERT INTO guilds(id) VALUES ($1)"
        query2 = "INSERT INTO users(id, name, discriminator) VALUES ($1, $2, $3)"
        query3 = "INSERT INTO users_in_guilds(guild_id, user_id) VALUES ($1, $2)"

        # while True:
        #     ...

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

    async def __ainit_(self):
        self.pdb: asyncpg.Pool = await asyncpg.create_pool(**self.cfg.DB_CREDENTIALS)
        self.db = await aiosqlite.connect(r"D:\backup\python_projects\bot_framework\db\DATABASE")

    async def on_ready(self):
        """
        Bot is ready to run.
        """
        print(f"[*] LOADED {self.latency * 1000:.2f} ms")
        self.invite = discord.utils.oauth_url(self.user.id, discord.Permissions(8))  # TODO change permisions etc.
        await self.log_to_db()

    async def on_connect(self):
        """
        Connection established to discord.
        """
        print("[*] CONNECTED")

    async def on_message_edit(self, before, after):
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

    # async def setup(self):
    #     """
    #     Db con.
    #     """
    #     self.pdb: asyncpg.Pool = await asyncpg.create_pool(**self.cfg.DB_CREDENTIALS)

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
            ...

        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send_exception(error)

        elif isinstance(error, commands.errors.CommandNotFound):
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

            embed = discord.Embed(title="Did you meant?", colour=EMBED_COLOR)
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










        elif isinstance(error, commands.errors.CommandOnCooldown):
            await ctx.send_exception(error)

        elif isinstance(error, commands.errors.NoPrivateMessage):
            await ctx.send_exception(error)

        elif isinstance(error, BadSpotify):
            await ctx.send_exception(error)

        elif isinstance(error, ItemNotFound):
            await ctx.send_exception(error)

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

    @run_in_executor
    def extractor(self, URL: str):
        songs = []
        if "https://open.spotify.com/playlist" in URL:
            try:
                yes = self.sp.playlist(URL)
                items = yes['tracks']['items']
            except:
                raise Exception(f"{URL} is an invalid spotify url.")
            songs.extend(f"{item['track']['name']} {item['track']['artists'][0]['name']}" for item in items)
            nor = yes['tracks']
            for x in range(floor(yes['tracks']['total'] / 100)):
                nor = self.sp.next(nor)
                songs.extend(f"{item['track']['name']} {item['track']['artists'][0]['name']}" for item in nor['items'])

        elif "https://open.spotify.com/track" in URL:
            try:
                yes = self.sp.track(URL)
            except:
                raise Exception(f"{URL} is an invalid spotify url.")
            songs.append(yes['name'])
        else:
            return [URL, ]

        return songs

class NyaCog(commands.Cog):
    ...
