import os
import logging
import json
import warnings

import discord
from discord.ext import commands
from discord.utils import get

from .audio.youtube import find_video, get_audio


class MusicBot(commands.Bot):

    class Song:

        def __init__(self, audio, title, url=None):
            self.audio = audio
            self.title = title
            self.url = url

        @classmethod
        def from_youtube(cls, query):
            video = find_video(query)
            audio = get_audio(video["url"])
            title = video["title"]
            url = video["url"]
            return cls(audio, title, url)

        def __str__(self):
            return self.title

    def __init__(self, cmd_prefix="!",
                 change_prefix=None, on_server_join=None,
                 on_server_remove=None):
        """Initialises :class:`MusicBot` object.

        :param cmd_prefix: Dictates what character(s) Discord-messages
            must start with to invoke a command. Can be a string or
            a callable that takes the :class:`Bot` object and
            :class:`discord.Message` object as its first two
            parameters.
        :param change_prefix: Method that will be called upon a user
            invoking the 'change_prefix' command. Must take
            :class:`Bot` and :class:`Message` objects as its first and
            second parameters.
        :type change_prefix: callable
        :param on_server_join: Method that will be called when bot
            joins a new server/guild.
        :type on_server_join: callable, optional
        :param on_server_remove: Method that will be called when bot
            leaves a server/guild.
        :type on_server_remove: callable, optional
        """
        self.prefix = cmd_prefix

        # Verify that method parameters are callable
        if change_prefix is not None:
            if not callable(change_prefix):
                raise TypeError(("change_prefix must be callable, not "
                                 f"{change_prefix.__class__.__name__}"))
        self.prefix_method = change_prefix
        if on_server_join is not None:
            if not callable(on_server_join):
                raise TypeError(("on_server_join must be callable, not"
                                 f"{on_server_join.__class__.__name__}"))
        self.on_server_join = on_server_join
        if on_server_remove is not None:
            if not callable(on_server_remove):
                raise TypeError(("on_server_remove must be callable, not "
                                 f"{on_server_remove.__class__.__name__}"))
        self.on_server_remove = on_server_remove

        commands.Bot.__init__(self, command_prefix=cmd_prefix,
                              self_bot=False)
        self.logger = logging.getLogger(__name__)

        # Bot messages in discord client
        self.on_play_msg = self._default_on_play_msg
        self.messages = {
            "NotInVoice": "You are not connected to a voice channel.",
            "BotBusy": "Bot is busy in another channel.",
            "Searching": self._default_search_msg,
            "Playing": self._default_on_play_msg,
            "ViewQueue": self._default_view_queue_msg,
            "Queueing": self._default_add_to_queue_msg,
            "Skipping": self._default_skip_msg
        }
        self._init_events()
        self._init_commands()

    async def on_ready(self):
        self.logger.info("Bot is ready")

    def _default_on_play_msg(self, vc):
        # Default message when playing song
        # title = vc.now_playing.title
        msg = (f"\N{MUSICAL NOTE} **Now playing:** `{vc.now_playing}`")
        return msg

    async def _send_msg(self, ctx, event, arg=None):
        msg = self.messages[event]
        if callable(msg):
            msg = msg(arg)
        if msg != "":
            await ctx.send(msg)

    def _default_search_msg(self, query):
        # Default message when searching for track
        msg = (f"Searching for: `{query}`")
        return msg

    def _default_add_to_queue_msg(self, vc):
        # Default message when queueing song
        queued_song = vc.queue[len(vc.queue) - 1]
        msg = (f"Added `{queued_song}` to queue.")
        return msg

    def _default_view_queue_msg(self, vc):
        vc = get(self.voice_clients, guild=ctx.guild)
        msg = f""
        for i in range(len(vc.queue)):
            song = vc.queue[i]
            nr = i + 1
            msg += f"**{nr}.** `{song}`\n"
        return msg

    def _default_skip_msg(self, vc):
        # Default message when skipping song
        if len(vc.queue) > 0:
            new_song = vc.queue[0]
            msg = f"Skipping! :track_next: `{new_song}`"
        else:
            msg = "Skipping!"
        return msg

    def _play_next(self, e=None, vc=None):
        # Plays next song in queue
        if vc is None:
            return
        queue = vc.queue
        if len(vc.queue) == 0:
            return
        song = vc.queue.pop(0)
        audio = song.audio
        if vc.is_playing():
            vc.stop()
        vc.play(discord.FFmpegPCMAudio(audio.url),
                after=self._play_next)
        vc.now_playing = song

    def _init_events(self):
        if self.on_server_join is not None:
            @self.event
            async def on_guild_join(guild):
                self.on_server_join(self, guild)
        if self.on_server_remove is not None:
            @self.event
            async def on_guild_remove(guild):
                self.on_server_remove(self, guild)

    def _init_commands(self):
        # The change_prefix command will only be available if you defined
        # the change_prefix callable when initiating the bot
        if self.prefix_method:
            @self.command(name="change_prefix", aliases=["prefix"],
                          pass_context=True)
            async def change_prefix(ctx, new_prefix):
                self.prefix_method(self, ctx.message, new_prefix)

        @self.command(name="play", aliases=["p"], pass_context=True)
        async def play(ctx, *args):
            user = ctx.message.author
            try:
                voice_channel = user.voice.channel
            except AttributeError:
                # This is most likely due to the user not being
                # connected to a voice channel
                if self.messages["NotInVoice"] != "":
                    await ctx.send(self.messages["NotInVoice"])
                return
            vc = get(self.voice_clients, guild=ctx.guild)
            if not vc or not vc.is_connected:
                vc = await voice_channel.connect()
                setattr(vc, "queue", [])
                setattr(vc, "now_playing", None)
                if vc.channel != voice_channel:
                    await self._send_msg(ctx, "BotBusy")
                    return

            query = " ".join(args)
            setattr(vc, "_query", query)
            await self._send_msg(ctx, "Searching", query)
            song = self.Song.from_youtube(query)
            audio = song.audio
            if vc.is_playing():  # Song already playing
                vc.queue.append(song)
                await self._send_msg(ctx, "Queueing", vc)
                return
            vc.play(discord.FFmpegPCMAudio(audio.url,),
                    after=self._play_next(vc=vc))
            vc.now_playing = song
            await self._send_msg(ctx, "Playing", vc)

        @self.command(name="skip", aliases=["s"], pass_context=True)
        async def skip(ctx):
            user = ctx.message.author
            vc = get(self.voice_clients, guild=ctx.guild)
            if vc.is_playing():
                if len(vc.queue) == 0:
                    vc.stop()
                else:
                    await self._send_msg(ctx, "Skipping", vc)
                    self._play_next(vc=vc)

        @self.command(name="pause", pass_context=True)
        async def pause(ctx):
            vc = get(self.voice_clients, guild=ctx.guild)
            if vc.is_playing():
                vc.pause()
            else:
                vc.resume()

        @self.command(name="resume", aliases=["r"], pass_context=True)
        async def resume(ctx):
            vc = get(self.voice_clients, guild=ctx.guild)
            if vc.is_paused():
                vc.resume()
            else:
                return

        @self.command(name="queue", pass_context=True)
        async def queue(ctx):
            vc = get(self.voice_clients, guild=ctx.guild)
            await self._send_msg(ctx, "ViewQueue", vc)
