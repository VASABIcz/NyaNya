import asyncio
import sys
from json import dumps

import aiohttp
from aiohttp import web

from nya_link import NyaLink
from player import Player

# TODO rest api done
# TODO add node for all cients bad idea
# TODO fix small lag after reconnect impossible
# TODO weighted track cache done
# it is posible that when nya link adn doesnt recive voice server update it wont play any audio until move to other chnnnel
# TODO add api that will ask our client for voice server update
# or just dont allow connecting while client isn't connected
# TODO fix server/state isnt handelded/better voice state
# TODO on player dc/stop stop track fetching or ignore it
# TODO playing spotify somehow skips itself done
# next.set issue
# TODO limit amount of tracks in queue when fetching can get rly slow

clients = {}


class Unbuffered:
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


if __name__ == '__main__':
    sys.stdout, sys.stderr, sys.stdin = Unbuffered(sys.stdout), Unbuffered(sys.stderr), Unbuffered(sys.stdin)
    routes = web.RouteTableDef()
    cache = {}


    @routes.get('/')
    async def handle_websocket(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        user_id = int(request.headers['user_id'])
        try:
            print("resuming client connection from:", user_id)
            c = clients[user_id]
            c.resume(ws)
        except Exception:
            print("creating client connection from:", user_id)
            clients[user_id] = NyaLink(ws, user_id, cache)

        await asyncio.Future()


    @routes.get('/player_data')
    async def return_player_data(request: aiohttp.web.Request):
        # TODO implement error messages
        try:
            d = request.query
            user_id = int(d['user'])
            guild_id = int(d['guild'])

            user: NyaLink = clients[user_id]

            player: Player = user.players[guild_id]
            return web.Response(text=dumps(player.json_data, indent=4))
        except Exception:
            return web.Response(text="{}")


    @routes.get('/track_data')
    async def return_player_truck(request: aiohttp.web.Request):
        try:
            d = request.query
            user_id = int(d['user'])
            guild_id = int(d['guild'])
            index = int(d['index'])

            user: NyaLink = clients[user_id]

            player: Player = user.players[guild_id]
            return web.Response(text=dumps(player.json_play_data(index), indent=4))
        except Exception:
            return web.Response(text="{}")


    @routes.get('/status')
    async def status(request: aiohttp.web.Request):
        d = {}
        for client in clients.values():
            user_id = str(client.user_id)
            d[user_id] = {}
            d[user_id]['connected'] = not client.closed
            d[user_id]['nodes'] = {}
            for node in client.nodes.values():
                identifier = str(node.identifier)
                d[user_id]['nodes'][identifier] = {}
                d[user_id]['nodes'][identifier]['penalty'] = node.penalty
                d[user_id]['nodes'][identifier]['players'] = {}
                for player in node.players.values():
                    guild_id = str(player.guild_id)
                    d[user_id]['nodes'][identifier]['players'][guild_id] = {}
                    d[user_id]['nodes'][identifier]['players'][guild_id]['queue'] = len(player.queue)
                    d[user_id]['nodes'][identifier]['players'][guild_id]['playing'] = player.playing
                    d[user_id]['nodes'][identifier]['players'][guild_id]['loop'] = player.queue.loop

        return web.Response(text=dumps(d, indent=4))

    @routes.get('/players')
    async def players(request: aiohttp.web.Request):
        d = request.query
        user_id = int(d['user'])

        client: NyaLink = clients[user_id]
        # {guild_id: playing}
        res = {}

        for p in client.players.values():
            res[p.guild_id] = p.channel_id

        return web.Response(text=dumps(res, indent=4))


    app = web.Application()
    app.router.add_routes(routes)

    web.run_app(app)
