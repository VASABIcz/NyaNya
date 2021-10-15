import datetime
import itertools
import time

from discord.ext import commands

from utils.functions_classes import NyaEmbed


class Nya_Nya_Help(commands.HelpCommand):
    """
    Custom help command for Nya Nya bot.
    """

    def __init__(self, **options):
        self.no_category = options.pop('no_category', 'No Category')
        self.no_info = options.pop("no_info", "No information provided.")
        ...  # too lazy to add more functionality

        super().__init__(**options)

    def default_help(self, cogs, update):
        default_prefix = self.context.bot.cfg.MAIN_PREFIX
        cogs.sort()
        embed = NyaEmbed(title=f"Default prefix is: **{default_prefix}**",
                         description=f"```diff\n- [] = optional argument\n- <> = required argument\n+ for more info use:\n+ {default_prefix}help [category]\n+ {default_prefix}help [command]```",
                         timestamp=datetime.datetime.utcfromtimestamp(time.time()))  # TODO add to cfg.

        embed.set_author(name="VASABI#3057", url="https://github.com/VASABIcz",
                         icon_url="https://cdn.discordapp.com/avatars/841271270015893535/ccab84cb5b9b3082e874d2c5d8961769.webp?size=1024")
        embed.set_image(
            url='https://cdn.discordapp.com/attachments/856264222949769277/873909151414251560/ezgif-7-a6b34b98c98f.gif')
        embed.set_footer(text=f"requested by {self.context.author}",
                         icon_url=f"{self.context.author.avatar_url}")

        embed.add_field(name="**📰updates📰**", value="\n".join(update), inline=False)
        embed.add_field(name='🚪Invite🚪', value=f'> [here]({self.context.bot.invite})\n\u200b', inline=True)
        embed.add_field(name='✅Vote✅', value=f'> [here]({self.context.bot.vote})\n\u200b', inline=True)
        embed.add_field(name='🙋Support🙋', value=f'> [here]({self.context.bot.support})\n\u200b', inline=True)

        for cog in cogs:
            embed.add_field(name=f"**{cog[0]}**", value=f"```ini\n[{cog[1]}] commands```", inline=True)

        for _ in range(3 - (len(cogs) % 3)):  # add invisible field o bottom for better look
            embed.add_field(name=f"\u200b", value=f"\u200b", inline=True)

        return embed

    def cog_help(self, cog, commands):
        commands.sort()
        default_prefix = self.context.bot.cfg.MAIN_PREFIX

        embed = NyaEmbed(title=cog.description)
        # description=f"```diff\n- [] = optional argument\n- <> = required argument\n+ for more info use:\n+ {default_prefix}help [category]\n+ {default_prefix}help [command]```")

        embed.set_author(name="VASABI#3057", url="https://github.com/VASABIcz",
                         icon_url="https://cdn.discordapp.com/avatars/841271270015893535/ccab84cb5b9b3082e874d2c5d8961769.webp?size=1024")

        embed.add_field(name=f"**{cog.qualified_name}**", value="\n".join(commands), inline=True)
        return embed

    def command_help(self, command):
        default_prefix = self.context.bot.cfg.MAIN_PREFIX
        help = command.help
        help = help if help else self.no_info

        embed = NyaEmbed(title=help if len(help) <= 256 else help[:253] + "...")
        # description=f"```diff\n- [] = optional argument\n- <> = required argument\n+ for more info use:\n+ {default_prefix}help [category]\n+ {default_prefix}help [command]```")

        embed.set_author(name="VASABI#3057", url="https://github.com/VASABIcz",
                         icon_url="https://cdn.discordapp.com/avatars/841271270015893535/ccab84cb5b9b3082e874d2c5d8961769.webp?size=1024")

        embed.add_field(name=f"**{default_prefix}{command.qualified_name} {command.signature}**",
                        value="**aliases:**" + "```" + "\n".join(
                            command.aliases) + "```" if command.aliases else "No other aliases", inline=True)  #
        return embed

    def command_not_found(self, command):
        raise commands.errors.CommandNotFound(f"Command {command} is not found")

    async def send_bot_help(self, mapping):
        def get_category(command):
            cog = command.cog
            default_emoji = self.context.bot.default_emoji
            if cog is None:
                return f"**{default_emoji}{self.no_category}{default_emoji}**"
            else:
                if hasattr(cog, "emoji"):
                    return f"**{cog.emoji}{cog.qualified_name}{cog.emoji}**"
                else:
                    return f"**{default_emoji}{cog.qualified_name}{default_emoji}**"

        if self.context.author.id not in self.context.bot.owner_ids:
            filtered = await self.filter_commands(self.context.bot.commands, sort=True, key=get_category)
        else:
            filtered = sorted(self.context.bot.commands, key=get_category)
        to_iterate = itertools.groupby(filtered, key=get_category)

        cogs = [(category, len(list(commands))) for category, commands in to_iterate]
        query = "SELECT date, content FROM updates order by id desc limit 3"
        rows = await self.context.bot.pdb.fetch(query)
        update = [f"✨<t:{int(row['date'].timestamp())}:R>✨```fix\n= {row['content']}```" for row in rows]
        await self.context.send(embed=self.default_help(cogs, update if update else ["Dev is kinda cringe"]))

    async def send_cog_help(self, cog):
        if self.context.author.id not in self.context.bot.owner_ids:
            filtered = await self.filter_commands(cog.get_commands(), sort=True)
        else:
            filtered = cog.get_commands()

        commands = [
            f"{self.context.bot.cfg.MAIN_PREFIX}{command.qualified_name} {command.signature} ```{command.short_doc if command.short_doc else self.no_info}```"
            for command in filtered]
        await self.context.send(embed=self.cog_help(cog, commands))

    async def send_command_help(self, command):
        if command.hidden and self.context.author.id not in self.context.bot.owner_ids:
            raise commands.CommandNotFound(f"Command {command.qualified_name} is not found")

        await self.context.send(embed=self.command_help(command))
