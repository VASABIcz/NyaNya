import asyncio
from json import loads, dumps

import aiohttp
from aiohttp import web

from node import Node
from player import Player


class NyaLink:
    def __init__(self, ws, user_id, cache):
        self.session = aiohttp.ClientSession()
        self.loop = asyncio.get_event_loop()
        self.ws: web.WebSocketResponse = ws
        self.user_id = user_id  # int(self.ws.headers['user_id'])
        self.cache: {} = cache

        self.closed = False

        self.nodes = {}

        self.listener = self.loop.create_task(self.listen())

    @property
    def players(self):
        return self._get_players()

    def _get_players(self) -> dict:
        players = []

        for node in self.nodes.values():
            players.extend(node.players.values())

        return {player.guild_id: player for player in players}

    def get_best_node(self):
        nodes = [n for n in self.nodes.values() if n.is_available]
        if not nodes:
            return None

        return sorted(nodes, key=lambda n: len(n.players))[0]

    async def send(self, **data):
        if not self.closed:
            data_str = dumps(data)
            if isinstance(data_str, bytes):
                data_str = data_str.decode('utf-8')
            await self.ws.send_str(data_str)

    async def request_voice_state(self, guild_id: int):
        await self.send(op='voice_state_request', guild=guild_id)

    def get_best_stats_node(self):
        nodes = [n for n in self.nodes.values() if n.is_available]
        if not nodes:
            return None

        return sorted(nodes, key=lambda n: n.penalty)[0]

    def get_node(self, identifier: str):
        return self.nodes.get(identifier, None)

    async def update_handler(self, data) -> None:
        if not data or 't' not in data:
            return

        # TODO implement move resume done
        # TODO implement dc teardown done

        if data['t'] == 'VOICE_SERVER_UPDATE':
            guild_id = int(data['d']['guild_id'])

            try:
                player = self.get_player(guild_id)
            except Exception:
                pass
            else:
                print("player vs", player.voice_state)
                await player.on_voice_server(data['d'])

        elif data['t'] == 'VOICE_STATE_UPDATE':
            if int(data['d']['user_id']) != int(self.user_id):
                return

            guild_id = int(data['d']['guild_id'])
            try:
                player = self.get_player(guild_id)
            except KeyError:
                pass
            else:
                print("player vs", player.voice_state)
                await player.on_voice_state(data['d'])

    def get_player(self, guild_id: int, **kwargs):
        players = self.players

        try:
            player = players[guild_id]
        except KeyError:
            pass
        else:
            return player

        node = self.get_best_node()

        player = Player(guild_id, node)
        print(f"node players: {node.players}")
        node.players[guild_id] = player

        return player

    async def add_node(self, data):
        print("adding node: ", data['identifier'])
        identifier = data['identifier']
        if identifier in self.nodes:
            return
        host = data['host']
        port = int(data['port'])
        user_id = self.user_id
        client = self
        session = self.session
        rest_uri = data['rest_uri']
        password = data['password']
        region = data.get('region')
        shard_id = data.get('shard_id', None)
        secure = data.get('secure', False)

        n = Node(host=host, port=port, user_id=user_id, client=client, session=session, rest_uri=rest_uri,
                 password=password, region=region, identifier=identifier, shard_id=shard_id, secure=secure)
        await n.connect()
        if n.is_available:
            self.nodes[identifier] = n
        else:
            await n.destroy()

    async def remove_node(self, **data):
        identifier = data['identifier']
        force = data.get("force", False)
        await self.nodes[identifier].destroy(force)

    async def process_data(self, msg):
        print(f"procesing: {msg.data}")
        data = loads(msg.data)
        # client
        if data['op'] == "fetch_track":
            ...
        # node
        elif data['op'] == "add_node":
            await self.add_node(data['data'])
        elif data['op'] == "remov_node":
            await self.remove_node(**data)
        # player
        elif data['op'] == "play":
            guild = int(data['guild'])
            requester = int(data['requester'])
            channel = int(data['channel'])
            cache = bool(data['cache'])
            d = list(data['data'])

            player = self.get_player(guild)

            await player.fetch_queue.put([cache, requester, d, channel])

        elif data['op'] == "skip":
            guild_id = int(data['guild_id'])

            await self.get_player(guild_id).stop()
        elif data['op'] == "skip_to":
            guild_id = int(data['guild_id'])
            index = int(data['index'])

            p = self.get_player(guild_id)
            p.queue.skip_to(index)

            p.ignore = True
            await p.stop()
        elif data['op'] == "stop":
            guild_id = int(data['guild_id'])

            p = self.get_player(guild_id)
            await p.clear()

        elif data['op'] == 'destroy':
            guild_id = int(data['guild_id'])

            p = self.get_player(guild_id)
            p.queue.clear()
            await p.teardown()

        elif data['op'] == "loop":
            guild_id = int(data['guild_id'])
            loop = int(data['loop'])

            if loop not in (0, 1, 2):
                return
            self.get_player(guild_id).queue.loop = loop
        elif data['op'] == "seek":
            guild_id = int(data['guild_id'])
            seek = int(data['time'])

            await self.get_player(guild_id).seek(seek)
        elif data['op'] == "revind":
            guild_id = int(data['guild_id'])

            p = self.get_player(guild_id)

            p.queue.revert()
            p.ignore = True
            await p.stop()
        elif data['op'] == "remove":
            guild_id = int(data['guild_id'])
            index = int(data['index'])
            try:
                await self.get_player(guild_id).queue.remove(index)
            except Exception:
                pass
        elif data['op'] == "pause":
            guild_id = int(data['guild_id'])
            pause = data['pause']

            await self.get_player(guild_id).set_pause(pause)
        elif data['op'] == "shuffle":
            guild_id = int(data['guild_id'])

            await self.get_player(guild_id).queue.shuffle()

        elif data['op'] == 'voice_update':
            d = data['data']
            await self.update_handler(d)

        # elif data['op'] == 'status':
        #     guild_id = int(data['guild_id'])
        #     p = self.get_player(guild_id)
        #     d = {}
        #     d['op'] = 'status'
        #     d['playing'] = p.is_playing
        #     d['current'] = True if p.current else False
        #     d['connected'] = p.is_connected
        #     d['paused'] = p.paused
        #     d['loop'] = p.queue.loop
        #     try:
        #         d['queue'] = len(p.queue)
        #     except Exception:
        #         d['queue'] = []
        #     d['node'] = {}
        #     d['node']['players'] = len(p.node.players)
        #     await self.ws.send_str(dumps(d))

        elif data['op'] == "move":
            guild_id = int(data['guild_id'])
            identifier = data.get('node', None)
            await self.get_player(guild_id).change_node(identifier)

    def close(self):
        self.closed = True
        self.listener.cancel()

    def resume(self, ws):
        self.ws = ws
        self.closed = False
        self.listener = asyncio.create_task(self.listen())

    async def listen(self):
        while not self.closed:
            msg = await self.ws.receive()
            if msg.type is aiohttp.WSMsgType.CLOSED:
                self.close()
            else:
                self.loop.create_task(self.process_data(msg))
