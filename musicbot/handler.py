from .iniparser import IniParser
import os
import sys
from .musicbot import MusicBot
import logging
import json


class BotHandler:

    def __init__(self, prefix_json="./prefixes.json",
                 perms_json="./perms.json"):
        """
        :param prefix_json: Path to json containing bot- and server
            specific command prefixes. For use with the
            :class:`BotHandler`:s prefix methods.
        :type prefix_json: str
        :param perms_json: Path to json containing bot- and server
            specific user permissions regarding bots.
        """
        self.prefix_path = prefix_json
        self.perms_path = perms_json
        self.bots = {}
        self.prefixes = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def add_bot(self, bot, nickname, token, default_prefix="!"):
        """Adds bot to handler.

        :param bot: A :class:`Bot` or derived object to add to handler.
        :type bot: discord.ext.commands.Bot
        :param nickname: Nickname to give bot.
        :type nickname: str
        :param token: Token to use for this bot.
        :type token: str
        """
        self.bots[nickname] = {
            "client": bot,
            "token": token,
            "prefix": default_prefix
        }

    def update_prefixes(self):
        try:
            with open(self.prefix_path, "r") as f:
                self.prefixes = json.load(f)
        except json.decoder.JSONDecodeError as e:
            self.logger.error(("Updating prefixes from json failed "
                               "due to a decode error. Verify the "
                               f"integrity of {self.prefix_path}."))

    def get_prefix(self, bot, msg):
        for nick in self.bots:
            if self.bots[nick]["client"] == bot:
                name = nick
        guild = str(msg.guild.id)
        try:
            prefix = self.prefixes[name][guild]["prefix"]
        except KeyError:
            for bot in self.bots:
                self.verify_data(self.bots[bot]["client"])
            # Something went wrong retrieving prefix from dict
            # -> try loading from json
            self.logger.warning((f"{name}: Something went wrong retrieving "
                                 f"prefix for guild {guild} - attempting "
                                 "to update prefixes from json."))
            self.update_prefixes()
            try:
                prefix = self.prefixes[name][guild]["prefix"]
            except KeyError:
                self.logger.warning((f"{name}: Failed to retrieve server "
                                     "prefix from json - using default "
                                     "prefix."))
                prefix = self.bots[name]["prefix"]
        return prefix

    def change_prefix(self, bot, msg, new_prefix):
        for nick in self.bots:
            if self.bots[nick]["client"] == bot:
                name = nick
        guild_id = str(msg.guild.id)
        self.prefixes[name][guild_id]["prefix"] = new_prefix
        with open(self.prefix_path, "w") as f:
            json.dump(self.prefixes, f, indent=2)
        self.update_prefixes()

    def on_join(self, bot, guild):
        self.set_default_prefix(bot, guild)
        self.logger.info(f"{name} joined server {guild_id}.")

    def set_default_prefix(self, bot, guild):
        guild_id = str(guild.id)
        for nick in self.bots:
            if self.bots[nick]["client"] == bot:
                name = nick
        # Get default prefix for this bot
        def_prefix = self.bots[name]["prefix"]
        bot_data = self.prefixes[name]
        bot_data[guild_id] = {
            "prefix": def_prefix
        }
        with open(self.prefix_path, "w") as f:
            json.dump(self.prefixes, f, indent=2)

    def verify_data(self, bot, update=True):
        for nick in self.bots:
            if self.bots[nick]["client"] == bot:
                name = nick
        if self.prefix_path is not None:
            with open(self.prefix_path, "r") as f:
                prefix_data = json.load(f)
        error_count = 0
        # Check that prefix data exists for this bot
        if name not in prefix_data.keys():
            self.logger.warning((f"No entry for {name} in {self.prefix_path}, "
                                 f"creating new entry with default prefix for "
                                 "all servers."))
            prefix_data[name] = {}
            for guild_id in [str(guild.id) for guild in bot.guilds]:
                prefix_data[name][guild_id] = {
                    "prefix": self.bots[name]["prefix"]
                }
            with open(self.prefix_path, "w") as f:
                json.dump(prefix_data, f, indent=2)
            error_count += 1
        else:
            # Check that prefix data exists for all guilds
            for guild in bot.guilds:
                guild_id = str(guild.id)
                if guild_id not in prefix_data[name].keys():
                    self.logger.warning((f"No entry for server {guild_id} in "
                                         f"{self.prefix_path}, creating new "
                                         "entry with default prefix."))
                    prefix_data[name][guild_id] = {
                        "prefix": self.bots[name]["prefix"]
                    }
                    with open(self.prefix_path, "w") as f:
                        json.dump(prefix_data, f, indent=2)
                    error_count += 1
        self.logger.info(f"Verifying finished with {error_count} errors.")
        if update:
            self.update_prefixes()

    def run_all(self):
        if os.path.isfile(self.prefix_path):
            try:
                self.update_prefixes()  # Load prefixes from json

            except json.decoder.JSONDecodeError as e:
                if os.stat(self.prefix_path).st_size == 0:  # Empty json
                    with open(self.prefix_path, "w") as f:
                        json.dump({}, f, indent=2)
                else:
                    raise e
        else:   # Prompt user to create prefix json
            ans = input((f"{self.prefix_path} doesn't exist. Do you want to "
                         "create this file? [Y/n] "))
            if ans.lower() in ["y", ""]:
                # Create necessary directories
                os.makedirs(os.path.dirname(self.prefix_path), exist_ok=True)
                with open(self.prefix_path, "w") as f:
                    json.dump({}, f, indent=2)
            else:
                print("Aborting...")
                sys.exit()
        # TODO FIX RUNNING MULTIPLE BOTS
        for bot in self.bots.values():
            bot["client"].run(bot["token"])


def import_settings(settings_path):
    """Imports settings for bot from selected ini-file if it exists,
    will otherwise prompt the user to generate the file with default
    keys and values.

    :param settings_path: File path to ini-file.
    :type settings_path: str
    :return: A :class:`PythonIni` object containing all settings from
        ini-file.
    :rtype: utils.PythonIni
    """
    if not os.path.isfile(settings_path):
        ans = input((f"{settings_path} not found."
                     " Do you want to generate this file"
                     " with default settings? [Y/n] "))
        if ans in ["Y", ""]:
            IniParser.to_ini(settings_path, DEFAULT_SETTINGS, makedirs=True)
            return DEFAULT_SETTINGS
        else:
            print("Aborting...")
            sys.exit()
    return IniParser.to_dict(settings_path, True)
