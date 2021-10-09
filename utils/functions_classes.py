import asyncio
import functools
import itertools
import json
import os
import random
import time
from dataclasses import dataclass

import async_timeout
import discord
import wavelink
import websockets
from discord.ext import commands
from discord.ext.commands import MemberConverter
from pygount import SourceAnalysis

from utils.constants import EMBED_COLOR


def to_time(time) -> str:
    time = int(time)
    m, s = divmod(time, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)

    return f"{f'{d}d ' if d else ''}{f'{h}h ' if h else ''}{f'{m}m ' if m else ''}{f'{s}s' if s else ''}"


class NyaEmbed(discord.Embed):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, colour=EMBED_COLOR)


class Unbuffered:
    """
    Used for stdout and stderr.
    """

    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()

    def writelines(self, datas):
        self.stream.writelines(datas)
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)


@dataclass
class CodeBlock:
    """Custom class for string code and language"""
    text: str
    language: str

    def to_codeblock(self) -> str:
        return codeblock(self.text, self.language)


class cfg:
    """
    Parse cfg.json to class.
    """

    def __init__(self, dict_):
        self.__dict__.update(dict_)


def intents():
    """
    Setup intents for bot.
    """
    intents = discord.Intents.all()
    # intents.bans = False
    # intents.integrations = False
    # intents.invites = False
    # intents.presences = False
    return intents


async def ws_ext(stonks: str) -> dict or str:
    """
    Used to comunicate with ydl websocket server.
    """
    async with websockets.connect("ws://ydlwebsocketapi.herokuapp.com", max_size=1_000_000_000) as websocket:
        await websocket.send(stonks)
        while True:
            response = await websocket.recv()
            if response == "PING":
                pass
            else:
                break

    response = json.loads(response)
    if 'error' in response:
        print(response['video'], response['error'])
        return "error"
    else:
        return response


async def scrap(URL: str, timeout=600) -> bool:
    if 'expire=' in URL:
        x = URL.find('expire=') + 7
        y = URL.find('&ei')
    else:
        x = URL.find('expire/') + 7
        y = URL.find('/ei/')
    ur = int(URL[x:y])
    ur += -timeout
    tim = int(time.time())
    if ur <= tim:
        return True
    else:
        return False


def codeblock(text, language="") -> str:
    """
    Convert message to codeblock.
    :param text:
    :param language:
    :return:
    """
    return f"```{language}\n{text}```"


def strip_codeblock(text) -> CodeBlock:
    """
    Get raw message from codeblock quotes.
    :param text:
    :return:
    """
    text = text.strip("```")

    posible_language = text[:text.find("\n")]

    if " " in posible_language:
        return CodeBlock(text)
    else:
        code = text[text.find("\n") + 1:]
        language = text[:text.find("\n") + 1]

        return CodeBlock(code, language)


class NyaNyaPages:
    """
    Custom implementation of interactive embed.
    """

    def __init__(self, ctx: commands.Context, data, owner=None, cb_language="", title=None, max=None, delete=False):
        self.max = 4096 if not max else max
        self.actual_len = self.max - len("```\n```") - len(cb_language)
        self.data = data
        self.owner = MemberConverter().convert(ctx, owner) if owner else ctx.author
        self.pages = [self.data[i:i + self.actual_len] for i in range(0, len(data), self.actual_len)]
        self.current_page = 0
        self.title = title
        self.cb_language = cb_language
        self.delete = delete

        self.ctx = ctx
        self.bot = self.ctx.bot

        self.task: asyncio.Task = self.bot.loop.create_task(self.run())
        self.closed = False

    def __exit__(self, exc_language, exc_val, exc_tb):
        self.task.cancel()

    async def close(self, delete=True):
        self.closed = True

        if delete:
            await self.message.delete()
        else:
            await self.message.edit(embed=self.embed)

        self.task.cancel()

    @property
    def embed(self):
        embed = NyaEmbed(title=self.title if self.title else "paginator",
                         description=codeblock(self.pages[self.current_page], language=self.cb_language))
        embed.set_footer(text=f"Page: <{self.current_page + 1}/{len(self.pages)}>" if not self.closed else "Closed",
                         icon_url=self.bot.user.avatar_url)

        return embed

    async def add_rections(self):
        await self.message.add_reaction("⏪")
        await self.message.add_reaction("◀️")
        await self.message.add_reaction("▶️")
        await self.message.add_reaction("⏩")
        await self.message.add_reaction("🗑️")

    def check(self, reaction, member):
        if reaction.message.id != self.message.id:
            return False

        if self.owner == None:
            return True
        elif self.owner == member:
            return True
        else:
            return False

    async def run(self):
        self.message = await self.ctx.send(embed=self.embed)

        await self.add_rections()

        while not self.bot.is_closed() and not self.task.cancelled():
            try:
                reaction, member = await self.bot.wait_for('reaction_add', timeout=10 * 60, check=self.check)
                old_page = self.current_page
            except TimeoutError:
                await self.close(delete=self.delete)
                break

            if reaction.emoji == "🗑️":
                await self.close()

            elif reaction.emoji == "⏪":
                self.current_page = 0

            elif reaction.emoji == "⏩":
                self.current_page = len(self.pages) - 1

            elif reaction.emoji == "◀️":
                self.current_page = max(self.current_page - 1, 0)

            elif reaction.emoji == "▶️":
                self.current_page = min(self.current_page + 1, len(self.pages) - 1)

            await reaction.remove(member)
            if old_page != self.current_page:
                await self.message.edit(embed=self.embed)


