import os
import logging
import json
import warnings

import discord
from discord.ext import commands
from discord.utils import get

from .audio.youtube import find_video, get_audio


class MusicBot(commands.Bot):

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
            "Queueing": self._default_queue_msg,
            "Skipping": self._default_skip_msg
        }
        self._init_events()
        self._init_commands()

    async def on_ready(self):
        self.logger.info("Bot is ready")

    def _default_on_play_msg(self, vc):
        # Default message when playing song
        title = vc.now_playing["title"]
        msg = (f"\N{MUSICAL NOTE} **Now playing:** `{title}`")
        return msg
    
    async def _send_msg(self, ctx, event, *args):
        msg = self.messages[event]
        if callable(msg):
            msg = msg(args)
        if msg != "":
            await ctx.send(msg)

    def _default_search_msg(self, query):
        # Default message when searching for track
        msg = (f"Searching for: `{query}`")
        return msg

    def _default_queue_msg(self, vc):
        # Default message when queueing song
        title = vc.queue[0]["title"]
        msg = (f"Added `{title}` to queue.")
        return msg
    
    def _default_skip_msg(self, vc):
        # Default message when skipping song
        if len(vc.queue) > 0:
            new_song = vc.queue[0]
            title = new_song["title"]
            msg = f"Skipping! :track_next: `{title}`"
        else:
            msg = "Skipping!"
        return msg

    def _play_next(self, vc):
        # Plays next song in queue
        queue = vc.queue
        if len(vc.queue) == 0:
            return
        song = vc.queue.pop()
        audio = song["audio"]
        if vc.is_playing():
            vc.stop()
        vc.play(discord.FFmpegPCMAudio(audio.url),
                after=lambda e: self._play_next(vc))
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
        @self.command(name="HelloWorld", pass_context=True)
        async def HelloWorld(ctx):
            await ctx.send("Hello World!")

        # The change_prefix command will only be available if you defined
        # the change_prefix callable when initiating the bot
        if self.prefix_method:
            @self.command(name="change_prefix", aliases=["prefix"],
                          pass_context=True)
            async def change_prefix(ctx, new_prefix):
                self.prefix_method(self, ctx.message, new_prefix)
        
        @self.command(name="play", pass_context=True)
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
                    if self.messages["BotBusy"] != "":
                        await ctx.send(self.messages["BotBusy"])
                    return

            query = " ".join(args)
            await ctx.send(self.messages["Searching"](query))
            video = find_video(query)
            audio = get_audio(video["url"])
            song = {
                "audio": audio,
                "title": video["title"],
                "url": video["url"]
            }
            if vc.is_playing():  # Song already playing
                vc.queue.append(song)
                await ctx.send(self.messages["Queueing"](vc))
                return
            vc.play(discord.FFmpegPCMAudio(audio.url,),
                    after=lambda e: self._play_next(vc))
            vc.now_playing = song
            await ctx.send(self.on_play_msg(vc))
                    
        @self.command(name="skip", pass_context=True)
        async def skip(ctx):
            user = ctx.message.author
            vc = get(self.voice_clients, guild=ctx.guild)
            if vc.is_playing():
                if len(vc.queue) == 0:
                    vc.stop()
                else:
                    await ctx.send(self.messages["Skipping"](vc))
                    self._play_next(vc)
