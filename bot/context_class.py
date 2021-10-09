import io
from ast import literal_eval

import discord
from discord.ext import commands
from discord.ext.commands import CommandError

from utils.embeds import pretty_list
from utils.functions_classes import NyaNyaPages, Player, NyaEmbed


class NyaNyaContext(commands.Context):

    async def send(self, content=None, *, tts=False, embed=None, file=None,
                   files=None, delete_after=None, nonce=None,
                   allowed_mentions=None, reference=None,
                   mention_author=None, filter=True):

        if filter:
            if content:
                content = discord.utils.escape_mentions(content)
            if embed:
                embed = NyaEmbed.from_dict(literal_eval(discord.utils.escape_mentions(str(embed.to_dict()))))

        return await super().send(content=content, tts=tts, embed=embed, file=file,
                                  files=files, delete_after=delete_after, nonce=nonce,
                                  allowed_mentions=allowed_mentions, reference=reference,
                                  mention_author=mention_author)

    async def send_error(self, error):
        embed = NyaEmbed(title="ERROR", description=f"```ini\n[{error}]```")

        await self.send(embed=embed)

    async def send_exception(self, error):
        embed = NyaEmbed(title="EXCEPTION", description=f"```ini\n[{error}]```")

        await self.send(embed=embed)

    async def send_pages(self, data, *args, **kwargs):
        return NyaNyaPages(self, data, *args, **kwargs)

    async def ok(self):
        await self.message.add_reaction("👌")

    # @property
    # def voice_state(self):
    #     state = self.bot.voice_states.get(self.guild.id)
    #     if not state:
    #         state = VoiceState(self.bot, self)
    #         self.bot.voice_states[self.guild.id] = state
#
    #     return state

    async def add_reaction(self, emoji):
        await self.message.add_reaction(emoji)

    async def filter_commands(self, commands, *, sort=False, key=None):
        if sort and key is None:
            key = lambda c: c.name
        iterator = filter(lambda c: not c.hidden, commands)

        async def predicate(cmd):
            try:
                return await cmd.can_run(self)
            except CommandError:
                return False

        ret = []
        for cmd in iterator:
            valid = await predicate(cmd)
            if valid:
                ret.append(cmd)
        if sort:
            ret.sort(key=key)
        return ret

    async def safe_send(self, content, *, escape_mentions=True, **kwargs):
        if escape_mentions:
            content = discord.utils.escape_mentions(content)

        if len(content) > 2000:
            fp = io.BytesIO(content.encode())
            kwargs.pop('file', None)
            return await self.send(file=discord.File(fp, filename='message_too_long.txt'), **kwargs)
        else:
            return await self.send(content)

    async def send_list(self, list, *args, **kwargs):
        await self.send(embed=pretty_list(list, *args, **kwargs))

    @property
    def player(self) -> Player:
        if self.guild:
            return self.bot.wavelink.get_player(guild_id=self.guild.id, cls=Player, context=self)
