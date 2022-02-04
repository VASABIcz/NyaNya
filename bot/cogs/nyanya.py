import asyncio
from json import dumps, loads

import aiohttp
from discord.ext import commands

from bot.utils.functions_classes import NyaEmbed, to_time, time_converter


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
    def headers(self):
        return {"client": str(self.bot.user.id)}

    @property
    def is_connected(self) -> bool:
        return self.ws is not None and not self.ws.closed

    async def setup(self):
        nodes = self.nodes
        for node in self.bot.cfg.NODES:
            await self.send(**node)

        await asyncio.sleep(1)  # small chance that bot will stop playing hope this fixes it

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
                    await asyncio.sleep(2)
                    self._loop.create_task(self._connect())
                    self.listener().close()
            else:
                asyncio.create_task(self.process(loads(msg.data)))

    async def process(self, data):
        print('processing', data)

        if data['op'] == 'track_result':
            t = data['track']['info']
            embed = NyaEmbed(title=t['title'], description=f"[{t['title']}]({t['uri']})")
            print(t['sourceName'])
            if t['sourceName'] == "youtube":
                url = f"https://img.youtube.com/vi/{t['identifier']}/hqdefault.jpg"
            else:
                url = "https://http.cat/404"
            print(url)
            embed.set_image(url=url)

            await self.bot.get_channel(int(data['channel'])).send(embed=embed)

    async def send(self, **data):
        if self.is_connected:
            # data['user_id'] = self.bot.user.id
            data_str = dumps(data)
            if isinstance(data_str, bytes):
                data_str = data_str.decode('utf-8')
            await self.ws.send_str(data_str)

    async def play(self, guild, name, requester, channel, cache=True):
        await self.send(op='play', guild=guild, name=name, requester=requester, channel=channel, cache=cache)

    async def skip(self, guild_id):
        await self.send(op='skip', guild=guild_id)

    async def loop(self, guild_id, loop):
        await self.send(op='loop', guild=guild_id, loop=loop)

    async def stop(self, guild_id):
        await self.send(op='clear', guild=guild_id)

    async def shuffle(self, guild_id):
        await self.send(op='shuffle', guild=guild_id)

    async def pause(self, guild_id, pause: bool):
        await self.send(op='pause', guild=guild_id, pause=pause)

    async def remove(self, guild_id, index):
        await self.send(op='remove', guild=guild_id, index=index)

    async def seek(self, guild_id, time):
        await self.send(op='seek', guild=guild_id, time=time)

    async def add_node(self, data):
        await self.send(op='add_node', data=data)

    async def now_playing(self, guild, channel, requester):
        await self.send(op='now_playing', guild=guild, channel=channel, requester=requester)


    async def voice_update(self, data):
        # TODO ignore mute/def client and server side
        if not data or 't' not in data:
            return

        if data['t'] in ('VOICE_SERVER_UPDATE', 'VOICE_STATE_UPDATE'):
            print("voids",data)
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

                await self.send(op='voice_state_update', **data['d'])
            else:
                self.last_server_state[int(data['d']['guild_id'])] = data
                await self.send(op='voice_server_update', **data['d'])

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

    @commands.cooldown(3, 3, commands.BucketType.user)
    @commands.command(aliases=["p"])
    async def play(self, ctx, *, link):
        await self.link.connect(ctx, ctx.author.voice.channel.id)
        await self.link.play(guild=ctx.guild.id, name=link, requester=ctx.author.id, channel=ctx.channel.id)

    @commands.cooldown(3, 3, commands.BucketType.user)
    @commands.command(aliases=["dc"])
    async def disconnect(self, ctx):
        await self.link.disconnect(ctx)

    @commands.cooldown(3, 3, commands.BucketType.user)
    @commands.command(aliases=["clear", "clean"])
    async def stop(self, ctx):
        await self.link.stop(ctx.guild.id)

    @commands.cooldown(3, 3, commands.BucketType.user)
    @commands.command()
    async def shuffle(self, ctx):
        await self.link.shuffle(ctx.guild.id)

    @commands.cooldown(3, 3, commands.BucketType.user)
    @commands.command()
    async def pause(self, ctx):
        await self.link.pause(ctx.guild.id, True)

    @commands.cooldown(3, 3, commands.BucketType.user)
    @commands.command()
    async def resume(self, ctx):
        await self.link.pause(ctx.guild.id, False)

    @commands.cooldown(3, 3, commands.BucketType.user)
    @commands.command(aliases=["s"])
    async def skip(self, ctx):
        await self.link.skip(ctx.guild.id)

    @commands.cooldown(3, 3, commands.BucketType.user)
    @commands.command()
    async def loop(self, ctx):
        await self.link.loop(ctx.guild.id, 2)

    @commands.cooldown(3, 3, commands.BucketType.user)
    @commands.command()
    async def loopone(self, ctx):
        await self.link.loop(ctx.guild.id, 1)

    @commands.cooldown(3, 3, commands.BucketType.user)
    @commands.command()
    async def noloop(self, ctx):
        await self.link.loop(ctx.guild.id, 0)

    @commands.cooldown(3, 3, commands.BucketType.user)
    @commands.command()
    async def seek(self, ctx, time: time_converter):
        await self.link.seek(ctx.guild.id, int(time*1000))

    @commands.cooldown(3, 3, commands.BucketType.user)
    @commands.command(aliases=["r"])
    async def remove(self, ctx, index: int):
        await self.link.remove(ctx.guild.id, index)

    @commands.cooldown(3, 3, commands.BucketType.user)
    @commands.command(aliases=["np"])
    async def nowplaying(self, ctx):
        await self.link.now_playing(ctx.guild.id, ctx.channel.id, ctx.author.id)




def setup(bot):
    bot.add_cog(Music(bot))
