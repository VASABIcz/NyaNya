from ast import literal_eval

import discord

from bot.bot_class import Nya_Nya
from utils.constants import EMBED_COLOR, LOL_REGIONS
from utils.errors import *


def summoner_embed(name, icon, update, flex, solo, level, champs, mains):
    embed = discord.Embed(title=name, colour=EMBED_COLOR,
                          description=f"[u.gg](https://u.gg/lol/profile/eun1/{name}/overview) | [op.gg](https://eune.op.gg/summoner/userName={name}) | [leagueofgraphs.com](https://www.leagueofgraphs.com/en/summoner/eune/{name})")

    embed.set_thumbnail(url=f"https://ddragon.leagueoflegends.com/cdn/11.12.1/img/profileicon/{icon}.png")
    embed.set_footer(text=f"Last update: {update}")

    embed.add_field(name="Solo/Duo", value=flex, inline=True)
    embed.add_field(name="Flex", value=solo, inline=True)
    embed.add_field(name="Level", value=level, inline=False)
    embed.add_field(name="Mains", value=f"{champs} Champs played", inline=False)

    mains = literal_eval(mains)  # Ez clap

    for main in list(mains):
        embed.add_field(name=main['championId'],
                        value=f"mastery: {main['championLevel']}\npoints: {main['championPoints']}", inline=False)
    return embed


class Lol(commands.Cog):
    """Show info about summoner"""

    def __init__(self, bot: Nya_Nya):
        self.bot = bot
        self.emoji = "🤬"

    @commands.command()
    async def lolsummoner(self, ctx, summoner, regions=None):
        """Send embed about summoner"""
        if not regions:
            regions = LOL_REGIONS.keys()
        else:
            regions = [regions]

        for region in regions:
            async with self.bot.session.get(
                    f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner}?api_key={self.bot.cfg.LOL_API_KEY}") as response:
                if response.status == 403:
                    # await ctx.send("DEV IS KINDA CRINGE")
                    raise ExpiredApiKey("DEV IS KINDA CRINGE")
                response = await response.json()
            sid = response['id']

            query = "SELECT name, icon, update, flex, solo, level, champs, mains FROM lolapi where id = $1 and region = $2"
            data = await self.bot.pdb.fetch(query, sid, region)
            if data != []:
                data = data[0]
                await ctx.send(
                    embed=summoner_embed(data["name"], data["icon"], data["update"], data["flex"], data["solo"],
                                         data["level"], data["champs"], data["mains"]))
                continue

            async with self.bot.session.get(
                    f"https://{region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{sid}?api_key={self.bot.cfg.LOL_API_KEY}") as response1:
                response1 = await response1.json()

            async with self.bot.session.get(
                    f"https://{region}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-summoner/{sid}?api_key={self.bot.cfg.LOL_API_KEY}") as response2:
                response2 = await response2.json()

            async with self.bot.session.get(
                    f"https://ddragon.leagueoflegends.com/cdn/11.12.1/data/en_US/champion.json") as response3:
                response3 = await response3.json()

            # VALUES
            sid = sid
            name = response['name']
            update = response['revisionDate']
            level = response['summonerLevel']
            icon = response['profileIconId']
            try:
                solo = response1[0]['tier'] + " " + response[0]['rank']
            except:
                solo = "NONE"
            try:
                flex = response1[1]['tier'] + " " + response[1]['rank']
            except:
                flex = "NONE"
            champs = len(response2)
            mains = response2[:3]
            for main in mains:
                ide = main['championId']
                for xd in response3['data']:
                    valuess = response3['data'][xd]
                    if int(valuess['key']) == ide:
                        main['championId'] = xd

            connection = await self.bot.pdb.acquire()
            async with connection.transaction():
                query = "INSERT INTO lolapi VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)"
                query1 = "UPDATE lolapi SET name = $1, level = $2, icon = $3, solo = $4, flex = $5, champs = $6, mains = $7, update = $8, region = $10 WHERE id = $9"
                try:
                    await self.bot.pdb.execute(query, sid, name, level, icon, solo, flex, champs, str(mains), update,
                                               region)
                except:
                    await self.bot.pdb.execute(query1, name, level, icon, solo, flex, champs, str(mains), update, sid,
                                               region)
            await self.bot.pdb.release(connection)

            print("????????????")
            await ctx.send(embed=summoner_embed(name, icon, update, flex, solo, level, champs, mains))

    # GET puuid
    # https://<region>.api.riotgames.com/lol/summoner/v4/summoners/by-name/<summoner_name>
    # {
    #    "id": "GaGY-GUaUXrVKlp_PdP7K6lkJWifDjSMkdVhu7tPiRLWucI",
    #    "accountId": "R6WOIVPu1j8xIKmmkekKleMI41WqJECK-VGHZ7Nxy5bscEKqSw7YsbJe",
    #    "puuid": "aIKg3-KRQJa-wwRGaWVZeojMsn2TURrQ8kO3A-STwLaw1HRmkYufVorqkVzR5m88zJgb3CJIhbt_-g",
    #    "name": "xVASABIx",
    #    "profileIconId": 3797,
    #    "revisionDate": 1623873434000,
    #    "summonerLevel": 156
    # }

    # GET icon.png
    # https://ddragon.leagueoflegends.com/cdn/10.15.1/img/profileicon/<icon_id>.png

    # GET rank
    # https://<region>.api.riotgames.com/lol/league/v4/entries/by-summoner/<id>
    # [
    #    {
    #        "leagueId": "1d33c355-0d86-478d-ab40-62d44b460e44",
    #        "queueType": "RANKED_SOLO_5x5",
    #        "tier": "BRONZE",
    #        "rank": "I",
    #        "summonerId": "GaGY-GUaUXrVKlp_PdP7K6lkJWifDjSMkdVhu7tPiRLWucI",
    #        "summonerName": "xVASABIx",
    #        "leaguePoints": 100,
    #        "wins": 58,
    #        "losses": 63,
    #        "veteran": false,
    #        "inactive": false,
    #        "freshBlood": false,
    #        "hotStreak": false,
    #        "miniSeries": {
    #            "target": 3,
    #            "wins": 0,
    #            "losses": 1,
    #            "progress": "LNNNN"
    #        }
    #    },
    #    {
    #        "leagueId": "5b14c570-f7c1-43ed-8590-66b8e169bbdf",
    #        "queueType": "RANKED_FLEX_SR",
    #        "tier": "BRONZE",
    #        "rank": "I",
    #        "summonerId": "GaGY-GUaUXrVKlp_PdP7K6lkJWifDjSMkdVhu7tPiRLWucI",
    #        "summonerName": "xVASABIx",
    #        "leaguePoints": 46,
    #        "wins": 5,
    #        "losses": 13,
    #        "veteran": false,
    #        "inactive": false,
    #        "freshBlood": false,
    #        "hotStreak": false
    #    }
    # ]

    # GET mains
    # https://{region}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-summoner/{sid}

    # GET gamps
    # https://ddragon.leagueoflegends.com/cdn/11.12.1/data/en_US/champion.json

    # GET latest lol version
    # https://ddragon.leagueoflegends.com/api/versions.json

    # get: name, icon, level, rank


def setup(bot):
    bot.add_cog(Lol(bot))
