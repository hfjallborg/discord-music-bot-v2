import os
import logging
import json
import warnings
import random

import discord
from discord.ext import commands
# from discord.utils import get

from ._bot_commands import _init_commands    # Bot commands
from ..audio.youtube import find_video, get_audio


class MusicBot(commands.Bot):
    """[CLASS DESCRIPTION]

    :param cmd_prefix: Dictates what character(s) Discord messages
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
    def __init__(self, cmd_prefix="!", change_prefix=None,
                 on_server_join=None, on_server_remove=None):
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
        _init_commands(self)    # Load commands from _bot_commands

    async def on_ready(self):
        self.logger.info("Bot is ready")

    async def _send_msg(self, ctx, event, arg=None):
        # Send event/command specific message according to the
        # 'messages' dictionary.
        msg = self.messages[event]
        if callable(msg):
            msg = msg(arg)
        if msg != "":
            await ctx.send(msg)
    
    def _default_on_play_msg(self, vc):
        # Default message when playing song
        msg = (f"\N{MUSICAL NOTE} **Now playing:** `{vc.session.now_playing}`\n")
        return msg

    def _default_search_msg(self, query):
        # Default message when searching for track
        msg = (f"Searching for: `{query}`")
        return msg

    def _default_add_to_queue_msg(self, vc):
        # Default message when queueing song
        queued_song = vc.session.queue[len(vc.session.queue) - 1]
        msg = (f"Added `{queued_song}` to queue.")
        return msg

    def _default_view_queue_msg(self, vc):
        # Default message for the 'queue' command.
        msg = f""
        for i in range(len(vc.session.queue)):
            song = vc.session.queue[i]
            nr = i + 1
            msg += f"**{nr}.** `{song}`\n"
        return msg

    def _default_skip_msg(self, vc):
        # Default message when skipping song
        if len(vc.session.queue) > 0:
            new_song = vc.session.queue[0]
            msg = f"Skipping! :track_next: `{new_song}`"
        else:
            msg = "Skipping!"
        return msg

    def _init_events(self):
        if self.on_server_join is not None:
            @self.event
            async def on_guild_join(guild):
                self.on_server_join(self, guild)
        if self.on_server_remove is not None:
            @self.event
            async def on_guild_remove(guild):
                self.on_server_remove(self, guild)
