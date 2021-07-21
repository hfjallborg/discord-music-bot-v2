import random
from datetime import datetime

import discord
from discord.ext import commands
from discord.utils import get

from ..audio.youtube import find_video, get_audio


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


class Session:
    """This class represents a listening session for the
    :class:`musicbot.client.MusicBot`. It is bound to a
    :class:`discord.VoiceClient` and can as such handle voice playback.

    :param vc: The :class:`VoiceClient` to use for music playback. This
        is created when a :class:`Bot` joins a voice channel.
    :type vc: discord.VoiceClient
    :param queue: A list of :class:`Song`s, representing the starting
        playback queue, defaults to []
    :type queue: list, optional
    """
    def __init__(self, vc, queue=[]):
        self.vc = vc
        self.now_playing = None
        self.queue = queue
        self.started_playing = None
        self.shuffle = False

    def add_song(self, song):
        """Adds song to session. If queue is empty and no song is
        playing, it will be played directly.

        :param song: A :class:`Song` object to add to the session.
        :type song: Song
        :return: Either "queued" or "played".
        :rtype: str
        """
        if len(self.queue) == 0 and not self.is_playing:
            self._play(song)
            return "played"
        else:
            self.queue.append(song)
            return "queued"

    def skip(self):
        """Skips current track. If queue is empty - stops playback,
        else - plays next track in queue.
        """
        if self.is_playing:
            self.vc.stop()
        if len(self.queue) == 0:
            return
        if self.shuffle:
            random.shuffle(self.queue)
        song = self.queue.pop(0)
        self._play(song)

    def pause(self):
        """Pauses playback. Resumes if already paused."""
        if self.is_playing:
            self.vc.pause()
        else:
            self.vc.resume()
    
    def resume(self):
        """Resumes playback if paused"""
        if self.vc.is_paused():
            self.vc.resume()
        else:
            return

    def seek(self, timedelta):
        # PSEUDOCODE
        # timestamp = self.playtime + timedelta
        # ffmpeg_arg = f"-ss str(timestamp)""
        # self.vc.stop_playing()
        # self.vc.play(self.now_playing.audio, before_options=ffmpeg_arg)
        # self.playtime += timedelta
        return

    def _play_next(self, e=None):
        if len(self.queue) == 0:
            return
        elif self.is_playing:
            return
        if self.shuffle:
            random.shuffle(self.queue)
        song = self.queue.pop(0)
        if song != self.now_playing:
            self._play(song)

    def _play(self, song, timestamp=None):
        self.vc.play(discord.FFmpegPCMAudio(song.audio.url),
                     after=self._play_next)
        self.now_playing = song
        self.started_playing = datetime.now()

    @property
    def playtime(self):
        now = datetime.now()
        delta = self.started_playing - now
        return delta

    @property
    def is_playing(self):
        return self.vc.is_playing()

    @property
    def is_paused(self):
        return self.vc.is_paused()
