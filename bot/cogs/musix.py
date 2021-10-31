import asyncio
import re
from math import floor

import discord
import wavelink
from discord.ext import tasks

from bot.bot_class import Nya_Nya
from bot.context_class import NyaNyaContext
from bot.utils.errors import *
from bot.utils.functions_classes import Track, time_converter, codeblock, run_in_executor, max_len, NyaEmbed

URL_REG = re.compile(r'https?://(?:www\.)?.+')
SPOTIFY_REG = re.compile(r'^(?:https://open\.spotify\.com|spotify)([/:])user\1([^/]+)\1playlist\1([a-z0-9]+)')


class NyaControler:
    """
    Responsive embed for music.
    """
    ...


class Music(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self, bot: Nya_Nya):
        self.bot = bot
        self.emoji = "🎶"

        if not hasattr(bot, "wavelink"):
            self.bot.wavelink = wavelink.Client(bot=bot, session=self.bot.session)

        self.start_nodes.start()

        self.eqs = {'flat':  wavelink.Equalizer.flat(),
                    'boost': wavelink.Equalizer.boost(),
                    'metal': wavelink.Equalizer.metal(),
                    'piano': wavelink.Equalizer.piano()}

    @tasks.loop(seconds=5.0)
    async def start_nodes(self):
        """
        Connect and intiate nodes.
        Also ensure that we are connected.
        """
        await self.bot.wait_until_ready()

        nodes = [n for n in self.bot.wavelink.nodes.values() if n.is_available]
        if not nodes or self.bot.wavelink_reload:
            if self.bot.wavelink.nodes:
                previous = self.bot.wavelink.nodes.copy()
                for node in previous.values():
                    await node.destroy()

            for n in self.bot.cfg.NODES.values():
                await self.bot.wavelink.initiate_node(**n)

            self.bot.wavelink_reload = False

    @run_in_executor
    def extractor(self, URL: str):
        songs = []
        if "https://open.spotify.com/playlist" in URL:
            try:
                yes = self.bot.sp.playlist(URL)
                items = yes['tracks']['items']
            except:
                raise Exception(f"{URL} is an invalid spotify url.")
            songs.extend(f"{item['track']['name']} {item['track']['artists'][0]['name']}" for item in items)
            nor = yes['tracks']
            for x in range(int((yes['tracks']['total'] - 1) / 100)):
                nor = self.bot.sp.next(nor)
                songs.extend(f"{item['track']['name']} {item['track']['artists'][0]['name']}" for item in nor['items'])

        elif "https://open.spotify.com/album" in URL:
            try:
                yes = self.bot.sp.album(URL)
                items = yes['tracks']['items']
            except:
                raise Exception(f"{URL} is an invalid spotify url.")
            songs.extend(f"{item['name']} {item['artists'][0]['name']}" for item in items)
            nor = yes['tracks']
            for x in range(int((yes['tracks']['total'] - 1) / 100)):
                nor = self.bot.sp.next(nor)
                songs.extend(f"{item['track']['name']} {item['track']['artists'][0]['name']}" for item in nor['items'])

        elif "https://open.spotify.com/track" in URL:
            try:
                yes = self.bot.sp.track(URL)
            except:
                raise Exception(f"{URL} is an invalid spotify url.")
            songs.append(yes['name'])
        else:
            return [URL]

        return songs


    @wavelink.WavelinkMixin.listener('on_track_stuck')
    @wavelink.WavelinkMixin.listener('on_track_end')
    @wavelink.WavelinkMixin.listener('on_track_exception')
    async def on_player_stop(self, node: wavelink.Node, payload):
        await payload.player.do_next()

    async def prepare_input(self, query):
        """
        Parses input to list of Lavalink compatible links.
        Currently supports youtube and spotify.
        """
        query = query.strip('<>')  # handle no embed link
        if not URL_REG.match(query):
            prepared = [f'ytsearch:{query}']
        elif 'https://open.spotify.com/' in query:
            prepared = await self.extractor(query)
            prepared = list(map(lambda v: f'ytsearch:{v}', prepared))
        else:
            prepared = [query]

        return prepared


    @commands.command(aliases=['p'])
    async def play(self, ctx: NyaNyaContext, *, query: str):
        """play a song"""

        player = ctx.player # player for current guild

        async def resolve_tracks(query) -> list[Track] or None:
            track = await self.bot.wavelink.get_best_node().get_tracks(query)

            if track is None:
                await ctx.send('No songs were found with that query. Please try again.', delete_after=15)
                return

            if isinstance(track, wavelink.TrackPlaylist):
                return [Track(track.id, track.info, requester=ctx.author) for track in track.tracks]
            else:
                track = track[0]
                return [Track(track.id, track.info, requester=ctx.author)]


        # parse input to lavalink compatible format
        prepared = await self.prepare_input(query)

        # search for songs
        tracks = await asyncio.gather(*[resolve_tracks(query) for query in prepared])


        # add all results to queue
        # and start playing
        for track in tracks:
            if not track:
                pass

            for t in track:
                await player.queue.put(t)

        if not player.is_playing:
            player.ignore = True
            await player.do_next()

        # send embed to inform everything is done
        await ctx.send(embed=tracks[0][0].embed, delete_after=30)

    @commands.command(name='connect', aliases=['join', 'c'])
    async def connect_(self, ctx, *, channel: discord.VoiceChannel = None):
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise NotConnected

        await ctx.send(f'Connecting to **`{channel.name}`**')
        await ctx.player.connect(channel.id)

    @play.before_invoke
    async def _connect(self, ctx):
        if not ctx.player.is_connected:
            await ctx.invoke(self.connect_)

    @commands.command(aliases=['s', 'next'])
    async def skip(self, ctx: NyaNyaContext):
        """Skip currently plaing song"""
        await ctx.player.stop()

    @commands.command(aliases=['st', 'jump'])
    async def skipto(self, ctx: NyaNyaContext, index: int):
        """skips to given index"""
        ctx.player.queue.skip_to(index - 1)
        ctx.player.ignore = True
        await ctx.player.stop()

    @commands.command()
    async def revert(self, ctx: NyaNyaContext):
        ctx.player.queue.revert()
        ctx.player.ignore = True
        await ctx.player.stop()

    @commands.command(aliases=['dc'])
    async def disconnect(self, ctx: NyaNyaContext):
        """Disconnects and clears queue"""
        await ctx.player.teardown()

    @commands.command(aliases=['clear'])
    async def stop(self, ctx: NyaNyaContext):
        """Clears queue and stops playing"""
        await ctx.player.stop()
        ctx.player.queue._queue.clear()

    @commands.command()
    async def pause(self, ctx: NyaNyaContext):
        """Pauses"""
        await ctx.player.set_pause(True)

    @commands.command()
    async def resume(self, ctx: NyaNyaContext):
        """Resumes"""
        await ctx.player.set_pause(False)

    @commands.command()
    async def volume(self, ctx: NyaNyaContext, volume: int):
        """Chnage volume"""
        await ctx.send("Not functional due to library bug. :C")

    @commands.command(aliases=['mix'])
    async def shuffle(self, ctx: NyaNyaContext):
        """Shuffles songs"""
        ctx.player.queue.shuffle()

    @commands.command(name='remove', aliases=['r', 'pop'])
    async def _remove(self, ctx: NyaNyaContext, index: int):
        """Removes a song from the queue at a given index."""
        if len(ctx.player.queue) == 0:
            return await ctx.send('Empty queue.')

        index -= 1

        if index == 1:
            raise ForbidentoRemovePlaying
        try:
            ctx.player.queue.remove(index - 1)
        except IndexError:
            raise OutOfbounds(index + 1)

    @commands.command(aliases=['loopqueue', 'loopq', 'qloop'])
    async def loop(self, ctx: NyaNyaContext):
        """Loops the current queue"""
        ctx.player.queue.loop = 2

    @commands.command(aliases=['loopo'])
    async def loopone(self, ctx: NyaNyaContext):
        """Loops the current queue"""
        ctx.player.queue.loop = 1

    @commands.command(aliases=['unloop', 'queuer', 'rq'])
    async def rqueue(self, ctx: NyaNyaContext):
        """Releases the current queue"""
        ctx.player.queue.loop = 0

    @commands.command(aliases=['eq'])
    async def equalizer(self, ctx: NyaNyaContext, *, equalizer: str):
        """Change the players equalizer."""

        return await ctx.send("Not functional due to library bug. :C")

        # if not ctx.player.is_connected:
        #    return
        # eq = self.eqs.get(equalizer.lower(), None)
        # if not eq:
        #    joined = "\n".join(self.eqs.keys())
        #    return await ctx.send(f'Invalid EQ provided. Valid EQs:\n\n{joined}')
        # await ctx.send(f'Successfully changed equalizer to {equalizer}', delete_after=15)
        # await ctx.player.set_eq(eq)

    @commands.command()
    async def seek(self, ctx: NyaNyaContext, time: time_converter):
        """Seek to time in '1h 1m 1s 1ms' format"""
        await ctx.player.seek(int(time * 1000))

    @commands.command(aliases=['np', 'cp', 'nowplaying'])
    async def now_playing(self, ctx: NyaNyaContext):
        if ctx.player.is_playing:
            await ctx.send(embed=ctx.player.embed)
        else:
            raise NothingPlaying

    @commands.command()
    async def queue(self, ctx: NyaNyaContext, page: int = 1):
        qlen = len(ctx.player.queue)
        items = 9

        x = floor(qlen // items)
        y = qlen % items

        page = min(page, x + 1)
        page = max(page, 1)

        embed = NyaEmbed(title="Queue", description=codeblock(f"{qlen} songs in queue"))
        embed.set_footer(icon_url=ctx.author.avatar_url,
                         text=f"{ctx.author.name} | {'⏸️' if ctx.player.paused else '▶️'} { ' | ' + ctx.player.queue.loop_emoji if ctx.player.queue.loop_emoji else ''} | page {page} out of {x + 1}")

        for n in range(6 if page <= x else y):
            item = ((page - 1) * items) + n
            embed.add_field(
                name=max_len(f"{item + 1}.{' (Now playing)' if item + 1 == 1 else ''} {ctx.player.queue[item].title}",
                             50),
                value=f"🔗[link]({ctx.player.queue[item].uri})", inline=False)
        for _ in range(3 - (len(embed.fields) % 3)):
            embed.add_field(name=f"\u200b", value=f"\u200b")

        await ctx.send(embed=embed)


    async def cog_check(self, ctx):
        nodes = [n for n in self.bot.wavelink.nodes.values() if n.is_available]
        if not nodes:
            await ctx.send("Our audio sending sever isn't available at the moment")
            return False

        return True


def setup(bot):
    bot.add_cog(Music(bot))