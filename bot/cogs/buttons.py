import asyncio
import datetime
import time

import discord
from discord.ext import commands
from discord_components import *

from bot.bot_class import Nya_Nya
from bot.context_class import NyaNyaContext
from utils.functions_classes import NyaEmbed


class Games(commands.Cog):
    def __init__(self, bot: Nya_Nya):
        self.bot = bot
        self.emoji = "🕹️"

    @commands.is_owner()
    @commands.command(disabled=True, hidden=True)
    async def test(self, ctx: NyaNyaContext):
        """IDK"""
        buttons = [[Button(style=ButtonStyle.blue, label="⏸️", id="PAUSED"),
                    Button(style=ButtonStyle.green, label="▶️", id="PLAYING"),
                    Button(style=ButtonStyle.red, label="⏹️", id="STOP")]]
        embed = NyaEmbed(title="PLAYER")
        await ctx.send(embed=embed, components=buttons)

    @commands.command(aliases=['ttt'])
    async def tic_tac_toe(self, ctx: NyaNyaContext, who: discord.Member):
        """Just a regular tic tac to with use of new feature."""
        cross_ascii = "❌"
        circle_ascii = "⭕"
        player = who
        players = {ctx.author: cross_ascii, who: circle_ascii}
        conditions = [
            [[0, 0], [0, 1], [0, 2]],
            [[1, 0], [1, 1], [1, 2]],
            [[2, 0], [2, 1], [2, 2]],
            [[0, 0], [1, 0], [2, 0]],
            [[0, 1], [1, 1], [2, 1]],
            [[0, 2], [1, 2], [2, 2]],
            [[0, 0], [1, 1], [2, 2]],
            [[0, 2], [1, 1], [2, 0]]
        ]
        buttons = [
            [
                Button(style=ButtonStyle.gray, label="⬛", id="tic0 0", ),
                Button(style=ButtonStyle.gray, label="⬛", id="tic0 1", ),
                Button(style=ButtonStyle.gray, label="⬛", id="tic0 2", )
            ],
            [
                Button(style=ButtonStyle.gray, label="⬛", id="tic1 0", ),
                Button(style=ButtonStyle.gray, label="⬛", id="tic1 1", ),
                Button(style=ButtonStyle.gray, label="⬛", id="tic1 2", )
            ],
            [
                Button(style=ButtonStyle.gray, label="⬛", id="tic2 0", ),
                Button(style=ButtonStyle.gray, label="⬛", id="tic2 1", ),
                Button(style=ButtonStyle.gray, label="⬛", id="tic2 2", )
            ]
        ]

        embed = NyaEmbed(title="TIC TAC TOE",
                         timestamp=datetime.datetime.utcfromtimestamp(time.time()),
                         description=f"```ini\n[{ctx.author.display_name}]``````css\n[{who.display_name}]```")

        message = await ctx.send(embed=embed, components=buttons)

        while True:
            try:
                interaction = await self.bot.wait_for("button_click", timeout=10,
                                                      check=lambda i: i.component.id.startswith(
                                                          "tic") and i.user == player)
                id0, id1 = [int(x) for x in interaction.component.id.strip("tic").split(" ")]
                buttons[id0][id1].label = players[player]
                buttons[id0][id1].disabled = True
                if players[player] == cross_ascii:
                    buttons[id0][id1].style = ButtonStyle.blue
                else:
                    buttons[id0][id1].style = ButtonStyle.red

                await interaction.respond(type=InteractionType.UpdateMessage, embed=embed, components=buttons)

                for condition in conditions:
                    if buttons[condition[0][0]][condition[0][1]].label == players[player] and buttons[condition[1][0]][
                        condition[1][1]].label == players[player] and buttons[condition[2][0]][condition[2][1]].label == \
                            players[player]:
                        buttons[condition[0][0]][condition[0][1]].style = ButtonStyle.green
                        buttons[condition[1][0]][condition[1][1]].style = ButtonStyle.green
                        buttons[condition[2][0]][condition[2][1]].style = ButtonStyle.green
                        for button_list in buttons:
                            for button in button_list:
                                button.disabled = True

                        await interaction.message.edit(components=buttons)
                        await ctx.send(f"{players[player]} `{player.display_name}` WON!")
                        return

                    else:
                        if len([button_list for button_list in buttons for button in button_list if
                                not button.label == "⬛"]) == 9:
                            await ctx.send(f"!!TIE!!")
                            return

                if player == who:
                    player = ctx.author
                else:
                    player = who

            except asyncio.TimeoutError:
                for button_list in buttons:
                    for button in button_list:
                        button.disabled = True
                embed = NyaEmbed(title="TIC TAC TOE\nTIMED OUT",
                                 timestamp=datetime.datetime.utcfromtimestamp(time.time()),
                                 description=f"```ini\n[{ctx.author.display_name}]``````css\n[{who.display_name}]```")
                await message.edit(components=buttons, embed=embed)
                return


def setup(bot):
    DiscordComponents(bot)
    bot.add_cog(Games(bot))