class NyaNyaCogs:
    """
    Custom class for managing cogs.
    """
    def __init__(self, bot, cogs=None, static_cogs=None, ignored=None, replace=""):
        if ignored is None:
            ignored = []

        if static_cogs is None:
            static_cogs = []

        if cogs is None:
            cogs = []

        self.bot = bot
        self.replace = replace

        self.cogs = cogs
        self.static = static_cogs
        self.ignored = ignored
        self._all = self.cogs + self.static

    def get_filename(self, cog):
        name = cog.__cog_name__
        return str(cog)[1:str(cog).find(name) - 1].replace(self.replace, "")

    def add_cogs(self, cogs):
        if isinstance(cogs, str):
            cogs = cogs.split(" ")
            self.cogs.extend(cogs)

        elif isinstance(cogs, list or tuple):
            self.cogs.extend(cogs)


    async def remove_cog(self, cogs):
        if isinstance(cogs, str):
            cogs = cogs.split(" ")


        for cog in cogs:
            if not cog in self.static:
                self.cogs.remove(cog)
                if cog in self.unloadable:
                    self.bot.unload_extension(f"bot.cogs.{cog}")

    @property
    def get_cogs(self):
        cogs = dict(self.bot.cogs)
        for ignored in self.ignored:
            cogs.pop(ignored)

        return [self.get_filename(cog) for cog in cogs.values()]


    @property
    def unloadable(self):
        unloadable = self.get_cogs

        for cog in self.static:
            unloadable.remove(cog)

        return unloadable

    @property
    def reloadable(self):
        reloadable = self.get_cogs

        return reloadable

    @property
    def loadable(self):
        loadable = self.cogs

        for cog in self.get_cogs:
            loadable.remove(cog)

        return loadable

    @property
    def all(self):
        return self._all


class Timer:
    def __init__(self):
        self._start = None
        self._end = None

    def start(self):
        self._start = time.perf_counter()

    def stop(self):
        self._end = time.perf_counter()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def __int__(self):
        return round(self.time)

    def __float__(self):
        return self.time

    def __str__(self):
        return str(self.time)

    def __repr__(self):
        return f"<Timer time={self.time}>"

    @property
    def time(self):
        if self._end is None:
            raise ValueError("Timer has not been ended.")
        return self._end - self._start


class CodeConveter(commands.Converter):
    """
    Custom converter for converting files or codeblock to Codeblock class (text, codeblock_language)
    If used as converter. file part doesnt work and acts like strip_codeblock !!!
    """

    async def convert(self, ctx, argument) -> CodeBlock:
        file: discord.Attachment = ctx.message.attachments[0] if ctx.message.attachments else None

        if file:
            code = (await file.read()).decode()
            code = CodeBlock(code, file.filename.split(".")[-1])
        else:
            code = strip_codeblock(argument)

        return code


class CodeCounter:
    def __init__(self):
        self.code = 0
        self.docs = 0
        self.empty = 0

    def __iter__(self):
        return iter((self.code, self.docs, self.empty))

    def __repr__(self):
        return f"Code: {self.code} Docs: {self.docs} Empty: {self.empty}"

    def count(self, folder):
        for subdir, _, files in os.walk(folder):
            for file in (f for f in files if f.endswith(".py")):
                analysis = SourceAnalysis.from_file(f"{subdir}/{file}", "pygount", encoding="utf-8")
                self.code += analysis.code_count
                self.docs += analysis.documentation_count
                self.empty += analysis.empty_count


# class SongQueue(asyncio.Queue):
#     def __getitem__(self, item):
#         if isinstance(item, slice):
#             return list(itertools.islice(self._queue, item.start, item.stop, item.step))
#         else:
#             return self._queue[item]
#
#     def __iter__(self):
#         return self._queue.__iter__()
#
#     def __len__(self):
#         return self.qsize()
#
#     def clear(self):
#         self._queue.clear()
#
#     def shuffle(self):
#         random.shuffle(self._queue)
#
#     def remove(self, index: int):
#         del self._queue[index]


