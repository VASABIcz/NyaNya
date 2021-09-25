import random
import re

import discord
import wavelink
from discord.ext import commands

from bot.bot_class import Nya_Nya
from bot.context_class import NyaNyaContext
from utils.functions_classes import Track
from utils.functions_classes import time_converter

URL_REG = re.compile(r'https?://(?:www\.)?.+')
SPOTIFY_REG = re.compile(r'^(?:https://open\.spotify\.com|spotify)([/:])user\1([^/]+)\1playlist\1([a-z0-9]+)')

class Music(commands.Cog, wavelink.WavelinkMixin):

    def __init__(self, bot: Nya_Nya):
        self.bot = bot
        self.emoji = "🎶"

        if not hasattr(bot, "wavelink"):
            self.bot.wavelink = wavelink.Client(bot=bot)

        self.bot.loop.create_task(self.start_nodes())

        self.eqs = {'flat': wavelink.Equalizer.flat(),
                    'boost': wavelink.Equalizer.boost(),
                    'metal': wavelink.Equalizer.metal(),
                    'piano': wavelink.Equalizer.piano()}

    async def start_nodes(self):
        """Connect and intiate nodes."""
        await self.bot.wait_until_ready()

        if self.bot.wavelink.nodes:
            previous = self.bot.wavelink.nodes.copy()
            for node in previous.values():
                await node.destroy()

        for n in self.bot.cfg.NODES.values():
            await self.bot.wavelink.initiate_node(**n)
        return

    @wavelink.WavelinkMixin.listener('on_track_stuck')
    @wavelink.WavelinkMixin.listener('on_track_end')
    @wavelink.WavelinkMixin.listener('on_track_exception')
    async def on_player_stop(self, node: wavelink.Node, payload):
        await payload.player.do_next()

    @commands.command(name='connect')
    async def connect_(self, ctx, *, channel: discord.VoiceChannel = None):
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise discord.DiscordException('No channel to join. Please either specify a valid channel or join one.')

        await ctx.send(f'Connecting to **`{channel.name}`**')
        await ctx.player.connect(channel.id)

    @commands.command(aliases=['p'])
    async def play(self, ctx, *, query: str):
        """play a song"""
        player = ctx.player

        def search_yt(value):
            return f'ytsearch:{value}'

        if not player.is_connected:
            await ctx.invoke(self.connect_)

        query = query.strip('<>')
        if not URL_REG.match(query):
            queryl = [f'ytsearch:{query}', ]
        elif 'https://open.spotify.com/' in query:
            queryl = await self.bot.extractor(query)
            queryl = list(map(search_yt, queryl))
        else:
            queryl = [query, ]

        for query in queryl:
            tracks = await self.bot.wavelink.get_best_node().get_tracks(query)
            if not tracks:
                return await ctx.send('No songs were found with that query. Please try again.', delete_after=15)

            if isinstance(tracks, wavelink.TrackPlaylist):
                for track in tracks.tracks:
                    track = Track(track.id, track.info, requester=ctx.author)
                    await player.queue.put(track)
            else:
                track = tracks[0]
                track = Track(track.id, track.info, requester=ctx.author)
                await player.queue.put(track)

            if not player.is_playing:
                await player.do_next()

        else:
            if not tracks:
                return await ctx.send('No songs were found with that query. Please try again.', delete_after=15)
            if isinstance(tracks, wavelink.TrackPlaylist):
                await ctx.send(embed=track.embed)
                # await ctx.send(
                #     f'```ini\nAdded the playlist {tracks.data["playlistInfo"]["name"]} with {len(tracks.tracks)} songs to the queue.\n```',
                #     delete_after=15)
            else:
                await ctx.send(embed=track.embed)
                # await ctx.send(f'```ini\nAdded {track.title} to the Queue\n```', delete_after=15)

    @commands.command(aliases=['s', 'next'])
    async def skip(self, ctx: NyaNyaContext):
        """Skip currently plaing song"""
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
        random.shuffle(ctx.player.queue._queue)

    @commands.command(name='remove', aliases=['r', 'pop'])
    async def _remove(self, ctx: NyaNyaContext, index: int):
        """Removes a song from the queue at a given index."""
        if len(ctx.player.queue) == 0:
            return await ctx.send('Empty queue.')

        ctx.player.queue.remove(index - 1)
        await ctx.message.add_reaction('✅')

    @commands.command(aliases=['loopqueue', 'loopq', 'qloop'])
    async def loop(self, ctx: NyaNyaContext):
        """Loops the current queue"""
        ctx.player.queue.looped = True

    @commands.command(aliases=['unloop', 'queuer', 'rq'])
    async def rqueue(self, ctx: NyaNyaContext):
        """Releases the current queue"""
        ctx.player.queue.looped = False

    @commands.command(aliases=['eq'])
    async def equalizer(self, ctx: NyaNyaContext, *, equalizer: str):
        """Change the players equalizer."""

        return await ctx.send("Not functional due to library bug. :C")

        # if not ctx.player.is_connected:
        #    return

    #
    # eq = self.eqs.get(equalizer.lower(), None)
    #
    # if not eq:
    #    joined = "\n".join(self.eqs.keys())
    #    return await ctx.send(f'Invalid EQ provided. Valid EQs:\n\n{joined}')
    #
    # await ctx.send(f'Successfully changed equalizer to {equalizer}', delete_after=15)
    # await ctx.player.set_eq(eq)

    @commands.command()
    async def seek(self, ctx: NyaNyaContext, time: time_converter):
        """Seek to time in '1h 1m 1s 1ms' format"""
        await ctx.player.seek(int(time * 1000))

    @commands.command(aliases=['np', 'cp', 'nowplaying'])
    async def now_playing(self, ctx: NyaNyaContext):
        await ctx.send(embed=ctx.player.embed)

    @commands.command()
    async def queue(self, ctx):
        ...#


def setup(bot):
    bot.add_cog(Music(bot))
