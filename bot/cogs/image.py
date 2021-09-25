from io import *

import discord
from PIL import Image, ImageDraw, ImageSequence, ImageFont
from discord.ext import commands

from bot.bot_class import Nya_Nya
from bot.context_class import NyaNyaContext


class Images(commands.Cog):
    """PIL image manipulation, some apis maybe later."""

    def __init__(self, bot: Nya_Nya):
        self.bot = bot
        self.emoji = "🖼️"

    @commands.command(name="bonk", brief="*BONK*")
    async def _bonk(self, ctx: NyaNyaContext, member: discord.Member, *, text=""):
        if not member:
            member = ctx.author

        bonk = Image.open("utils/images/bonk.png")
        icon = member.avatar_url_as(size=128)
        icon = BytesIO(await icon.read())
        icon = Image.open(icon)
        font_path = r"utils\images\font.ttf"
        font = ImageFont.truetype(font_path, 30)

        icon = icon.resize((100, 50))
        bonk.paste(icon, (140, 120))
        bonk.convert("RGBA")
        text_layer = Image.new(mode='RGBA', size=bonk.size, color=(255, 0, 0, 0))

        d = ImageDraw.Draw(text_layer)
        d.text((140, 120), text, font=font, anchor="ms", fill=(0, 0, 0))
        text_layer = text_layer.rotate(45, expand=0)

        bonk.paste(text_layer, (0, 0), mask=text_layer)
        # bonk.paste(ImageOps.colorize(text_layer, (0,0,0), (10, 10,10)), (42,60),  text_layer)

        with BytesIO() as image_binary:
            bonk.save(image_binary, 'PNG')
            image_binary.seek(0)
            await ctx.send(file=discord.File(fp=image_binary, filename="image.png"))

    # @commands.command(name="damejo", brief="UwU")
    # async def _damejo(self, ctx, *, text="E"):
    #    im = Image.open(r"C:\python_projects\bot_framework\bot\images\dameto.gif")
    #    font_path = r"C:\python_projects\bot_framework\bot\images\font.ttf"
    #    font = ImageFont.truetype(font_path, 50)
    #
    #    frames = []
    #    for frame in ImageSequence.Iterator(im):
    #        d = ImageDraw.Draw(frame)
    #        d.text((320, 60), text, font=font, anchor="ms")
    #        del d
    #
    #        b = BytesIO()
    #        frame.save(b, format="GIF")
    #        frame = Image.open(b)
    #
    #        frames.append(frame)
    #
    #
    #    print("DONE")
    #    with BytesIO() as image_binary:
    #        frames[0].save(image_binary, 'GIF', save_all=True, append_images=frames[1:])
    #        image_binary.seek(0)
    #        print("DONE 2")
    #        await ctx.send(file=discord.File(fp=image_binary, filename="image.gif"))

    @commands.command(name="pet", brief="be friend pet someone")
    async def _pet(self, ctx: NyaNyaContext, member: discord.Member = None):
        if member == None:
            member = ctx.author

        icon = member.avatar_url_as(size=128)
        icon = BytesIO(await icon.read())
        icon = Image.open(icon)

        pet = Image.open(r"utils\images\pet.gif")  # 526/526
        pet.convert("RGBA")
        x = ImageSequence.Iterator(pet)
        x = x[0]
        x.convert("RGBA")
        xd = x.paste(icon, x)
        xd.show()
        # icon = member.avatar_url_as(size=128)
        # icon = BytesIO(await icon.read())
        # icon = Image.open(icon)
        # icon = icon.resize((526, 526))

        # frames = []
        # for frame in ImageSequence.Iterator(pet):
        #    frame.save("frame.gif")
        #    frame.show()
        #    break
        # frame.show()
        #    icon.paste(frame, (0, 0), mask=frame)

    #
    #    b = BytesIO()
    #    frame.save(b, format="GIF")
    #    frame = Image.open(b)
    #    frames.append(frame)
    #
    #
    # with BytesIO() as image_binary:
    #    frames[0].save(image_binary, 'GIF', save_all=True, append_images=frames[1:])
    #    image_binary.seek(0)
    #    print("DONE 2")
    #    await ctx.send(file=discord.File(fp=image_binary, filename="image.gif"))

    @commands.command(name="curse", brief="Once it was bug now its feature (:")
    async def _curse(self, ctx: NyaNyaContext, member: discord.Member = None):
        if member == None:
            member = ctx.author
        pet = Image.open("utils/images/pet.gif")  # 526/526
        icon = member.avatar_url_as(size=128)
        icon = BytesIO(await icon.read())
        icon = Image.open(icon)
        icon = icon.resize((526, 526))
        pet.convert("RGB")
        icon.convert("RGB")
        frames = []
        for frame in ImageSequence.Iterator(pet):
            frame.paste(icon, (0, 0))
            b = BytesIO()
            frame.save(b, format="GIF")
            frame = Image.open(b)
            frames.append(frame)
        with BytesIO() as image_binary:
            frames[0].save(image_binary, 'GIF', save_all=True, append_images=frames[1:])
            image_binary.seek(0)
            print("DONE 2")
            await ctx.send("Trust me its a feature (:", file=discord.File(fp=image_binary, filename="image.gif"))


def setup(bot):
    bot.add_cog(Images(bot))
