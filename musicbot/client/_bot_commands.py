from datetime import datetime

import discord
from discord.ext import commands
from discord.utils import get

from ._structures import Song, Session


def _init_commands(bot):
    if bot.prefix_method:
        @bot.command(name="change_prefix", aliases=["prefix"],
                     pass_context=True)
        async def change_prefix(ctx, new_prefix):
            bot.prefix_method(bot, ctx.message, new_prefix)

    #
    # MUSIC CONTROL COMMANDS
    #
    @bot.command(name="play", aliases=["p"], pass_context=True)
    async def play(ctx, *args):
        user = ctx.message.author
        try:
            voice_channel = user.voice.channel
        except AttributeError:
            # This is most likely due to the user not being
            # connected to a voice channel.
            await self._send_msg(ctx, "NotInVoice")
            return
        vc = get(bot.voice_clients, guild=ctx.guild)
        if not vc or not vc.is_connected:
            vc = await voice_channel.connect()
            if vc.channel != voice_channel:
                await bot._send_msg(ctx, "BotBusy")
                return
            setattr(vc, "session", Session(vc))
        query = " ".join(args)
        await bot._send_msg(ctx, "Searching", query)
        song = Song.from_youtube(query)
        action = vc.session.add_song(song)
        if action == "played":
            await bot._send_msg(ctx, "Playing", vc)
        elif action == "queued":
            await bot._send_msg(ctx, "Queueing", vc)

    @bot.command(name="skip", aliases=["s"], pass_context=True)
    async def skip(ctx):
        vc = get(bot.voice_clients, guild=ctx.guild)
        vc.session.skip()
        await bot._send_msg(ctx, "Skipping", vc)

    @bot.command(name="pause", pass_context=True)
    async def pause(ctx):
        vc = get(bot.voice_clients, guild=ctx.guild)
        vc.session.pause()

    @bot.command(name="resume", aliases=["r"], pass_context=True)
    async def resume(ctx):
        vc = get(bot.voice_clients, guild=ctx.guild)
        vc.session.resume()

    @bot.command(name="forward", aliases=["fw"], pass_context=True)
    async def forward(ctx, timedelta):
        # PSEUDOCODE
        # vc = get(...)
        # vc.session.seek(timedelta)
        return

    #
    # INFORMATION COMMANDS
    #
    @bot.command(name="queue", pass_context=True)
    async def queue(ctx):
        vc = get(bot.voice_clients, guild=ctx.guild)
        await bot._send_msg(ctx, "ViewQueue", vc)
