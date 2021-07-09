import discord
from discord.ext import commands
from discord.utils import get
import logging
import json
import os
import warnings


class MusicBot(commands.Bot):

    def __init__(self, cmd_prefix="!", perms_json=None,
                 change_prefix=None, on_server_join=None,
                 on_server_remove=None):
        """Initialises :class:`MusicBot` object.

        :param cmd_prefix: Dictates what character(s) Discord-messages
            must start with to invoke a command. Can be a string or
            a callable that takes the :class:`Bot` object and
            :class:`discord.Message` object as its first two
            parameters.
        :param perms_json: Path to json containing server permissions
            regarding commands. If 'None', all commands can be used
            by everyone.
        :type perms_json: str, optional
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
        self.perms = perms_json

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
        self._init_events()
        self._init_commands()

    async def on_ready(self):
        self.logger.info("Bot is ready")

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
        """Defines all bot commands"""
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
