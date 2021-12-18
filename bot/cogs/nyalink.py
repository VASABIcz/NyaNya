import asyncio
from json import dumps, loads
from math import ceil
from time import perf_counter

import aiohttp
import discord
from discord.ext import commands

from bot.utils.errors import BadSpotify
from bot.utils.functions_classes import NyaEmbed, to_time, max_len, codeblock, run_in_executor, time_converter


# TODO sync nya_link voice_state w bot
# not sure if it can work bcs i thin when bot dc it terminates all ws
# so duno

class NyaLink:
    def __init__(self, bot, uri, rest, nodes, session=None, loop=None):
        self.bot = bot
        self.uri = uri
        self.rest = rest
        self.session = session or aiohttp.ClientSession()
        self._loop = loop or asyncio.get_event_loop()
        self.bot.add_listener(self.voice_update, 'on_socket_response')

        self.closed = True

        self._loop.create_task(self._connect())
        self.task = None

        self._voice_state = {}
        self.last_voice_state = {}
        self.last_server_state = {}

        self.nodes = nodes
        self.ws = None

    @property
    async def ping(self) -> float:
        s = perf_counter()
        await self.rest_players()
        return perf_counter() - s

    @property
    def headers(self):
        return {"user_id": str(self.bot.user.id)}

    @property
    def is_connected(self) -> bool:
        return self.ws is not None and not self.ws.closed

    async def setup(self):
        nodes = self.nodes
        for node in nodes:
            print("adding node:", node['identifier'])
            await self.add_node(node)

        await asyncio.sleep(1)  # small chance that bot will stop playing hope this fixes it
        await self.sync()

    async def _connect(self):
        await self.bot.wait_until_ready()

        while self.closed:
            self.ws = await self.session.ws_connect(self.uri, headers=self.headers)
            print("connected")
            self.closed = False

            self.task = self._loop.create_task(self.listener())
            await self.setup()

    async def disconnect_all(self):
        """dc from all guilds"""
        for guild, channel in self._voice_state.values():
            if channel is not None:
                await self._get_shard_socket(self.bot.get_guild(guild).shard_id).voice_state(guild, None,
                                                                                             self_deaf=False)

    async def listener(self):
        while True:
            msg = await self.ws.receive()
            print(msg)
            if msg.type is aiohttp.WSMsgType.CLOSED:
                self.closed = True
                self._loop.create_task(self.disconnect_all())
                if not self.is_connected:
                    self._loop.create_task(self._connect())
                    self.listener().close()
            else:
                asyncio.create_task(self.process(loads(msg.data)))

    async def process(self, data):
        print('processing', data)
        if data['op'] == 'voice_state_request':
            gid = int(data['guild'])
            try:
                await self.send(op='voice_update', data=self.last_server_state[gid])
                await self.send(op='voice_update', data=self.last_voice_state[gid])
            except KeyError:
                pass
        elif data['op'] == 'play_response':
            channel = self.bot.get_channel(int(data['channel']))
            if channel is None:
                return

            await channel.send(embed=self.play_embed(data['data']))

    async def sync(self):
        # we connect with our new ws
        # only cost is small lag
        # its better than dcing tbh
        data = await self.rest_players()
        for guild_id, channel_id in data.items():
            print("syncing:", guild_id, channel_id)
            g = self.bot.get_guild(int(guild_id))
            await self._get_shard_socket(g.shard_id).voice_state(guild_id, channel_id, self_deaf=False)

    async def send(self, **data):
        if self.is_connected:
            data['user_id'] = self.bot.user.id
            data_str = dumps(data)
            if isinstance(data_str, bytes):
                data_str = data_str.decode('utf-8')
            await self.ws.send_str(data_str)

    async def play(self, guild, data, requester, channel, cache=True):
        await self.send(op='play', guild=guild, data=data, requester=requester, channel=channel, cache=cache)

    async def skip(self, guild_id):
        await self.send(op='skip', guild_id=guild_id)

    async def skip_to(self, guild_id, index):
        await self.send(op='skip_to', guild_id=guild_id, index=index)

    async def stop(self, guild_id):
        await self.send(op='stop', guild_id=guild_id)

    async def loop(self, guild_id, loop):
        await self.send(op='loop', guild_id=guild_id, loop=loop)

    async def seek(self, guild_id, time):
        await self.send(op='seek', guild_id=guild_id, time=time)

    async def revind(self, guild_id):
        await self.send(op='revind', guild_id=guild_id)

    async def remove(self, guild_id, index):
        await self.send(op='remove', guild_id=guild_id, index=index)

    async def pause(self, guild_id, pause):
        await self.send(op='pause', guild_id=guild_id, pause=pause)

    async def shuffle(self, guild_id):
        await self.send(op='shuffle', guild_id=guild_id)

    async def destroy(self, guild_id):
        await self.send(op='destroy', guild_id=guild_id)

    async def add_node(self, data):
        await self.send(op='add_node', data=data)

    async def move_player(self, guild_id, node=None):
        await self.send(op='move', guild_id=guild_id, node=node)

    async def rest_player_data(self, guild_id):
        res = await self.session.get(f"{self.rest}/player_data?user={self.bot.user.id}&guild={guild_id}")
        res = await res.text()
        return loads(res)

    async def rest_track_data(self, guild_id, index=0):
        res = await self.session.get(f"{self.rest}/track_data?user={self.bot.user.id}&guild={guild_id}&index={index}")
        res = await res.text()
        return loads(res)

    async def rest_status(self):
        res = await self.session.get(f'{self.rest}/status')
        res = await res.text()
        return loads(res)

    async def rest_players(self):
        res = await self.session.get(f'{self.rest}/players?user={self.bot.user.id}')
        res = await res.text()
        return loads(res)

    async def voice_update(self, data):
        # TODO ignore mute/def client and server side
        if not data or 't' not in data:
            return

        if data['t'] in ('VOICE_SERVER_UPDATE', 'VOICE_STATE_UPDATE'):
            if data['t'] == 'VOICE_STATE_UPDATE':
                d = data['d']

                if int(d['user_id']) != int(self.bot.user.id):
                    return
                try:
                    ch_id = int(d['channel_id'])
                except TypeError:
                    ch_id = None

                self._voice_state[int(d['guild_id'])] = ch_id
                self.last_voice_state[int(d['guild_id'])] = data

                await self.send(op='voice_update', data=data)
            else:
                self.last_server_state[int(data['d']['guild_id'])] = data
                await self.send(op='voice_update', data=data)

    def _get_shard_socket(self, shard_id: int):
        if isinstance(self.bot, commands.AutoShardedBot):
            try:
                return self.bot.shards[shard_id].ws
            except AttributeError:
                return self.bot.shards[shard_id]._parent.ws

        if self.bot.shard_id is None or self.bot.shard_id == shard_id:
            return self.bot.ws

    async def connect(self, ctx, channel_id):
        await self._get_shard_socket(ctx.guild.shard_id).voice_state(ctx.guild.id, channel_id, self_deaf=False)

    async def disconnect(self, ctx):
        await self._get_shard_socket(ctx.guild.shard_id).voice_state(ctx.guild.id, None, self_deaf=False)

    def play_embed(self, data: dict):
        track = data.get('track', None)

        if track is None:
            return NyaEmbed(title='No tracks were found for that query')

        requester = self.bot.get_user(track['requester'])
        track = track['track']

        if data['loop'] == 0:
            emoji = ""
        elif data['loop'] == 1:
            emoji = "🔂"
        else:
            emoji = "🔁"

        embed = NyaEmbed(title=track['title'], description=f"🔗[link]({track['uri']})")
        embed.set_image(url=f"https://img.youtube.com/vi/{track['identifier']}/hqdefault.jpg")
        embed.set_footer(icon_url=requester.avatar_url,
                         text=f"{requester.name} | {'⏸️' if data['paused'] else '▶️'} {' | ' + emoji if emoji else ''} | {to_time(data['position'] / 1000)} / {to_time(track['length'] / 1000)}")

        return embed


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.link = NyaLink(self.bot, uri=f'ws://{self.bot.cfg.NYALINK}', nodes=self.bot.cfg.NODES,
                                session=self.bot.session, loop=self.bot.loop,
                                rest=f"http://{self.bot.cfg.NYALINK}")
        self.link = self.bot.link

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
        return [URL]
        # raise BadSpotify(f"\"{URL}\" is invalid")

    def embed(self, data, new=True):
        track = data['queue'][-1 if new else 0]
        requester = self.bot.get_user(track['requester'])
        track = track['track']
        if data['loop'] == 0:
            emoji = ""
        elif data['loop'] == 1:
            emoji = "🔂"
        else:
            emoji = "🔁"

        embed = NyaEmbed(title=track['title'], description=f"🔗[link]({track['uri']})")
        embed.set_image(url=f"https://img.youtube.com/vi/{track['identifier']}/hqdefault.jpg")
        embed.set_footer(icon_url=requester.avatar_url,
                         text=f"{requester.name} | {'⏸️' if data['paused'] else '▶️'} {' | ' + emoji if emoji else ''} | {to_time(data['position'] / 1000)} / {to_time(track['length'] / 1000)}")

        return embed

    def play_embed(self, data: dict):
        track = data.get('track', None)
        player = data

        if track is None:
            return NyaEmbed(title='No tracks were found for that query')

        requester = self.bot.get_user(track['requester'])
        track = track['track']

        if player['loop'] == 0:
            emoji = ""
        elif player['loop'] == 1:
            emoji = "🔂"
        else:
            emoji = "🔁"

        embed = NyaEmbed(title=track['title'], description=f"🔗[link]({track['uri']})")
        embed.set_image(url=f"https://img.youtube.com/vi/{track['identifier']}/hqdefault.jpg")
        embed.set_footer(icon_url=requester.avatar_url,
                         text=f"{requester.name} | {'⏸️' if player['paused'] else '▶️'} {' | ' + emoji if emoji else ''} | {to_time(player['position'] / 1000)} / {to_time(track['length'] / 1000)}")

        return embed

    def chop(self, array: list, page: int, amount: int = 10) -> (list, int, int):
        """
        Split array to pages
        """
        x = amount * page  # math.ceil(len(array)/len(array)*amount)*start
        pages = len(array) / amount

        return array[x:x + amount], page + 1, int(ceil(pages))

    @commands.command(aliases=['p', 'pl'])
    async def play(self, ctx, *, query):
        """
        Plays a tack from yt or spotify
        """

        await self._play(ctx, query)

    @commands.command()
    async def playr(self, ctx, query):
        """
        Play songs without using internal cache can result in slow track resolve, but loads up to date data
        """
        await self._play(ctx, query, cache=False)

    async def _play(self, ctx, query, cache=True):
        if not ctx.author.voice:
            return await ctx.send("You need to be connected to voice :)")

        data = await self.extractor(query)
        data = await self.link.play(ctx.guild.id, data, ctx.author.id, ctx.channel.id, cache)

    @commands.command(aliases=['np', 'currently'])
    async def nowplaying(self, ctx):
        """
        Displays currently playing track
        """
        data = await self.link.rest_track_data(ctx.guild.id)
        await ctx.send(embed=self.play_embed(data))

    @commands.command()
    async def queue(self, ctx, page: int = 1):
        """
        Displays current queue
        """
        data = await self.link.rest_player_data(ctx.guild.id)
        if not data or not data['queue']:
            return await ctx.send("Nothing in queue")

        n = 10
        items = self.chop(data['queue'], page - 1, n)
        qlen = len(data['queue'])

        if data['loop'] == 0:
            emoji = ""
        elif data['loop'] == 1:
            emoji = "🔂"
        else:
            emoji = "🔁"

        embed = NyaEmbed(title="Queue", description=codeblock(f"{qlen} songs in queue"))
        embed.set_footer(icon_url=ctx.author.avatar_url,
                         text=f"{ctx.author.name} | {'⏸️' if data['paused'] else '▶️'} {' | ' + emoji if emoji else ''} | page {items[1]} out of {items[2]}")

        for i, track in enumerate(items[0]):
            name = max_len(
                f"{i + ((items[1] - 1) * n) + 1}.{' (Now playing)' if track == data['queue'][0] else ''} {track['track']['title']}",
                50)
            value = f"🔗[link]({track['track']['uri']})"

            embed.add_field(
                name=name,
                value=value,
                inline=False)

        await ctx.send(embed=embed)

    @commands.command(aliases=['s'])
    async def skip(self, ctx):
        """
        Skips current track
        """
        await self.link.skip(ctx.guild.id)

    @commands.command()
    async def loop(self, ctx):
        """
        Loops whole queue
        """
        await self.link.loop(ctx.guild.id, 2)

    @commands.command()
    async def noloop(self, ctx):
        """
        Removes any loop
        """
        await self.link.loop(ctx.guild.id, 0)

    @commands.command()
    async def loopone(self, ctx):
        """
        loops currently playing track
        """
        await self.link.loop(ctx.guild.id, 1)

    @commands.command()
    async def resume(self, ctx):
        """
        Resumes
        """
        await self.link.pause(ctx.guild.id, False)

    @commands.command()
    async def pause(self, ctx):
        """
        Pauses
        """
        await self.link.pause(ctx.guild.id, True)

    @commands.command(aliases=['dc'])
    async def disconnect(self, ctx):
        """
        Disconnects from voice channel
        """
        await self.link.disconnect(ctx)
        # await self.link.stop(ctx.guild.id)
        # xd its implemented server side

    @commands.command(aliases=['clear'])
    async def stop(self, ctx):
        """
        Stops playing and clears queue
        """
        await self.link.stop(ctx.guild.id)

    @commands.command(name='connect', aliases=['join', 'c'])
    async def connect_(self, ctx, *, channel: discord.VoiceChannel = None):
        if self.link._voice_state.get(ctx.guild.id, False):
            if ctx.author.voice.channel.id == self.link._voice_state[ctx.guild.id]:
                return

        if not ctx.author.voice.channel:
            return

        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise commands.CommandError

        await ctx.send(f'Connecting to **`{channel.name}`**')
        await self.link.connect(ctx, channel.id)

    @commands.command()
    async def seek(self, ctx, time: time_converter):
        """
        Seeks to specified position in a track
        """
        await self.link.seek(ctx.guild.id, int(time * 1000))

    @commands.command()
    async def shuffle(self, ctx):
        """
        Shuffles songs in queue
        """
        await self.link.shuffle(ctx.guild.id)

    @commands.command()
    async def remove(self, ctx, index: int):
        """
        Romves track at specified index from queue
        """
        index -= 1
        index = max(index, 0)
        await self.link.remove(ctx.guild.id, index)

        # if we r np song skip
        if index == 0:
            await self.link.stop(ctx.guild.id)

        await self.link.remove(ctx.guild.id, index)

    @commands.command()
    async def skipto(self, ctx, index: int):
        """Skip to specified index and start playing from that point"""
        index -= 1
        index = max(index, 0)
        await self.link.skip_to(ctx.guild.id, index)

    @playr.before_invoke
    @play.before_invoke
    async def _connect(self, ctx):
        try:
            await ctx.invoke(self.connect_)
        except:
            pass

    @commands.is_owner()
    @commands.command(hidden=True)
    async def move(self, ctx, guild_id, *, node: str = None):
        await self.link.move_player(guild_id, node)

    @commands.is_owner()
    @commands.command(hidden=True)
    async def linkus(self, ctx):
        res = await self.link.rest_status()
        embed = NyaEmbed(title='STATUS', description=codeblock(str(res), 'json'))
        await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.command(hidden=True)
    async def pps(self, ctx):
        res = await self.link.rest_players()
        await ctx.send(str(res))


def setup(bot):
    bot.add_cog(Music(bot))
