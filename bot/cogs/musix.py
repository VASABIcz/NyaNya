import asyncio
import re
from difflib import get_close_matches
from math import floor
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
            self.bot.wavelink = wavelink.Client(bot=bot, session=self.bot.session)
        self.wavelink = self.bot.wavelink

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
        if 'https://open.spotify.com/' in query:
            prepared = await self.extractor(query)
        else:
            prepared = [query]

        return prepared

    @commands.Cog.listener()
    async def on_voice_state_update(self, m, b, a):
        # FOR LIKE 6th time
        # plz work
        # this should handle users manually moving, disconnecting bot and handle those events

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

    async def custom_query(self, ctx, query, retry_on_failure=True) -> list[Track] or None:
        """Custom implementation of wavelink.get_track()"""
        node = self.wavelink.get_best_node()
        backoff = ExponentialBackoff(base=1)

        for attempt in range(5):
            async with self.bot.session.get(f'{node.rest_uri}/loadtracks?identifier={quote(query)}',
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
                    await self.from_track_dict(query, data['tracks'], playlist=True)
                    return [Track(track['track'], track['info'], requester=ctx.author) for track in data['tracks']]
                else:
                    await self.from_track_dict(query, data['tracks'],
                                               playlist=False)  # we cache all results for better performane in future
                    return [Track(data['tracks'][0]['track'], data['tracks'][0]['info'],
                                  requester=ctx.author)]  # we want to return oly one result and thats the most acurate

    async def from_track_dict(self, query: str, tracks: list[dict], playlist=True):
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

    async def from_data(self, query: str) -> list[dict] or None:
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

    async def query_tracks(self, query: str, ctx: NyaNyaContext, cache=True) -> list[Track] or None:
        if cache:
            track = await self.from_data(query)
            if track:
                print("cached")
                return [Track(track['id'], track['data'], requester=ctx.author) for track in track]

        if URL_REG.match(query):
            prepared = query
        else:
            prepared = f"ytsearch:{query}"

        res = await self.custom_query(ctx, prepared)
        if not res:
            await ctx.send('No songs were found with that query. Please try again.', delete_after=15)

        return res

    async def _play(self, ctx: NyaNyaContext, query: str, cache=True):
        # method that represents play command
        # better than having 2 instances of the same code

        player = ctx.player  # player for current guild
        prepared = await self.prepare_input(query)

        if len(prepared) > 100:
            await ctx.send("This query may take a while")

        n = 8  # split to chunks
        final = [prepared[i * n:(i + 1) * n] for i in range((len(prepared) + n - 1) // n)]
        # big brain moment split insane amount of songs to smaller chunks to not blow up ur server :) # the more you know

        procesed = []
        for tracks in final:
            procesed.extend(
                await asyncio.gather(*[self.query_tracks(query, ctx, cache) for query in tracks]))  # search for songs

        # add all results to queue
        # and start playing
        for track in procesed:
            if not track:
                pass

            for t in track:
                await player.queue.put(t)

        if not player.is_playing:
            player.ignore = True
            await player.do_next()

        # send embed
        await ctx.send(embed=procesed[0][0].embed, delete_after=30)

    @commands.is_nsfw()
    @commands.command(aliases=['p'])
    async def play(self, ctx: NyaNyaContext, *, query: str):
        """play a song"""
        await self._play(ctx, query)

    @commands.cooldown(4, 60, commands.BucketType.user)
    @commands.is_nsfw()
    @commands.command(aliases=['pr'])
    async def playr(self, ctx: NyaNyaContext, *, query: str):
        """Plays without using internal cache may take longer time to load but will retrieve the best results"""
        await self._play(ctx, query, cache=False)

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

    @commands.is_nsfw()
    @commands.command(aliases=['np', 'cp', 'nowplaying'])
    async def now_playing(self, ctx: NyaNyaContext):
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