# class VoiceState:
#     def __init__(self, bot, ctx: commands.Context):
#         self.bot = bot
#         self._ctx = ctx
#         self.current = None
#         self.voice = None
#         self.next = asyncio.Event()
#         self.songs = SongQueue()
#         self._loop = False
#         self._volume = 0.5
#         self.audio_player: asyncio.Task = bot.loop.create_task(self.audio_player_task())
#
#     def __del__(self):
#         self.audio_player.cancel()
#
#     @property
#     def loop(self):
#         return self._loop
#
#     @loop.setter
#     def loop(self, value: bool):
#         self._loop = value
#
#     @property
#     def volume(self):
#         return self._volume
#
#     @volume.setter
#     def volume(self, value: float):
#         self._volume = value
#
#     @property
#     def is_playing(self):
#         return self.voice and self.current
#
#     @property
#     def alone(self):
#         return not len(self.voice.channel.members) > 1
#
#     async def audio_player_task(self):
#         while True:
#             self.next.clear()
#             if not self.loop:
#                 try:
#                     async with timeout(5):
#                         print("waiting for song")
#                         self.current = await self.songs.get()
#                 except asyncio.TimeoutError:
#                     if self.alone:
#                         print("stoped")
#                         self.bot.loop.create_task(self.stop())
#                         return
#                     print("someone in voice")
#             self.current.source.volume = self._volume
#             self.voice.play(self.current.source, after=self.play_next_song)
#             await self.current.source.channel.send(embed=self.current.create_embed(), delete_after=60)
#             await self.next.wait()
#
#     def play_next_song(self, error=None):
#         if error:
#             raise Exception(error)
#         self.next.set()
#
#     def skip(self):
#         if self.is_playing:
#             self.voice.stop()
#
#     async def stop(self):
#         self.songs.clear()
#         try:
#             del self.bot.voice_states[self._ctx.guild.id]
#         except KeyError:
#             print("prop some desync")  # weird error stops when already stoped
#         if self.voice:
#             await self.voice.disconnect()
#         self.audio_player.cancel()


def run_in_executor(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, functools.partial(f, *args, **kwargs))

    return inner


class NyaNyaQueue(asyncio.Queue):
    def __init__(self, *args, **kwargs):
        self.looped = False

        super().__init__(*args, **kwargs)

    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]

    async def get(self):
        """Remove and return an item from the queue.

        If queue is empty, wait until an item is available.
        """

        while self.empty():
            getter = self._loop.create_future()
            self._getters.append(getter)
            try:
                await getter
            except:
                getter.cancel()  # Just in case getter is not done yet.
                try:
                    # Clean self._getters from canceled getters.
                    self._getters.remove(getter)
                except ValueError:
                    # The getter could be removed from self._getters by a
                    # previous put_nowait call.
                    pass
                if not self.empty() and not getter.cancelled():
                    # We were woken up by put_nowait(), but can't take
                    # the call.  Wake up the next in line.
                    self._wakeup_next(self._getters)
                raise
        if not self.looped:
            return self.get_nowait()
        else:
            self._queue.append(self._queue.popleft())
            return self._queue[0]


class Player(wavelink.Player):
    """Custom wavelink Player class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.queue = NyaNyaQueue()

        self.waiting = False

        # self.teardown_t = self.bot.loop.create_task(self.teardown_task())

    async def do_next(self) -> None:
        if self.is_playing or self.waiting:
            return

        try:
            self.waiting = True
            with async_timeout.timeout(5 * 60):
                track = await self.queue.get()
        except asyncio.TimeoutError:
            # No music has been played for 5 minutes, cleanup and disconnect...
            return await self.teardown()

        await self.play(track)
        self.waiting = False

    # def check(self, member, before, after):
    #     print("check")
    #     if not self.channel:
    #         return False
    #     if len(self.channel.members) == 1:
    #         return True
    #     else:
    #         return False
    # async def teardown_task(self):
    #     while True:
    #         xd = await self.bot.wait_for("voice_state_update", check=self.check)
    #         print(xd)

    @property
    def embed(self) -> NyaEmbed:
        track: Track = self.current

        embed = NyaEmbed(title=track.title, description=f"(link)[{track.uri}]")
        embed.set_image(url=track.thumb)
        embed.set_footer(icon_url=track.requester.avatar_url,
                         text=f"{track.requester.name} | {'⏸️' if self.paused else '▶️'} | {to_time(self.position / 1000)} / {to_time(track.length / 1000)}")

        return embed

    @property
    def channel(self):
        return self.bot.get_channel(self.channel_id)

    @property
    def guild(self):
        return self.bot.get_guild(self.guild_id)

    async def teardown(self):
        try:
            await self.destroy()
        except KeyError:
            pass


def time_converter(time: str) -> float:
    table = {"h": 3600, "m": 60, "s": 1, "ms": 0.001}
    actual_time = 0

    time = time.replace(" ", "").lower()

    for t, sec in table.items():
        xd = time.split(t)
        try:
            actual_time += float(xd[0]) * sec
        except ValueError:
            pass
        if len(xd) > 1:
            time = xd[1]

    return actual_time


class Track(wavelink.Track):
    """Wavelink Track object with a requester attribute."""

    __slots__ = ('requester',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

        self.requester = kwargs.get('requester')

    @property
    def embed(self) -> NyaEmbed:
        embed = NyaEmbed(title=self.title)
        embed.set_image(url=self.thumb)
        embed.set_footer(icon_url=self.requester.avatar_url,
                         text=f"{self.requester.name}")

        return embed


def max_len(text, lenght, end="..."):
    return text[:lenght - len(end)] + end
