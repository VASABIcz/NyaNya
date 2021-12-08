import asyncio
import re
from difflib import get_close_matches
from math import floor, ceil
from urllib.parse import quote

import discord
import wavelink
from discord.ext import tasks
from wavelink.backoff import ExponentialBackoff

from bot.bot_class import Nya_Nya
from bot.context_class import NyaNyaContext
from bot.utils.errors import *
from bot.utils.functions_classes import Track, time_converter, codeblock, run_in_executor, max_len, NyaEmbed, Player

URL_REG = re.compile(r'https?://(?:www\.)?.+')
SPOTIFY_REG = re.compile(r'^(?:https://open\.spotify\.com|spotify)([/:])user\1([^/]+)\1playlist\1([a-z0-9]+)')

class Music(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self, bot: Nya_Nya):
        self.bot = bot
        self.emoji = "🎶"
        self.music_cache = self.bot.mongo_client.production.music_cache

        if not hasattr(bot, "wavelink"):
            self.bot.wavelink = wavelink.Client(bot=bot, session=bot.session)
        self.wavelink = self.bot.wavelink

        self.start_nodes.start()

        self.eqs = {'flat': wavelink.Equalizer.flat(),
                    'boost': wavelink.Equalizer.boost(),
                    'metal': wavelink.Equalizer.metal(),
                    'piano': wavelink.Equalizer.piano()}

    @tasks.loop(seconds=5.0)
    async def start_nodes(self):
        """
        Connect and initiate nodes.
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

    @wavelink.WavelinkMixin.listener('on_track_stuck')
    @wavelink.WavelinkMixin.listener('on_track_end')
    @wavelink.WavelinkMixin.listener('on_track_exception')
    async def on_player_stop(self, node: wavelink.Node, payload):
        await payload.player.do_next()

    @commands.Cog.listener()
    async def on_voice_state_update(self, m, b, a):
        # FOR LIKE 6th time
        # plz work
        # this should handle users manually moving, disconnecting bot

        if m == self.bot.user:  # only handle bot
            if b.channel != a.channel:  # only handle if bot changes channel ignore mutes etc.
                if b.channel and a.channel:
                    p = self.bot.wavelink.get_player(guild_id=m.guild.id, cls=Player)
                    await p.magic_pause()
                    # move (resume playing)
                elif b.channel and not a.channel:
                    p = self.bot.wavelink.get_player(guild_id=m.guild.id, cls=Player)
                    await p.teardown()
                    # disconnect (temrinate player)
                elif not b.channel and a.channel:
                    ...
                    # connect (nothing) cant happen manually

    @run_in_executor
    def extractor(self, URL: str) -> [str]:
        if "https://open.spotify.com/track" in URL:
            track = self.bot.sp.track(URL)
            if not track:
                raise BadSpotify(f"\"{URL}\" is invalid")
            return [f"{track['name']} {track['artists'][0]['name']}"]
        elif "https://open.spotify.com/playlist" in URL or "https://open.spotify.com/album" in URL:
            songs = []
            if "https://open.spotify.com/album" in URL:
                res = self.bot.sp.album(URL)
                if not res:
                    raise BadSpotify(f"\"{URL}\" is invalid")
                tracks = res['tracks']
                for _ in range(ceil((res['tracks']['total']) / 100)):
                    songs.extend(
                        f"{item['name']} {item['artists'][0]['name']}" for item in tracks['items'])
                    tracks = self.bot.sp.next(tracks)
                return songs
            else:
                res = self.bot.sp.playlist(URL)
                if not res:
                    raise BadSpotify(f"\"{URL}\" is invalid")
                tracks = res['tracks']
                for _ in range(ceil((res['tracks']['total']) / 100)):
                    songs.extend(
                        f"{item['track']['name']} {item['track']['artists'][0]['name']}" for item in tracks['items'])
                    tracks = self.bot.sp.next(tracks)
                return songs

        raise BadSpotify(f"\"{URL}\" is invalid")

    async def prepare_input(self, query: str) -> [str]:
        """
        Parses query to list of queries
        Currently supports youtube and spotify.
        """
        query = query.strip('<>')
        if 'https://open.spotify.com/' in query:
            prepared = await self.extractor(query)
        else:
            prepared = [query]

        return prepared

    async def fetch_track(self, ctx, query, retry_on_failure=True) -> list[Track] or None:
        """Custom implementation of wavelink.get_track()"""
        node = self.wavelink.get_best_node()
        backoff = ExponentialBackoff(base=1)

        if URL_REG.match(query):
            prepared = query
        else:
            prepared = f"ytsearch:{query}"

        for attempt in range(5):
            async with self.bot.session.get(f'{node.rest_uri}/loadtracks?identifier={quote(prepared)}',
                                            headers={'Authorization': node.password}) as resp:

                if not resp.status == 200 and retry_on_failure:
                    retry = backoff.delay()

                    await asyncio.sleep(retry)
                    continue

                elif not resp.status == 200 and not retry_on_failure:
                    return

                data = await resp.json()

                if not data['tracks']:
                    continue  # most of the time it returns none bcs overload so we try again

                if data['playlistInfo']:
                    await self.store_tracks(query, data['tracks'], playlist=True)
                    return [Track(track['track'], track['info'], requester=ctx.author) for track in data['tracks']]
                else:
                    await self.store_tracks(query, data['tracks'],
                                            playlist=False)  # we cache all results for better performane in future
                    return [Track(data['tracks'][0]['track'], data['tracks'][0]['info'],
                                  requester=ctx.author)]  # we want to return oly one result and thats the most acurate

    async def store_tracks(self, query: str, tracks: list[dict], playlist=True):
        """
        Cache data
        """
        t = [{'query': t['info']['title'], 'meta': [{'id': t['track'], 'data': t['info']}]} for t in
             tracks]  # track by its name

        if playlist:
            t.append(
                {'query': query,
                 'meta': [{'id': t['track'], 'data': t['info']} for t in tracks]})  # query and all its tracks
        else:
            t.append({'query': query,
                      'meta': [{'id': tracks[0]['track'], 'data': tracks[0]['info']}]})  # or one if not playlist

        for tt in t:
            await self.music_cache.update_one({'query': tt['query']}, {'$set': tt}, upsert=True)

    async def load_tracks(self, query: str) -> list[dict] or None:
        """
        Retrieve Tracks from cache
        """
        d = await self.music_cache.find_one({'query': query})  # find 100% match
        if d:
            return d['meta']
        else:
            # find best possible match
            res = await self.music_cache.find({"$text": {"$search": query}}).to_list(length=10)
            if not res:
                return
            best = get_close_matches(query, [x['query'] for x in res], 1)
            if not best:
                return
            for r in res:
                if r['query'] == best[0]:
                    return r['meta']

    async def get_data(self, query: str, ctx: NyaNyaContext) -> str or None:
        """
        Retrieve Tracks from cache.
        """
        tracks = await self.load_tracks(query)
        if tracks:
            print("cached")
            p = ctx.player
            for track in tracks:
                await p.queue.put(Track(track['id'], track['data'], requester=ctx.author))
                if not p.is_playing:
                    p.ignore = True
                    await p.do_next()
        else:
            return query

    async def fetch_data(self, ctx, query):
        print("fetched")
        tracks = await self.fetch_track(ctx, query)
        p = ctx.player
        for track in tracks:
            if track:
                await p.queue.put(track)
                if not p.is_playing:
                    p.ignore = True
                    await p.do_next()

    async def other_play(self, ctx: NyaNyaContext, query: str, cache=True):
        player = ctx.player  # player for current guild
        prepared = await self.prepare_input(query)

        if cache:
            left = await asyncio.gather(*[self.get_data(x, ctx) for x in prepared])
            left = [x for x in left if x != None]  # cleanup
        else:
            left = prepared

        if left:
            # if len(left) > 100:
            #     await ctx.send("This query may take a while")

            n = 50  # split to chunks
            chunks = [left[i * n:(i + 1) * n] for i in range((len(left) + n - 1) // n)]

            for tracks in chunks:
                await asyncio.gather(*[self.fetch_data(ctx, query) for query in tracks])
                # search for songs

        if player.queue[-1]:
            await ctx.send(embed=player.queue[-1].embed, delete_after=30)


    @commands.is_nsfw()
    @commands.command(aliases=['p'])
    async def play(self, ctx: NyaNyaContext, *, query: str):
        """play a song"""
        await self.other_play(ctx, query)

    @commands.cooldown(4, 60, commands.BucketType.user)
    @commands.is_nsfw()
    @commands.command(aliases=['pr'])
    async def playr(self, ctx: NyaNyaContext, *, query: str):
        """Plays without using internal cache may take longer time to load but will retrieve the best results"""
        await self.other_play(ctx, query, cache=False)

    @commands.command(name='connect', aliases=['join', 'c'])
    async def connect_(self, ctx, *, channel: discord.VoiceChannel = None):
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise NotConnected

        await ctx.send(f'Connecting to **`{channel.name}`**')
        await ctx.player.connect(channel.id)

    @playr.before_invoke
    @play.before_invoke
    async def _connect(self, ctx):
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
        """revert finished song"""
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

    @commands.is_nsfw()
    @commands.command(aliases=['np', 'cp', 'nowplaying'])
    async def playing(self, ctx: NyaNyaContext):
        if ctx.player.is_playing:
            await ctx.send(embed=ctx.player.embed)
        else:
            raise NothingPlaying

    @commands.is_nsfw()
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
