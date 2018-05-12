import os
import sys
import time
import shlex
import shutil
import random
import inspect
import logging
import asyncio
import pathlib
import traceback
import math
import re
import datetime
import random
import urllib
import errno
import psutil

import aiohttp
import discord
import colorlog

from io import BytesIO, StringIO
from functools import wraps
from textwrap import dedent
from datetime import timedelta
from collections import defaultdict

from discord.enums import ChannelType
from discord.ext.commands.bot import _get_variable

from . import exceptions
from . import downloader

from .playlist import Playlist
from .player import MusicPlayer
from .entry import StreamPlaylistEntry
from .opus_loader import load_opus_lib
from .config import Config, ConfigDefaults
from .permissions import Permissions, PermissionsDefaults
from .constructs import SkipState, Response, VoiceStateUpdate
from .utils import load_file, write_file, fixg, ftimedelta, _func_
from .spotify import Spotify
from .json import Json

from .constants import VERSION as BOTVERSION
from .constants import DISCORD_MSG_CHAR_LIMIT, AUDIO_CACHE_PATH


load_opus_lib()

log = logging.getLogger(__name__)

timezone_dict = {'ACDT': 'UTC+10:30', 'ACST': 'UTC+09:30', 'ACT': 'UTC-05', 'ADT': 'UTC-03', 'AEDT': 'UTC+11', 'AEST': 'UTC+10', 'AFT': 'UTC+04:30', 'AKDT': 'UTC-08', 'AKST': 'UTC-09', 'AMST': 'UTC-03', 'AMT': 'UTC-04', 'AMT': 'UTC+04', 'ART': 'UTC-03', 'AST': 'UTC+03', 'AST': 'UTC-04', 'AWST': 'UTC+08', 'AZOST': 'UTC±00', 'AZOT': 'UTC-01', 'AZT': 'UTC+04', 'BDT': 'UTC+08', 'BIOT': 'UTC+06', 'BIT': 'UTC-12', 'BOT': 'UTC-04', 'BRST': 'UTC-02', 'BRT': 'UTC-03', 'BST': 'UTC+06', 'BST': 'UTC+11', 'BST': 'UTC+01', 'BTT': 'UTC+06', 'CAT': 'UTC+02', 'CCT': 'UTC+06:30', 'CDT': 'UTC-05', 'CDT': 'UTC-04', 'CEST': 'UTC+02', 'CET': 'UTC+01', 'CHADT': 'UTC+13:45', 'CHAST': 'UTC+12:45', 'CHOT': 'UTC+08', 'CHOST': 'UTC+09', 'CHST': 'UTC+10', 'CHUT': 'UTC+10', 'CIST': 'UTC-08', 'CIT': 'UTC+08', 'CKT': 'UTC-10', 'CLST': 'UTC-03', 'CLT': 'UTC-04', 'COST': 'UTC-04', 'COT': 'UTC-05', 'CST': 'UTC-06', 'CST': 'UTC+08', 'ACST': 'UTC+09:30', 'ACDT': 'UTC+10:30', 'CST': 'UTC-05', 'CT': 'UTC+08', 'CVT': 'UTC-01', 'CWST': 'UTC+08:45', 'CXT': 'UTC+07', 'DAVT': 'UTC+07', 'DDUT': 'UTC+10', 'DFT': 'UTC+01', 'EASST': 'UTC-05', 'EAST': 'UTC-06', 'EAT': 'UTC+03', 'ECT': 'UTC-04', 'ECT': 'UTC-05', 'EDT': 'UTC-04', 'AEDT': 'UTC+11', 'EEST': 'UTC+03', 'EET': 'UTC+02', 'EGST': 'UTC±00', 'EGT': 'UTC-01', 'EIT': 'UTC+09', 'EST': 'UTC-05', 'AEST': 'UTC+10', 'FET': 'UTC+03', 'FJT': 'UTC+12', 'FKST': 'UTC-03', 'FKT': 'UTC-04', 'FNT': 'UTC-02', 'GALT': 'UTC-06', 'GAMT': 'UTC-09', 'GET': 'UTC+04', 'GFT': 'UTC-03', 'GILT': 'UTC+12', 'GIT': 'UTC-09', 'GMT': 'UTC+00', 'GST': 'UTC-02', 'GST': 'UTC+04', 'GYT': 'UTC-04', 'HADT': 'UTC-09', 'HAEC': 'UTC+02', 'HAST': 'UTC-10', 'HKT': 'UTC+08', 'HMT': 'UTC+05', 'HOVST': 'UTC+08', 'HOVT': 'UTC+07', 'ICT': 'UTC+07', 'IDT': 'UTC+03', 'IOT': 'UTC+03', 'IRDT': 'UTC+04:30', 'IRKT': 'UTC+08', 'IRST': 'UTC+03:30', 'IST': 'UTC+05:30', 'IST': 'UTC+01', 'IST': 'UTC+02', 'JST': 'UTC+09', 'KGT': 'UTC+06', 'KOST': 'UTC+11', 'KRAT': 'UTC+07', 'KST': 'UTC+09', 'LHST': 'UTC+10:30', 'LHST': 'UTC+11', 'LINT': 'UTC+14', 'MAGT': 'UTC+12', 'MART': 'UTC-09:30', 'MAWT': 'UTC+05', 'MDT': 'UTC-06', 'MET': 'UTC+01', 'MEST': 'UTC+02', 'MHT': 'UTC+12', 'MIST': 'UTC+11', 'MIT': 'UTC-09:30', 'MMT': 'UTC+06:30', 'MSK': 'UTC+03', 'MST': 'UTC+08', 'MST': 'UTC-07', 'MUT': 'UTC+04', 'MVT': 'UTC+05', 'MYT': 'UTC+08', 'NCT': 'UTC+11', 'NDT': 'UTC-02:30', 'NFT': 'UTC+11', 'NPT': 'UTC+05:45', 'NST': 'UTC-03:30', 'NT': 'UTC-03:30', 'NUT': 'UTC-11', 'NZDT': 'UTC+13', 'NZST': 'UTC+12', 'OMST': 'UTC+06', 'ORAT': 'UTC+05', 'PDT': 'UTC-07', 'PET': 'UTC-05', 'PETT': 'UTC+12', 'PGT': 'UTC+10', 'PHOT': 'UTC+13', 'PHT': 'UTC+08', 'PKT': 'UTC+05', 'PMDT': 'UTC-02', 'PMST': 'UTC-03', 'PONT': 'UTC+11', 'PST': 'UTC-08', 'PYST': 'UTC-03', 'PYT': 'UTC-04', 'RET': 'UTC+04', 'ROTT': 'UTC-03', 'SAKT': 'UTC+11', 'SAMT': 'UTC+04', 'SAST': 'UTC+02', 'SBT': 'UTC+11', 'SCT': 'UTC+04', 'SGT': 'UTC+08', 'SLST': 'UTC+05:30', 'SRET': 'UTC+11', 'SRT': 'UTC-03', 'SST': 'UTC-11', 'SST': 'UTC+08', 'SYOT': 'UTC+03', 'TAHT': 'UTC-10', 'THA': 'UTC+07', 'TFT': 'UTC+05', 'TJT': 'UTC+05', 'TKT': 'UTC+13', 'TLT': 'UTC+09', 'TMT': 'UTC+05', 'TRT': 'UTC+03', 'TOT': 'UTC+13', 'TVT': 'UTC+12', 'ULAST': 'UTC+09', 'ULAT': 'UTC+08', 'USZ1': 'UTC+02', 'UTC': 'UTC+00', 'UYST': 'UTC-02', 'UYT': 'UTC-03', 'UZT': 'UTC+05', 'VET': 'UTC-04', 'VLAT': 'UTC+10', 'VOLT': 'UTC+04', 'VOST': 'UTC+06', 'VUT': 'UTC+11', 'WAKT': 'UTC+12', 'WAST': 'UTC+02', 'WAT': 'UTC+01', 'WEST': 'UTC+01', 'WET': 'UTC±00', 'WIT': 'UTC+07', 'WST': 'UTC+08', 'YAKT': 'UTC+09', 'YEKT': 'UTC+05'}

def find_key(dic, val):
    try:
        #99% sure there is a less convoluted way to implement this
        key = [k for k, v in timezone_dict.items() if v == val][0]
        return True
    except:
        return False

class MusicBot(discord.Client):
    def __init__(self, config_file=None, perms_file=None):
        try:
            sys.stdout.write("\x1b]2;MusicBot {}\x07".format(BOTVERSION))
        except:
            pass
        
        print()

        if config_file is None:
            config_file = ConfigDefaults.options_file

        if perms_file is None:
            perms_file = PermissionsDefaults.perms_file

        self.players = {}
        self.exit_signal = None
        self.init_ok = False
        self.cached_app_info = None
        self.last_status = None
        self.uptime = time.time()       
        self.message_count = 0      
        self.autoassignrole = False     
        self.autorole = {"default": "default"}

        self.config = Config(config_file)
        self.permissions = Permissions(perms_file, grant_all=[self.config.owner_id])
        self.str = Json(self.config.i18n_file)

        self.blacklist = set(load_file(self.config.blacklist_file))
        self.autoplaylist = load_file(self.config.auto_playlist_file)

        self.aiolocks = defaultdict(asyncio.Lock)
        self.downloader = downloader.Downloader(download_folder='audio_cache')

        self._setup_logging()

        log.info('Starting MusicBot {}'.format(BOTVERSION))

        if not self.autoplaylist:
            log.warning("Autoplaylist is empty, disabling.")
            self.config.auto_playlist = False
        else:
            log.info("Loaded autoplaylist with {} entries".format(len(self.autoplaylist)))

        if self.blacklist:
            log.debug("Loaded blacklist with {} entries".format(len(self.blacklist)))

        # TODO: Do these properly
        ssd_defaults = {
            'last_np_msg': None,
            'auto_paused': False,
            'availability_paused': False
        }
        self.server_specific_data = defaultdict(ssd_defaults.copy)

        super().__init__()
        self.aiosession = aiohttp.ClientSession(loop=self.loop)
        self.http.user_agent += ' MusicBot/%s' % BOTVERSION

        self.spotify = None
        if self.config._spotify:
            self.spotify = Spotify(self.config.spotify_clientid, self.config.spotify_clientsecret, aiosession=self.aiosession, loop=self.loop)
            if not self.spotify.token:
                log.warning('Your Spotify credentials could not be validated. Please make sure your client ID and client secret '
                            'in the config file are correct. Disabling Spotify integration for this session.')
                self.config._spotify = False
            else:
                log.info('Authenticated with Spotify successfully using client ID and secret.')

    def __del__(self):
        # These functions return futures but it doesn't matter
        try:    self.http.session.close()
        except: pass

        try:    self.aiosession.close()
        except: pass

        super().__init__()
        self.aiosession = aiohttp.ClientSession(loop=self.loop)
        self.http.user_agent += ' MusicBot/%s' % BOTVERSION

    # TODO: Add some sort of `denied` argument for a message to send when someone else tries to use it
    def owner_only(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Only allow the owner to use these commands
            orig_msg = _get_variable('message')

            if not orig_msg or orig_msg.author.id == self.config.owner_id:
                # noinspection PyCallingNonCallable
                return await func(self, *args, **kwargs)
            else:
                raise exceptions.PermissionsError("Only the owner can use this command.", expire_in=30)

        return wrapper

    def dev_only(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            orig_msg = _get_variable('message')

            if orig_msg.author.id in self.config.dev_ids:
                # noinspection PyCallingNonCallable
                return await func(self, *args, **kwargs)
            else:
                raise exceptions.PermissionsError("Only dev users can use this command.", expire_in=30)

        wrapper.dev_cmd = True
        return wrapper

    def ensure_appinfo(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            await self._cache_app_info()
            # noinspection PyCallingNonCallable
            return await func(self, *args, **kwargs)

        return wrapper

    def _get_owner(self, *, server=None, voice=False):
            return discord.utils.find(
                lambda m: m.id == self.config.owner_id and (m.voice_channel if voice else True),
                server.members if server else self.get_all_members()
            )

    def _delete_old_audiocache(self, path=AUDIO_CACHE_PATH):
        try:
            shutil.rmtree(path)
            return True
        except:
            try:
                os.rename(path, path + '__')
            except:
                return False
            try:
                shutil.rmtree(path)
            except:
                os.rename(path + '__', path)
                return False

        return True

    def _setup_logging(self):
        if len(logging.getLogger(__package__).handlers) > 1:
            log.debug("Skipping logger setup, already set up")
            return

        shandler = logging.StreamHandler(stream=sys.stdout)
        shandler.setFormatter(colorlog.LevelFormatter(
            fmt = {
                'DEBUG': '{log_color}[{levelname}:{module}] {message}',
                'INFO': '{log_color}{message}',
                'WARNING': '{log_color}{levelname}: {message}',
                'ERROR': '{log_color}[{levelname}:{module}] {message}',
                'CRITICAL': '{log_color}[{levelname}:{module}] {message}',

                'EVERYTHING': '{log_color}[{levelname}:{module}] {message}',
                'NOISY': '{log_color}[{levelname}:{module}] {message}',
                'VOICEDEBUG': '{log_color}[{levelname}:{module}][{relativeCreated:.9f}] {message}',
                'FFMPEG': '{log_color}[{levelname}:{module}][{relativeCreated:.9f}] {message}'
            },
            log_colors = {
                'DEBUG':    'cyan',
                'INFO':     'white',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'bold_red',

                'EVERYTHING': 'white',
                'NOISY':      'white',
                'FFMPEG':     'bold_purple',
                'VOICEDEBUG': 'purple',
        },
            style = '{',
            datefmt = ''
        ))
        shandler.setLevel(self.config.debug_level)
        logging.getLogger(__package__).addHandler(shandler)

        log.debug("Set logging level to {}".format(self.config.debug_level_str))

        if self.config.debug_mode:
            dlogger = logging.getLogger('discord')
            dlogger.setLevel(logging.DEBUG)
            dhandler = logging.FileHandler(filename='logs/discord.log', encoding='utf-8', mode='w')
            dhandler.setFormatter(logging.Formatter('{asctime}:{levelname}:{name}: {message}', style='{'))
            dlogger.addHandler(dhandler)

    @staticmethod
    def _check_if_empty(vchannel: discord.Channel, *, excluding_me=True, excluding_deaf=False):
        def check(member):
            if excluding_me and member == vchannel.server.me:
                return False

            if excluding_deaf and any([member.deaf, member.self_deaf]):
                return False

            return True

        return not sum(1 for m in vchannel.voice_members if check(m))


    async def _join_startup_channels(self, channels, *, autosummon=True):
        joined_servers = set()
        channel_map = {c.server: c for c in channels}

        def _autopause(player):
            if self._check_if_empty(player.voice_client.channel):
                log.info("Initial autopause in empty channel")

                player.pause()
                self.server_specific_data[player.voice_client.channel.server]['auto_paused'] = True

        for server in self.servers:
            if server.unavailable or server in channel_map:
                continue

            if server.me.voice_channel:
                log.info("Found resumable voice channel {0.server.name}/{0.name}".format(server.me.voice_channel))
                channel_map[server] = server.me.voice_channel

            if autosummon:
                owner = self._get_owner(server=server, voice=True)
                if owner:
                    log.info("Found owner in \"{}\"".format(owner.voice_channel.name))
                    channel_map[server] = owner.voice_channel

        for server, channel in channel_map.items():
            if server in joined_servers:
                log.info("Already joined a channel in \"{}\", skipping".format(server.name))
                continue

            if channel and channel.type == discord.ChannelType.voice:
                log.info("Attempting to join {0.server.name}/{0.name}".format(channel))

                chperms = channel.permissions_for(server.me)

                if not chperms.connect:
                    log.info("Cannot join channel \"{}\", no permission.".format(channel.name))
                    continue

                elif not chperms.speak:
                    log.info("Will not join channel \"{}\", no permission to speak.".format(channel.name))
                    continue

                try:
                    player = await self.get_player(channel, create=True, deserialize=self.config.persistent_queue)
                    joined_servers.add(server)

                    log.info("Joined {0.server.name}/{0.name}".format(channel))

                    if player.is_stopped:
                        player.play()

                    if self.config.auto_playlist:
                        if self.config.auto_pause:
                            player.once('play', lambda player, **_: _autopause(player))
                        if not player.playlist.entries:
                            await self.on_player_finished_playing(player)
                
                except Exception:
                    log.debug("Error joining {0.server.name}/{0.name}".format(channel), exc_info=True)
                    log.error("Failed to join {0.server.name}/{0.name}".format(channel))

            elif channel:
                log.warning("Not joining {0.server.name}/{0.name}, that's a text channel.".format(channel))

            else:
                log.warning("Invalid channel thing: {}".format(channel))

    async def _wait_delete_msg(self, message, after):
        await asyncio.sleep(after)
        await self.safe_delete_message(message, quiet=True)

    # TODO: Check to see if I can just move this to on_message after the response check
    async def _manual_delete_check(self, message, *, quiet=False):
        if self.config.delete_invoking:
            await self.safe_delete_message(message, quiet=quiet)

    async def _check_ignore_non_voice(self, msg):
        vc = msg.server.me.voice_channel

        # If we've connected to a voice chat and we're in the same voice channel
        if not vc or vc == msg.author.voice_channel:
            return True
        else:
            raise exceptions.PermissionsError(
                "you cannot use this command when not in the voice channel (%s)" % vc.name, expire_in=30)

    async def _cache_app_info(self, *, update=False):
        if not self.cached_app_info and not update and self.user.bot:
            log.debug("Caching app info")
            self.cached_app_info = await self.application_info()

        return self.cached_app_info


    async def remove_from_autoplaylist(self, song_url:str, *, ex:Exception=None, delete_from_ap=False):
        if song_url not in self.autoplaylist:
            log.debug("URL \"{}\" not in autoplaylist, ignoring".format(song_url))
            return

        async with self.aiolocks[_func_()]:
            self.autoplaylist.remove(song_url)
            log.info("Removing unplayable song from autoplaylist: %s" % song_url)

            with open(self.config.auto_playlist_removed_file, 'a', encoding='utf8') as f:
                f.write(
                    '# Entry removed {ctime}\n'
                    '# Reason: {ex}\n'
                    '{url}\n\n{sep}\n\n'.format(
                        ctime=time.ctime(),
                        ex=str(ex).replace('\n', '\n#' + ' ' * 10), # 10 spaces to line up with # Reason:
                        url=song_url,
                        sep='#' * 32
                ))

            if delete_from_ap:
                log.info("Updating autoplaylist")
                write_file(self.config.auto_playlist_file, self.autoplaylist)

    @ensure_appinfo
    async def generate_invite_link(self, *, permissions=discord.Permissions(70380544), server=None):
        return discord.utils.oauth_url(self.cached_app_info.id, permissions=permissions, server=server)


    async def join_voice_channel(self, channel):
        if isinstance(channel, discord.Object):
            channel = self.get_channel(channel.id)

        if getattr(channel, 'type', ChannelType.text) != ChannelType.voice:
            raise discord.InvalidArgument('Channel passed must be a voice channel')

        server = channel.server

        if self.is_voice_connected(server):
            raise discord.ClientException('Already connected to a voice channel in this server')

        def session_id_found(data):
            user_id = data.get('user_id')
            guild_id = data.get('guild_id')
            return user_id == self.user.id and guild_id == server.id

        log.voicedebug("(%s) creating futures", _func_())
        # register the futures for waiting
        session_id_future = self.ws.wait_for('VOICE_STATE_UPDATE', session_id_found)
        voice_data_future = self.ws.wait_for('VOICE_SERVER_UPDATE', lambda d: d.get('guild_id') == server.id)

        # "join" the voice channel
        log.voicedebug("(%s) setting voice state", _func_())
        await self.ws.voice_state(server.id, channel.id)

        log.voicedebug("(%s) waiting for session id", _func_())
        session_id_data = await asyncio.wait_for(session_id_future, timeout=15, loop=self.loop)

        # sometimes it gets stuck on this step.  Jake said to wait indefinitely.  To hell with that.
        log.voicedebug("(%s) waiting for voice data", _func_())
        data = await asyncio.wait_for(voice_data_future, timeout=15, loop=self.loop)

        kwargs = {
            'user': self.user,
            'channel': channel,
            'data': data,
            'loop': self.loop,
            'session_id': session_id_data.get('session_id'),
            'main_ws': self.ws
        }

        voice = discord.VoiceClient(**kwargs)
        try:
            log.voicedebug("(%s) connecting...", _func_())
            with aiohttp.Timeout(15):
                await voice.connect()

        except asyncio.TimeoutError as e:
            log.voicedebug("(%s) connection failed, disconnecting", _func_())
            try:
                await voice.disconnect()
            except:
                pass
            raise e

        log.voicedebug("(%s) connection successful", _func_())

        self.connection._add_voice_client(server.id, voice)
        return voice


    async def get_voice_client(self, channel: discord.Channel):
        if isinstance(channel, discord.Object):
            channel = self.get_channel(channel.id)

        if getattr(channel, 'type', ChannelType.text) != ChannelType.voice:
            raise AttributeError('Channel passed must be a voice channel')

        async with self.aiolocks[_func_() + ':' + channel.server.id]:
            if self.is_voice_connected(channel.server):
                return self.voice_client_in(channel.server)

            vc = None
            t0 = t1 = 0
            tries = 5

            for attempt in range(1, tries+1):
                log.debug("Connection attempt {} to {}".format(attempt, channel.name))
                t0 = time.time()

                try:
                    vc = await self.join_voice_channel(channel)
                    t1 = time.time()
                    break

                except asyncio.TimeoutError:
                    log.warning("Failed to connect, retrying ({}/{})".format(attempt, tries))

                    # TODO: figure out if I need this or not
                    # try:
                    #     await self.ws.voice_state(channel.server.id, None)
                    # except:
                    #     pass

                except:
                    log.exception("Unknown error attempting to connect to voice")

                await asyncio.sleep(0.5)

            if not vc:
                log.critical("Voice client is unable to connect, restarting...")
                await self.restart()

            log.debug("Connected in {:0.1f}s".format(t1-t0))
            log.info("Connected to {}/{}".format(channel.server, channel))

            vc.ws._keep_alive.name = 'VoiceClient Keepalive'

            return vc

    async def reconnect_voice_client(self, server, *, sleep=0.1, channel=None):
        log.debug("Reconnecting voice client on \"{}\"{}".format(
            server, ' to "{}"'.format(channel.name) if channel else ''))

        async with self.aiolocks[_func_() + ':' + server.id]:
            vc = self.voice_client_in(server)

            if not (vc or channel):
                return

            _paused = False
            player = self.get_player_in(server)

            if player and player.is_playing:
                log.voicedebug("(%s) Pausing", _func_())

                player.pause()
                _paused = True

            log.voicedebug("(%s) Disconnecting", _func_())

            try:
                await vc.disconnect()
            except:
                pass

            if sleep:
                log.voicedebug("(%s) Sleeping for %s", _func_(), sleep)
                await asyncio.sleep(sleep)

            if player:
                log.voicedebug("(%s) Getting voice client", _func_())

                if not channel:
                    new_vc = await self.get_voice_client(vc.channel)
                else:
                    new_vc = await self.get_voice_client(channel)

                log.voicedebug("(%s) Swapping voice client", _func_())
                await player.reload_voice(new_vc)

                if player.is_paused and _paused:
                    log.voicedebug("Resuming")
                    player.resume()

        log.debug("Reconnected voice client on \"{}\"{}".format(
            server, ' to "{}"'.format(channel.name) if channel else ''))

    async def disconnect_voice_client(self, server):
        vc = self.voice_client_in(server)
        if not vc:
            return

        if server.id in self.players:
            self.players.pop(server.id).kill()

        await vc.disconnect()

    async def disconnect_all_voice_clients(self):
        for vc in list(self.voice_clients).copy():
            await self.disconnect_voice_client(vc.channel.server)

    async def set_voice_state(self, vchannel, *, mute=False, deaf=False):
        if isinstance(vchannel, discord.Object):
            vchannel = self.get_channel(vchannel.id)

        if getattr(vchannel, 'type', ChannelType.text) != ChannelType.voice:
            raise AttributeError('Channel passed must be a voice channel')

        await self.ws.voice_state(vchannel.server.id, vchannel.id, mute, deaf)
        # I hope I don't have to set the channel here
        # instead of waiting for the event to update it

    def get_player_in(self, server: discord.Server) -> MusicPlayer:
        return self.players.get(server.id)

    async def get_player(self, channel, create=False, *, deserialize=False) -> MusicPlayer:
        server = channel.server

        async with self.aiolocks[_func_() + ':' + server.id]:
            if deserialize:
                voice_client = await self.get_voice_client(channel)
                player = await self.deserialize_queue(server, voice_client)

                if player:
                    log.debug("Created player via deserialization for server %s with %s entries", server.id, len(player.playlist))
                    # Since deserializing only happens when the bot starts, I should never need to reconnect
                    return self._init_player(player, server=server)

            if server.id not in self.players:
                if not create:
                    raise exceptions.CommandError(
                        'The bot is not in a voice channel.  '
                        'Use %ssummon to summon it to your voice channel.' % self.config.command_prefix)

                voice_client = await self.get_voice_client(channel)

                playlist = Playlist(self)
                player = MusicPlayer(self, voice_client, playlist)
                self._init_player(player, server=server)

            async with self.aiolocks[self.reconnect_voice_client.__name__ + ':' + server.id]:
                if self.players[server.id].voice_client not in self.voice_clients:
                    log.debug("Reconnect required for voice client in {}".format(server.name))
                    await self.reconnect_voice_client(server, channel=channel)

        return self.players[server.id]

    def _init_player(self, player, *, server=None):
        player = player.on('play', self.on_player_play) \
                       .on('resume', self.on_player_resume) \
                       .on('pause', self.on_player_pause) \
                       .on('stop', self.on_player_stop) \
                       .on('finished-playing', self.on_player_finished_playing) \
                       .on('entry-added', self.on_player_entry_added) \
                       .on('error', self.on_player_error)

        player.skip_state = SkipState()

        if server:
            self.players[server.id] = player

        return player

    async def on_player_play(self, player, entry):
        await self.update_now_playing_status(entry)
        player.skip_state.reset()

        # This is the one event where its ok to serialize autoplaylist entries
        await self.serialize_queue(player.voice_client.channel.server)

        if self.config.write_current_song:
            await self.write_current_song(player.voice_client.channel.server, entry)

        channel = entry.meta.get('channel', None)
        author = entry.meta.get('author', None)
        thumbnail = entry.filename_thumbnail

        if channel and author:
            last_np_msg = self.server_specific_data[channel.server]['last_np_msg']
            if last_np_msg and last_np_msg.channel == channel:

                async for lmsg in self.logs_from(channel, limit=1):
                    if lmsg != last_np_msg and last_np_msg:
                        await self.safe_delete_message(last_np_msg)
                        self.server_specific_data[channel.server]['last_np_msg'] = None
                    break  # This is probably redundant

            
            author_perms = self.permissions.for_user(author)
            
            if author not in player.voice_client.channel.voice_members and author_perms.skip_when_absent:
                newmsg = 'Skipping next song in `%s`: `%s` added by `%s` as queuer not in voice' % (
                    player.voice_client.channel.name, entry.title, entry.meta['author'].name)
                player.skip()
            elif self.config.now_playing_mentions:
                newmsg = '%s - your song `%s` is now playing in `%s`!' % (
                    entry.meta['author'].mention, entry.title, player.voice_client.channel.name)
            else:
                newmsg = 'Now playing in `%s`: `%s` added by `%s`' % (
                    player.voice_client.channel.name, entry.title, entry.meta['author'].name)

            if self.server_specific_data[channel.server]['last_np_msg']:
                self.server_specific_data[channel.server]['last_np_msg'] = await self.safe_edit_message(last_np_msg, newmsg, fp=thumbnail, send_if_fail=True)
            elif thumbnail:
                self.server_specific_data[channel.server]['last_np_msg'] = await self.safe_send_file(channel, newmsg, thumbnail)
            else:
                self.server_specific_data[channel.server]['last_np_msg'] = await self.safe_send_message(channel, newmsg)

        # TODO: Check channel voice state?

    async def on_player_resume(self, player, entry, **_):
        await self.update_now_playing_status(entry)

    async def on_player_pause(self, player, entry, **_):
        await self.update_now_playing_status(entry, True)
        # await self.serialize_queue(player.voice_client.channel.server)

    async def on_player_stop(self, player, **_):
        await self.update_now_playing_status()

    async def on_player_finished_playing(self, player, **_):
        def _autopause(player):
            if self._check_if_empty(player.voice_client.channel):
                log.info("Player finished playing, autopaused in empty channel")

                player.pause()
                self.server_specific_data[player.voice_client.channel.server]['auto_paused'] = True
        
        
        if not player.playlist.entries and not player.current_entry and self.config.auto_playlist:
            if not player.autoplaylist:
                if not self.autoplaylist:
                    # TODO: When I add playlist expansion, make sure that's not happening during this check
                    log.warning("No playable songs in the autoplaylist, disabling.")
                    self.config.auto_playlist = False
                else:
                    log.debug("No content in current autoplaylist. Filling with new music...")
                    player.autoplaylist = list(set(self.autoplaylist))

            while player.autoplaylist:
                if self.config.auto_playlist_random:
                    random.shuffle(player.autoplaylist)
                    song_url = random.choice(player.autoplaylist)
                else:
                    song_url = player.autoplaylist[0]
                player.autoplaylist.remove(song_url)

                info = {}

                try:
                    info = await self.downloader.extract_info(player.playlist.loop, song_url, download=False, process=False)
                except downloader.youtube_dl.utils.DownloadError as e:
                    if 'YouTube said:' in e.args[0]:
                        # url is bork, remove from list and put in removed list
                        log.error("Error processing youtube url:\n{}".format(e.args[0]))

                    else:
                        # Probably an error from a different extractor, but I've only seen youtube's
                        log.error("Error processing \"{url}\": {ex}".format(url=song_url, ex=e))

                    await self.remove_from_autoplaylist(song_url, ex=e, delete_from_ap=self.config.remove_ap)
                    continue

                except Exception as e:
                    log.error("Error processing \"{url}\": {ex}".format(url=song_url, ex=e))
                    log.exception()

                    self.autoplaylist.remove(song_url)
                    continue

                if info.get('entries', None):  # or .get('_type', '') == 'playlist'
                    log.debug("Playlist found but is unsupported at this time, skipping.")
                    # TODO: Playlist expansion

                # Do I check the initial conditions again?
                # not (not player.playlist.entries and not player.current_entry and self.config.auto_playlist)
                
                if self.config.auto_pause:
                    player.once('play', lambda player, **_: _autopause(player))

                try:
                    await player.playlist.add_entry(song_url, channel=None, author=None)
                except exceptions.ExtractionError as e:
                    log.error("Error adding song from autoplaylist: {}".format(e))
                    log.debug('', exc_info=True)
                    continue

                break

            if not self.autoplaylist:
                # TODO: When I add playlist expansion, make sure that's not happening during this check
                log.warning("No playable songs in the autoplaylist, disabling.")
                self.config.auto_playlist = False

        else: # Don't serialize for autoplaylist events
            await self.serialize_queue(player.voice_client.channel.server)

    async def on_player_entry_added(self, player, playlist, entry, **_):
        if entry.meta.get('author') and entry.meta.get('channel'):
            await self.serialize_queue(player.voice_client.channel.server)

    async def on_player_error(self, player, entry, ex, **_):
        if 'channel' in entry.meta:
            await self.safe_send_message(
                entry.meta['channel'],
                "```\nError from FFmpeg:\n{}\n```".format(ex)
            )
        else:
            log.exception("Player error", exc_info=ex)

    async def update_now_playing_status(self, entry=None, is_paused=False):
        game = None

        if not self.config.status_message:
            if self.user.bot:
                activeplayers = sum(1 for p in self.players.values() if p.is_playing)
                if activeplayers > 1:
                    game = discord.Game(type=0, name="music on %s servers" % activeplayers)
                    entry = None

                elif activeplayers == 1:
                    player = discord.utils.get(self.players.values(), is_playing=True)
                    entry = player.current_entry

            if entry:
                prefix = u'\u275A\u275A ' if is_paused else ''

                name = u'{}{}'.format(prefix, entry.title)[:128]
                game = discord.Game(type=0, name=name)
        else:
            game = discord.Game(type=0, name=self.config.status_message.strip()[:128])

        async with self.aiolocks[_func_()]:
            if game != self.last_status:
                await self.change_presence(game=game)
                self.last_status = game

    async def update_now_playing_message(self, server, message, *, channel=None):
        lnp = self.server_specific_data[server]['last_np_msg']
        m = None

        if message is None and lnp:
            await self.safe_delete_message(lnp, quiet=True)

        elif lnp:  # If there was a previous lp message
            oldchannel = lnp.channel

            if lnp.channel == oldchannel:  # If we have a channel to update it in
                async for lmsg in self.logs_from(channel, limit=1):
                    if lmsg != lnp and lnp:  # If we need to resend it
                        await self.safe_delete_message(lnp, quiet=True)
                        m = await self.safe_send_message(channel, message, quiet=True)
                    else:
                        m = await self.safe_edit_message(lnp, message, send_if_fail=True, quiet=False)

            elif channel: # If we have a new channel to send it to
                await self.safe_delete_message(lnp, quiet=True)
                m = await self.safe_send_message(channel, message, quiet=True)

            else:  # we just resend it in the old channel
                await self.safe_delete_message(lnp, quiet=True)
                m = await self.safe_send_message(oldchannel, message, quiet=True)

        elif channel: # No previous message
            m = await self.safe_send_message(channel, message, quiet=True)

        self.server_specific_data[server]['last_np_msg'] = m


    async def serialize_queue(self, server, *, dir=None):
        """
        Serialize the current queue for a server's player to json.
        """

        player = self.get_player_in(server)
        if not player:
            return

        if dir is None:
            dir = 'data/%s/queue.json' % server.id

        async with self.aiolocks['queue_serialization'+':'+server.id]:
            log.debug("Serializing queue for %s", server.id)

            with open(dir, 'w', encoding='utf8') as f:
                f.write(player.serialize(sort_keys=True))

    async def serialize_all_queues(self, *, dir=None):
        coros = [self.serialize_queue(s, dir=dir) for s in self.servers]
        await asyncio.gather(*coros, return_exceptions=True)

    async def deserialize_queue(self, server, voice_client, playlist=None, *, dir=None) -> MusicPlayer:
        """
        Deserialize a saved queue for a server into a MusicPlayer.  If no queue is saved, returns None.
        """

        if playlist is None:
            playlist = Playlist(self)

        if dir is None:
            dir = 'data/%s/queue.json' % server.id

        async with self.aiolocks['queue_serialization' + ':' + server.id]:
            if not os.path.isfile(dir):
                return None

            log.debug("Deserializing queue for %s", server.id)

            with open(dir, 'r', encoding='utf8') as f:
                data = f.read()

        return MusicPlayer.from_json(data, self, voice_client, playlist)

    async def write_current_song(self, server, entry, *, dir=None):
        """
        Writes the current song to file
        """
        player = self.get_player_in(server)
        if not player:
            return

        if dir is None:
            dir = 'data/%s/current.txt' % server.id

        async with self.aiolocks['current_song'+':'+server.id]:
            log.debug("Writing current song for %s", server.id)

            with open(dir, 'w', encoding='utf8') as f:
                f.write(entry.title)

    @ensure_appinfo
    async def _on_ready_sanity_checks(self):
        # Ensure folders exist
        await self._scheck_ensure_env()

        # Server permissions check
        await self._scheck_server_permissions()

        # playlists in autoplaylist
        await self._scheck_autoplaylist()

        # config/permissions async validate?
        await self._scheck_configs()


    async def _scheck_ensure_env(self):
        log.debug("Ensuring data folders exist")
        for server in self.servers:
            pathlib.Path('data/%s/' % server.id).mkdir(exist_ok=True)

        with open('data/server_names.txt', 'w', encoding='utf8') as f:
            for server in sorted(self.servers, key=lambda s:int(s.id)):
                f.write('{:<22} {}\n'.format(server.id, server.name))

        if not self.config.save_videos and os.path.isdir(AUDIO_CACHE_PATH):
            if self._delete_old_audiocache():
                log.debug("Deleted old audio cache")
            else:
                log.debug("Could not delete old audio cache, moving on.")


    async def _scheck_server_permissions(self):
        log.debug("Checking server permissions")
        pass # TODO

    async def _scheck_autoplaylist(self):
        log.debug("Auditing autoplaylist")
        pass # TODO

    async def _scheck_configs(self):
        log.debug("Validating config")
        await self.config.async_validate(self)

        log.debug("Validating permissions config")
        await self.permissions.async_validate(self)



#######################################################################################################################


    async def safe_send_message(self, dest, content, **kwargs):
        tts = kwargs.pop('tts', False)
        quiet = kwargs.pop('quiet', False)
        expire_in = kwargs.pop('expire_in', 0)
        allow_none = kwargs.pop('allow_none', True)
        also_delete = kwargs.pop('also_delete', None)

        msg = None
        lfunc = log.debug if quiet else log.warning

        try:
            if content is not None or allow_none:
                if isinstance(content, discord.Embed):
                    msg = await self.send_message(dest, embed=content)
                else:
                    msg = await self.send_message(dest, content, tts=tts)

        except discord.Forbidden:
            lfunc("Cannot send message to \"%s\", no permission", dest.name)

        except discord.NotFound:
            lfunc("Cannot send message to \"%s\", invalid channel?", dest.name)

        except discord.HTTPException:
            if len(content) > DISCORD_MSG_CHAR_LIMIT:
                lfunc("Message is over the message size limit (%s)", DISCORD_MSG_CHAR_LIMIT)
            else:
                lfunc("Failed to send message")
                log.noise("Got HTTPException trying to send message to %s: %s", dest, content)

        finally:
            if msg and expire_in:
                asyncio.ensure_future(self._wait_delete_msg(msg, expire_in))

            if also_delete and isinstance(also_delete, discord.Message):
                asyncio.ensure_future(self._wait_delete_msg(also_delete, expire_in))

        return msg

    async def safe_send_file(self, dest, content, fp, *, tts=False, expire_in=0, also_delete=None, quiet=False, filename=None):
        msg = None
        try:
            msg = await self.send_file(dest, fp, content=content, tts=tts)

            if msg and expire_in:
                asyncio.ensure_future(self._wait_delete_msg(msg, expire_in))

            if also_delete and isinstance(also_delete, discord.Message):
                asyncio.ensure_future(self._wait_delete_msg(also_delete, expire_in))

        except discord.Forbidden:
            if not quiet:
                self.safe_print("Warning: Cannot send message or file to %s, no permission" % dest.name)

        except discord.NotFound:
            if not quiet:
                self.safe_print("Warning: Cannot send message or file to %s, invalid channel?" % dest.name)

        return msg

    async def safe_delete_message(self, message, *, quiet=False):
        lfunc = log.debug if quiet else log.warning

        try:
            return await self.delete_message(message)

        except discord.Forbidden:
            lfunc("Cannot delete message \"{}\", no permission".format(message.clean_content))

        except discord.NotFound:
            lfunc("Cannot delete message \"{}\", message not found".format(message.clean_content))

    async def safe_edit_message(self, message, new, *, send_if_fail=False, quiet=False):
        lfunc = log.debug if quiet else log.warning

        try:
            return await self.edit_message(message, new)

        except discord.NotFound:
            lfunc("Cannot edit message \"{}\", message not found".format(message.clean_content))
            if send_if_fail:
                lfunc("Sending message instead")
                return await self.safe_send_message(message.channel, new)

    async def send_typing(self, destination):
        try:
            return await super().send_typing(destination)
        except discord.Forbidden:
            log.warning("Could not send typing to {}, no permission".format(destination))

    async def edit_profile(self, **fields):
        if self.user.bot:
            return await super().edit_profile(**fields)
        else:
            return await super().edit_profile(self.config._password,**fields)


    async def restart(self):
        self.exit_signal = exceptions.RestartSignal()
        await self.logout()

    def restart_threadsafe(self):
        asyncio.run_coroutine_threadsafe(self.restart(), self.loop)

    def _cleanup(self):
        try:
            self.loop.run_until_complete(self.logout())
        except: pass

        pending = asyncio.Task.all_tasks()
        gathered = asyncio.gather(*pending)

        try:
            gathered.cancel()
            self.loop.run_until_complete(gathered)
            gathered.exception()
        except: pass

    # noinspection PyMethodOverriding
    def run(self):
        try:
            self.loop.run_until_complete(self.start(*self.config.auth))

        except discord.errors.LoginFailure:
            # Add if token, else
            raise exceptions.HelpfulError(
                "Bot cannot login, bad credentials.",
                "Fix your token in the options file.  "
                "Remember that each field should be on their own line."
            )  #     ^^^^ In theory self.config.auth should never have no items

        finally:
            try:
                self._cleanup()
            except Exception:
                log.error("Error in cleanup", exc_info=True)

            self.loop.close()
            if self.exit_signal:
                raise self.exit_signal

    async def logout(self):
        await self.disconnect_all_voice_clients()
        return await super().logout()

    async def on_error(self, event, *args, **kwargs):
        ex_type, ex, stack = sys.exc_info()

        if ex_type == exceptions.HelpfulError:
            log.error("Exception in {}:\n{}".format(event, ex.message))

            await asyncio.sleep(2)  # don't ask
            await self.logout()

        elif issubclass(ex_type, exceptions.Signal):
            self.exit_signal = ex_type
            await self.logout()

        else:
            log.error("Exception in {}".format(event), exc_info=True)

    async def on_resumed(self):
        log.info("\nReconnected to discord.\n")

    async def on_ready(self):
        dlogger = logging.getLogger('discord')
        for h in dlogger.handlers:
            if getattr(h, 'terminator', None) == '':
                dlogger.removeHandler(h)
                print()

        log.debug("Connection established, ready to go.")

        self.ws._keep_alive.name = 'Gateway Keepalive'

        if self.init_ok:
            log.debug("Received additional READY event, may have failed to resume")
            return

        await self._on_ready_sanity_checks()

        self.init_ok = True

        ################################

        log.info("Connected: {0}/{1}#{2}".format(
            self.user.id,
            self.user.name,
            self.user.discriminator
        ))

        owner = self._get_owner(voice=True) or self._get_owner()
        if owner and self.servers:
            log.info("Owner:     {0}/{1}#{2}\n".format(
                owner.id,
                owner.name,
                owner.discriminator
            ))

            log.info('Server List:')
            for s in self.servers:
                ser = ('{} (unavailable)'.format(s.name) if s.unavailable else s.name)
                log.info(' - ' + ser)

        elif self.servers:
            log.warning("Owner could not be found on any server (id: %s)\n" % self.config.owner_id)

            log.info('Server List:')
            for s in self.servers:
                ser = ('{} (unavailable)'.format(s.name) if s.unavailable else s.name)
                log.info(' - ' + ser)

        else:
            log.warning("Owner unknown, bot is not on any servers.")
            if self.user.bot:
                log.warning(
                    "To make the bot join a server, paste this link in your browser. \n"
                    "Note: You should be logged into your main account and have \n"
                    "manage server permissions on the server you want the bot to join.\n"
                    "  " + await self.generate_invite_link()
                )

        print(flush=True)

        if self.config.bound_channels:
            chlist = set(self.get_channel(i) for i in self.config.bound_channels if i)
            chlist.discard(None)

            invalids = set()
            invalids.update(c for c in chlist if c.type == discord.ChannelType.voice)

            chlist.difference_update(invalids)
            self.config.bound_channels.difference_update(invalids)

            if chlist:
                log.info("Bound to text channels:")
                [log.info(' - {}/{}'.format(ch.server.name.strip(), ch.name.strip())) for ch in chlist if ch]
            else:
                print("Not bound to any text channels")

            if invalids and self.config.debug_mode:
                print(flush=True)
                log.info("Not binding to voice channels:")
                [log.info(' - {}/{}'.format(ch.server.name.strip(), ch.name.strip())) for ch in invalids if ch]

            print(flush=True)

        else:
            log.info("Not bound to any text channels")

        if self.config.autojoin_channels:
            chlist = set(self.get_channel(i) for i in self.config.autojoin_channels if i)
            chlist.discard(None)

            invalids = set()
            invalids.update(c for c in chlist if c.type == discord.ChannelType.text)

            chlist.difference_update(invalids)
            self.config.autojoin_channels.difference_update(invalids)

            if chlist:
                log.info("Autojoining voice chanels:")
                [log.info(' - {}/{}'.format(ch.server.name.strip(), ch.name.strip())) for ch in chlist if ch]
            else:
                log.info("Not autojoining any voice channels")

            if invalids and self.config.debug_mode:
                print(flush=True)
                log.info("Cannot autojoin text channels:")
                [log.info(' - {}/{}'.format(ch.server.name.strip(), ch.name.strip())) for ch in invalids if ch]

            autojoin_channels = chlist

        else:
            log.info("Not autojoining any voice channels")
            autojoin_channels = set()
        
        if self.config.show_config_at_start:
            print(flush=True)
            log.info("Options:")

            log.info("  Command prefix: " + self.config.command_prefix)
            log.info("  Default volume: {}%".format(int(self.config.default_volume * 100)))
            log.info("  Skip threshold: {} votes or {}%".format(
                self.config.skips_required, fixg(self.config.skip_ratio_required * 100)))
            log.info("  Now Playing @mentions: " + ['Disabled', 'Enabled'][self.config.now_playing_mentions])
            log.info("  Auto-Summon: " + ['Disabled', 'Enabled'][self.config.auto_summon])
            log.info("  Auto-Playlist: " + ['Disabled', 'Enabled'][self.config.auto_playlist] + " (order: " + ['sequential', 'random'][self.config.auto_playlist_random] + ")")
            log.info("  Auto-Pause: " + ['Disabled', 'Enabled'][self.config.auto_pause])
            log.info("  Delete Messages: " + ['Disabled', 'Enabled'][self.config.delete_messages])
            if self.config.delete_messages:
                log.info("    Delete Invoking: " + ['Disabled', 'Enabled'][self.config.delete_invoking])
            log.info("  Debug Mode: " + ['Disabled', 'Enabled'][self.config.debug_mode])
            log.info("  Downloaded songs will be " + ['deleted', 'saved'][self.config.save_videos])
            if self.config.status_message:
                log.info("  Status message: " + self.config.status_message)
            log.info("  Write current songs to file: " + ['Disabled', 'Enabled'][self.config.write_current_song])
            log.info("  Author insta-skip: " + ['Disabled', 'Enabled'][self.config.allow_author_skip])
            log.info("  Embeds: " + ['Disabled', 'Enabled'][self.config.embeds])
            log.info("  Spotify integration: " + ['Disabled', 'Enabled'][self.config._spotify])

        print(flush=True)

        await self.update_now_playing_status()

        # maybe option to leave the ownerid blank and generate a random command for the owner to use
        # wait_for_message is pretty neato

        await self._join_startup_channels(autojoin_channels, autosummon=self.config.auto_summon)

        # we do this after the config stuff because it's a lot easier to notice here
        if self.config.missing_keys:
            log.warning('Your config file is missing some options. If you have recently updated, '
                        'check the example_options.ini file to see if there are new options available to you. '
                        'The options missing are: {0}'.format(self.config.missing_keys))
            print(flush=True)

        # t-t-th-th-that's all folks!

    def _gen_embed(self):
        """Provides a basic template for embeds"""
        e = discord.Embed(colour=0x1abc9c)
        e.set_author(name="Sigma v" + BOTVERSION, icon_url=self.user.avatar_url)
        e.set_footer(text="Sugoi!")
        return e

#####################################################

    """

    Custom Commands
    Code written by NeonLights10, 2017 (C) 

    """
    async def cmd_hello(self, author):
        """
        Usage:
            {command_prefix}hello
        Talk to Sigma-chan!    
        """
        msg = "Hello %s! How are you doing today?" % author.mention
        return Response(msg, reply=False, delete_after=30)

    async def cmd_hug(self, channel, author, user_mentions):
        """
        Usage:
            {command_prefix}hug [recipient]
        Hug somebody!
        If no recipient is specified, Sigma-chan will hug you <3
        """
        #thumbnail = os.path.join('data/gifs/', random.choice(os.listdir(GIF_CACHE_PATH)))
        #time.sleep(.2) #welcome to jenky solutions part 10

        if user_mentions and len(user_mentions) == 1:
            msg = "%s hugged %s!" % (author.mention, user_mentions[0].mention)
        elif user_mentions and len(user_mentions) > 1:
            msg = "%s hugged " % author.mention
            if len(user_mentions) == 2:
                msg += "%s " % user_mentions[0].mention
            else:
                for i in range(len(user_mentions) - 1):
                    msg += "%s, " % user_mentions[i].mention
            msg += "and %s" % user_mentions[len(user_mentions) - 1].mention
            #raise exceptions.CommandError(
            #    'You are trying to hug too many people at once! Take it once at a time, please <3' , expire_in=20
            #)
        else:
            msg = self.user.name + " gives %s a soft hug <:heartmodern:328603582993661982>" % (author.mention)

        async with aiohttp.ClientSession() as session:
            async with session.get('https://nekos.life/api/v2/img/hug') as resp:
                rjson = await resp.json()
                content = discord.Embed(colour=0x1abc9c)
                content.set_footer(text="Sugoi!")
                url = rjson.get('url')
                #something something 2 positional parameters so i have to do this extra variable assignment
                content.set_image(url=url)
                content.description = msg
                await self.safe_send_message(channel, content, expire_in=45)    
    
        

    async def cmd_yikes(self, message):
        return Response("Yikes! 😬", reply=False, delete_after=30)

    async def cmd_shrug(self, message):
        return Response("¯\_(ツ)_/¯", reply=False, delete_after=30)

    async def cmd_roll(self, author, num=None):
        if num:
            try:
                num = int(num)
                answer = random.randint(0, num)
                msg = "%s rolled a " % author.mention + str(answer) 
                return Response(msg, reply=False, delete_after=30)
            except ValueError:
                pass
        answer = random.randint(0, 100)
        msg = "%s rolled a " % author.mention + str(answer)
        return Response(msg, reply=False, delete_after=30)

    #TODO: Make aar persist through shutdown/restart (tough)
    @owner_only
    async def cmd_aar(self, channel, server, role=None):
        """
        Usage:
            {command_prefix}aar [role]
        Enables auto assign role with a specific role. Server specific.
        Owner only.
        """
        if role:
            #Let's find the role
            role = discord.utils.find(lambda r: r.name == role, server.roles)
            if role:
                self.autorole[server] = role
                self.autoassignrole = True
                return Response("Enabled autorole in %s with role %s" % (server,role), reply=False, delete_after=20)

            else:
                #oops, can't find that role. Try again
                raise exceptions.CommandError("Invalid role specified.", expire_in=20)

        elif not self.autoassignrole:
            raise exceptions.CommandError("Autorole is currently disabled. No role specified.", expire_in=20)

        elif self.autoassignrole:
            self.autoassignrole = False
            return Response("Autorole disabled", reply=False, delete_after=20)
        #print(self.autorole)

    async def cmd_purge(self, channel, message, user_mentions, leftover_args, num = None, usermentions = None):
        """
        Usage:
            {command_prefix}purge [number]
        Deletes the previous # of messages from the channel.
        """

        if user_mentions:
            for user in user_mentions:
                def user_check(m):
                    return m.author == user
                if num:
                    try:
                        num = int(num)
                    except ValueError:
                        raise exceptions.CommandError("Invalid number specified.", expire_in=20)

                    deleted = await self.purge_from(channel, limit=num+1, check=user_check)
                    msg = "The last {} messages by {} were purged".format(len(deleted), user.name)
                    return Response(msg, reply=False, delete_after=20)
        if num:
            try:
                num = int(num)
            except ValueError:
                raise exceptions.CommandError("Invalid number specified.", expire_in=20)

            await self.purge_from(channel, limit=num, before=message)
            msg = str(num) + " message(s) purged."
            return Response(msg, reply=False, delete_after=20)
        else:
            raise exceptions.CommandError("Specify a number of messages to delete!")
        
    async def cmd_mute(self, message, server, author, channel, mentions, time=None, reason=None):
            """
            Usage:
                {command_prefix}mute [user_mentions] [time] [reason]
            Mutes the specified users. Length of mute in seconds and reason are optional.
            """
            if not message.mentions:
                raise exceptions.CommandError("Invalid user specified.")
            if time and not reason and not time.isdigit():
                reason = time
                time = None
            if time:
                try:
                    float(time)
                except ValueError:
                    raise exceptions.CommandError("Time provided invalid:\n{}\n".format(time))
            mutedrole = discord.utils.get(server.roles, name='Muted')
            if not mutedrole:
                raise exceptions.CommandError('No Muted role created')
            for member in message.mentions:
                if member.id in (self.user.id, author.id, self.config.owner_id):
                    raise exceptions.CommandError("You cannot perform this command on this user.", expire_in=20)
                try:
                    await self.add_roles(member, mutedrole)
                    await self.server_voice_state(member, mute=True)
                except discord.Forbidden:
                    raise exceptions.CommandError('Not enough permissions to mute user : {}'.format(member.name))
                except:
                    raise exceptions.CommandError('Unable to mute user defined:\n{}\n'.format(member.name))
            await self.safe_send_message(channel, "Muted " + str(len(message.mentions)) + " users.", expire_in=30)
            if time:
                await asyncio.sleep(float(time))
                for member in message.mentions:
                    memberroles = member.roles
                    if mutedrole in memberroles:
                        await self.remove_roles(member, mutedrole)
                        await self.server_voice_state(member, mute=False)

    async def cmd_unmute(self, message, server, channel, mentions):
        """
        Usage:
            {command_prefix}mute [user_mentions]
        Unmutes users
        """
        if not mentions:
            raise exceptions.CommandError("Invalid user specified.")
        for member in message.mentions:
            mutedrole = discord.utils.get(server.roles, name='Muted')
            memberroles = member.roles
            if mutedrole in memberroles:
                await self.remove_roles(member, mutedrole)
                await self.server_voice_state(member, mute=False)
            else:
                raise exceptions.CommandError("User not muted!", expire_in=20)
        await self.safe_send_message(channel, "Muted " + str(len(message.mentions)) + " users.", expire_in=30)

    """ 
    # Debugging purpose
    async def cmd_getroles(self, author):
        for role in author.roles:
            print(role)
        return Response("Printed roles to console", reply=False, delete_after=10)
    """

    async def cmd_time(self, timezone=None):
        """
        Usage:
            {command_prefix}time [timezone]
        Prints the current date and time in UTC.
        If a timezone is specified, the time will be displayed in that timezone.
        """        
        #Get current time in UTC.
        current_time = datetime.datetime.utcnow()
       
        #If a timezone is specified let's convert time into that timezone.
        if timezone:
            timezone = timezone.upper()
            if re.search('(UTC)(\+|\-)(\d{2})(:\d{2})?', timezone):
                if find_key(timezone_dict, timezone):
                    pass
                else:
                    raise exceptions.CommandError("This is not a valid timezone.", expire_in=20)
            else:
                #Let's convert the abbreviation into UTC format
                try:
                    timezone = timezone_dict[timezone]
                except KeyError:
                    raise exceptions.CommandError("This is not a valid timezone.", expire_in=20)
            #Take care of those pesky 30 or 45 minute intervals that some timezones have (I'm looking at you, NST :/)
            if ":" in timezone:
                timezone_parsed = timezone.split(":")
                timezone_hour = timezone_parsed[0]
                timezone_minute = timezone_parsed[1]
                try:
                    hour = int(timezone_hour[3:len(timezone_hour)])
                    minute = int(timezone_minute)
                except ValueError:
                    raise exceptions.CommandError("This is not a valid timezone.", expire_in=20)
                 
                current_time = current_time + timedelta(hours=hour, minutes=minute)
            else:
                try:
                    hour = int(timezone[3:len(timezone)])
                except ValueError:
                    raise exceptions.CommandError("This is not a valid timezone.", expire_in=20)

                current_time = current_time + timedelta(hours=hour)
        else:
            timezone = "UTC"
            
        current_time = current_time.strftime('%Y-%m-%d | %H:%M ' + timezone)
        msg = "The current time is: " + current_time
        return Response(msg, reply=True, delete_after=30)

    async def cmd_tconvert(self, time_in=None, timezone1=None, timezone2=None):
        """
        Usage:
            {command_prefix}tconvert [time] [timezone_from] [timezone_to]
            Convert a time from one timezone to another.
            The first timezone is the original timezone the time is in.
            The second timezone is the timezone you wish to convert to.
        """
        #Parse time first
        if time_in:
            time_parsed = time_in.split(":")
            try:
                hour = int(time_parsed[0])
                minute = int(time_parsed[1])
            except ValueError:
                raise exceptions.CommandError("This is not a valid time!", expire_in=20)
            if hour > 23 or hour < 0 or minute > 59 or minute < 0:
                raise exceptions.CommandError("This is not a valid time!", expire_in=20)
        else:
            raise exceptions.CommandError("You did not specify a time!", expire_in=20)
        #Now parse from timezone and separate into hours and minutes, and get the combined minute version
        if timezone1:
            timezone1 = timezone1.upper()
            try:
                if re.search('(UTC)(\+|\-)(\d{1,2})(:\d{2})?', timezone1):
                    if find_key(timezone_dict, timezone1):
                        pass
                    else:
                        raise exceptions.CommandError("This is not a valid timezone.", expire_in=20)
                else:
                    timezone1 = timezone_dict[timezone1]
            except KeyError:
                raise exceptions.CommandError("This is not a valid from timezone.", expire_in=20)
            if ":" in timezone1:
                timezone1_parsed = timezone1.split(":")
                try:
                    timezone1_hour = timezone1_parsed[0]
                    timezone1_hour = int(timezone1_hour[3:len(timezone1_hour)])
                    timezone1_minute = int(timezone1_parsed[1])
                    if timezone1_hour < 0:
                        timezone1_combined = timezone1_hour * 60 - timezone1_minute
                    elif timezone1_hour > 0:
                        timezone1_combined = timezone1_hour * 60 + timezone1_minute
                    elif timezone1_hour == 0:
                        timezone1_combined = 0
                except ValueError:
                    raise exceptions.CommandError("Timezone dictionary error.", expire_in=20)
            else:
                try:
                    timezone1_hour = int(timezone1[3:len(timezone1)])
                    timezone1_combined = timezone1_hour * 60
                except ValueError:
                    raise exceptions.CommandError("Could not parse timezone.", expire_in=20)
            #Do the same with timezone 2, make sure it's nested in timezone1 check
            if timezone2:
                timezone2 = timezone2.upper()
                try:
                    if re.search('(UTC)(\+|\-)(\d{2})(:\d{2})?', timezone2):
                        if find_key(timezone_dict, timezone2):
                            pass
                        else:
                            raise exceptions.CommandError("This is not a valid timezone.", expire_in=20)
                    else:
                        timezone2 = timezone_dict[timezone2]
                except KeyError:
                        raise exceptions.CommandError("This is not a valid timezone.", expire_in=20)
                if ":" in timezone2:
                    timezone2_parsed = timezone2.split(":")
                    try:
                        timezone2_hour = timezone2_parsed[0]
                        timezone2_hour = int(timezone2_hour[3:len(timezone2_hour)])
                        timezone2_minute = int(timezone2_parsed[1])
                        if timezone2_hour < 0:
                            timezone2_combined = timezone2_hour * 60 - timezone2_minute
                        elif timezone2_hour > 0:
                            timezone2_combined = timezone2_hour * 60 + timezone2_minute
                        elif timezone2_hour == 0:
                            timezone2_combined = 0;
                    except ValueError:
                        raise exceptions.CommandError("Timezone dictionary error.", expire_in=20)
                else:
                    try:
                        timezone2_hour = int(timezone2[3:len(timezone2)])
                        timezone2_combined = timezone2_hour * 60
                    except ValueError:
                        raise exceptions.CommandError("Could not parse timezone.", expire_in=20)
                    
                #Catch all the different scenarios that could happen
                if timezone1_hour == 0:
                    difference = timezone2_combined
                elif timezone2_hour == 0:
                    if timezone1_hour < timezone2_hour:
                        difference = abs(timezone1_combined)
                    elif timezone1_hour > timezone2_hour:
                        difference = -timezone1_combined
                elif timezone1_hour < 0 and timezone2_hour < 0:
                    difference = abs(timezone1_combined) - abs(timezone2_combined)
                elif timezone1_hour < 0 and timezone2_hour > 0:
                    difference = abs(timezone1_combined) + abs(timezone2_combined)
                elif timezone1_hour > 0 and timezone2_hour < 0:
                    difference = -(abs(timezone1_combined) + abs(timezone2_combined))
                elif timezone1_hour > 0 and timezone2_hour > 0:
                    difference = abs(timezone1_combined - timezone2_combined)
                
                converted_time = hour * 60 + minute + difference
                hour = int(converted_time / 60)
                #Make sure time isn't reported in negative time (because that doesn't exist) OR >24 (because that also doesn't exist)
                if hour < 0:
                    hour = 24 + hour
                if hour >= 24:
                    hour = abs(24 - hour)
                minute = converted_time % 60
                #print(converted_time)
               
                #I'm lazy, probably a better way to do this
                if minute == 0:
                    minute = str(minute) + "0"
                elif minute < 10:
                    minute = "0" + str(minute)
                final_time = str(hour) + ":" + str(minute)

                msg = "Converted time from **" + timezone1 + "** to **" + timezone2 + "** is **" + final_time + "**"
                return Response(msg, reply=False, delete_after=30)
            else:
                raise exceptions.CommandError("You did not specify a to timezone!")
        else:
            raise exceptions.CommandError("You did not specify a from timezone!")
    
    async def cmd_repeat(self, player):
        """
        Usage:
            {command_prefix}repeat
        Cycles through the repeat options. Default is no repeat, switchable to repeat all or repeat current song.
        """
        if player.is_stopped:
            raise exceptions.CommandError("Can't change repeat mode! The player is not playing!", expire_in=20)

        player.repeat()

        if player.is_repeatNone:
            return Response(":play_pause: Repeat mode: None", delete_after=20)
        if player.is_repeatAll:
            return Response(":repeat: Repeat mode: All", delete_after=20)
        if player.is_repeatSingle:
            return Response(":repeat_one: Repeat mode: Single", delete_after=20)

    async def cmd_promote(self, player, position=None):
        """
        Usage:
            {command_prefix}promote
            {command_prefix}promote [song position]
        Promotes the last song in the queue to the front.
        If you specify a position in the queue, it promotes the song at that position to the front.
        """
        #if self.ownerlock:
        #    raise exceptions.PermissionsError("This bot has been locked by the owner")

        if player.is_stopped:
            raise exceptions.CommandError("Can't modify the queue! The player is not playing!", expire_in=20)

        length = len(player.playlist.entries)

        if length < 2:
            raise exceptions.CommandError("Can't promote! Please add at least 2 songs to the queue!", expire_in=20)

        if not position:
            entry = player.playlist.promote_last()
        else:
            try:
                position = int(position)
            except ValueError:
                raise exceptions.CommandError("This is not a valid song number! Please choose a song \
                    number between 2 and {}!".format(length), expire_in=20)

            if position == 1:
                raise exceptions.CommandError("This song is already at the top of the queue!", expire_in=20)
            if position < 1 or position > length:
                raise exceptions.CommandError("Can't promote a song not in the queue! Please choose a song \
                    number between 2 and {}!".format(length), expire_in=20)

            entry = player.playlist.promote_position(position)

        reply_text = "Promoted **{}** to the :top: of the queue. Estimated time until playing: {}"
        btext = entry.title

        try:
            time_until = await player.playlist.estimate_time_until(1, player)
        except:
            traceback.print_exc()
            time_until = ''

        reply_text.format(btext, time_until)

        return Response(reply_text, delete_after=30)

    async def cmd_sub(self, player, channel, author, permissions, leftover_args, song_url, pos=None):
        """
        Usage:
            {command_prefix}sub [song position]
        Substitute a song in the queue with a different song.
        """
        #if self.ownerlock:
        #    raise exceptions.PermissionsError("This bot has been locked by the owner")

        if player.is_stopped:
            raise exceptions.CommandError("Can't modify the queue! The player is not playing!", expire_in=20)

        length = len(player.playlist.entries)

        try:
            pos = int(pos)
        except ValueError:
            raise exceptions.CommandError("This is not a valid song number! Please choose a song \
                    number between 1 and %s!" % length, expire_in=20)

        if pos < 1 or pos > length:
            raise exceptions.CommandError("Can't substitute a song not in the queue! Please choose a song \
                number between 1 and %s!" % length, expire_in=20)

        song_url = song_url.strip('<>')

        await self.send_typing(channel)

        if leftover_args:
            song_url = ' '.join([song_url, *leftover_args])
        leftover_args = None  # prevent some crazy shit happening down the line

        # Make sure forward slashes work properly in search queries
        linksRegex = '((http(s)*:[/][/]|www.)([a-z]|[A-Z]|[0-9]|[/.]|[~])*)'
        pattern = re.compile(linksRegex)
        matchUrl = pattern.match(song_url)
        song_url = song_url.replace('/', '%2F') if matchUrl is None else song_url

        # Rewrite YouTube playlist URLs if the wrong URL type is given
        playlistRegex = r'watch\?v=.+&(list=[^&]+)'
        matches = re.search(playlistRegex, song_url)
        groups = matches.groups() if matches is not None else []
        song_url = "https://www.youtube.com/playlist?" + groups[0] if len(groups) > 0 else song_url

        if song_url.startswith('spotify:'):  # treat it as probably a spotify URI
            if self.config._spotify:
                song_url = song_url.split(":", 1)[1]
                try:

                    if song_url.startswith('track:'):
                        song_url = song_url.split(":", 1)[1]
                        res = await self.spotify.get_track(song_url)
                        song_url = res['artists'][0]['name'] + ' ' + res['name']  # spooky

                    elif song_url.startswith('album:'):
                        song_url = song_url.split(":", 1)[1]
                        res = await self.spotify.get_album(song_url)
                        await self._do_playlist_checks(permissions, player, author, res['tracks']['items'])
                        procmesg = await self.safe_send_message(channel, self.str.get('cmd-play-spotify-album-process', 'Processing album `{0}`').format(res['name']))
                        for i in res['tracks']['items']:
                            song_url = i['name'] + ' ' + i['artists'][0]['name']
                            log.debug('Processing {0}'.format(song_url))
                            await self.cmd_play(message, player, channel, author, permissions, leftover_args, song_url)
                        await self.safe_delete_message(procmesg)
                        return Response(self.str.get('cmd-play-spotify-album-queued', "Enqueued `{0}` with **{1}** songs.").format(res['name'], len(res['tracks']['items'])))

                    elif song_url.startswith('user:') and 'playlist:' in song_url:
                        user = song_url.split(":",)[1]
                        song_url = song_url.split(":", 3)[3]
                        res = await self.spotify.get_playlist(user, song_url)
                        await self._do_playlist_checks(permissions, player, author, res['tracks']['items'])
                        procmesg = await self.safe_send_message(channel, self.str.get('cmd-play-spotify-playlist-process', 'Processing playlist `{0}`').format(res['name']))
                        for i in res['tracks']['items']:
                            song_url = i['track']['name'] + ' ' + i['track']['artists'][0]['name']
                            log.debug('Processing {0}'.format(song_url))
                            await self.cmd_play(message, player, channel, author, permissions, leftover_args, song_url)
                        await self.safe_delete_message(procmesg)
                        return Response(self.str.get('cmd-play-spotify-playlist-queued', "Enqueued `{0}` with **{1}** songs.").format(res['name'], len(res['tracks']['items'])))

                    else:
                        raise exceptions.CommandError(self.str.get('cmd-play-spotify-unsupported', 'That is not a supported Spotify URI.'), expire_in=30)

                except exceptions.SpotifyError:
                    raise exceptions.CommandError(self.str.get('cmd-play-spotify-invalid', 'You either provided an invalid URI, or there was a problem.'))
            else:
                raise exceptions.CommandError(self.str.get('cmd-play-spotify-unavailable', 'The bot is not setup to support Spotify URIs. Check your config.'))

        async with self.aiolocks[_func_() + ':' + author.id]:
            if permissions.max_songs and player.playlist.count_for_user(author) >= permissions.max_songs:
                raise exceptions.PermissionsError(
                    self.str.get('cmd-play-limit', "You have reached your enqueued song limit ({0})").format(permissions.max_songs), expire_in=30
                )

            if player.karaoke_mode and not permissions.bypass_karaoke_mode:
                raise exceptions.PermissionsError(
                    self.str.get('karaoke-enabled', "Karaoke mode is enabled, please try again when its disabled!"), expire_in=30
                )

            try:
                info = await self.downloader.extract_info(player.playlist.loop, song_url, download=False, process=False)
            except Exception as e:
                if 'unknown url type' in str(e):
                    song_url = song_url.replace(':', '')  # it's probably not actually an extractor
                    info = await self.downloader.extract_info(player.playlist.loop, song_url, download=False, process=False)
                else:
                    raise exceptions.CommandError(e, expire_in=30)

            if not info:
                raise exceptions.CommandError(
                    self.str.get('cmd-play-noinfo', "That video cannot be played. Try using the {0}stream command.").format(self.config.command_prefix),
                    expire_in=30
                )

            log.debug(info)

            if info.get('extractor', '') not in permissions.extractors and permissions.extractors:
                raise exceptions.PermissionsError(
                    self.str.get('cmd-play-badextractor', "You do not have permission to play media from this service."), expire_in=30
                )

            # abstract the search handling away from the user
            # our ytdl options allow us to use search strings as input urls
            if info.get('url', '').startswith('ytsearch'):
                # print("[Command:play] Searching for \"%s\"" % song_url)
                info = await self.downloader.extract_info(
                    player.playlist.loop,
                    song_url,
                    download=False,
                    process=True,    # ASYNC LAMBDAS WHEN
                    on_error=lambda e: asyncio.ensure_future(
                        self.safe_send_message(channel, "```\n%s\n```" % e, expire_in=120), loop=self.loop),
                    retry_on_error=True
                )

                if not info:
                    raise exceptions.CommandError(
                        self.str.get('cmd-play-nodata', "Error extracting info from search string, youtubedl returned no data. "
                                                        "You may need to restart the bot if this continues to happen."), expire_in=30
                    )

                if not all(info.get('entries', [])):
                    # empty list, no data
                    log.debug("Got empty list, no data")
                    return

                # TODO: handle 'webpage_url' being 'ytsearch:...' or extractor type
                song_url = info['entries'][0]['webpage_url']
                info = await self.downloader.extract_info(player.playlist.loop, song_url, download=False, process=False)
                # Now I could just do: return await self.cmd_play(player, channel, author, song_url)
                # But this is probably fine

            # TODO: Possibly add another check here to see about things like the bandcamp issue
            # TODO: Where ytdl gets the generic extractor version with no processing, but finds two different urls

            if 'entries' in info:
                raise exceptions.CommandError("You cannot sub a playlist!", expire_in=30)

            else:
                if info.get('extractor', '').startswith('youtube:playlist'):
                    try:
                        info = await self.downloader.extract_info(player.playlist.loop, 'https://www.youtube.com/watch?v=%s' % info.get('url', ''), download=False, process=False)
                    except Exception as e:
                        raise exceptions.CommandError(e, expire_in=30)

                if permissions.max_song_length and info.get('duration', 0) > permissions.max_song_length:
                    raise exceptions.PermissionsError(
                        self.str.get('cmd-play-song-limit', "Song duration exceeds limit ({0} > {1})").format(info['duration'], permissions.max_song_length),
                        expire_in=30
                    )

                try:
                    old_entry = player.playlist.entries[pos - 1]
                    entry, position = await player.playlist.sub_entry(song_url, pos, channel=channel, author=author)
                    # Get the song ready now, otherwise race condition where finished-playing will fire before
                    # the song is finished downloading, which will then cause another song from autoplaylist to
                    # be added to the queue. Even when we're subbing, we want to make sure that if the song ends 
                    # and the song is being subbed at position 1 we don't have autoplaylist running
                    await entry.get_ready_future()

                except exceptions.WrongEntryTypeError as e:
                    if e.use_url == song_url:
                        log.warning("Determined incorrect entry type, but suggested url is the same.  Help.")

                    log.debug("Assumed url \"%s\" was a single entry, was actually a playlist" % song_url)
                    log.debug("Using \"%s\" instead" % e.use_url)

                    return await self.cmd_play(player, channel, author, permissions, leftover_args, e.use_url)

                reply_text = "Substituted **%s** with **%s** at position %s"
                btext1 = old_entry.title
                btext2 = entry.title


            if position == 1 and player.is_stopped:
                position = self.str.get('cmd-play-next', 'Up next!')
                reply_text %= (btext2, position)

            else:
                try:
                    time_until = await player.playlist.estimate_time_until(position, player)
                    reply_text += self.str.get('cmd-play-eta', ' - estimated time until playing: %s')
                except:
                    traceback.print_exc()
                    time_until = ''

                reply_text %= (btext, btext2, position, ftimedelta(time_until))

        return Response(reply_text, delete_after=30)

    async def on_member_join(self, member):
        if self.autorole:
            await self.add_roles(member, self.autorole[member.server])
            log.info("Added a user")
        else:
            log.info("Autorole disabled")

    async def cmd_addrole(self, message, server, mentions, leftover_args):
        """
        Usage:
            {command_prefix}addteam <user mentions> <teamname>

        Adds selected members to a new team (role created with name specified). User mentions are optional.
        """

        args = ' '.join(leftover_args)
        log.info(args)
        #This is actually the most jenky way to deal with whatever the fudge this bot handles leftover args, but I have no better ideas right now.
        parsedargs = re.sub('<@!?\d{17,18}>', '', args).strip()
        log.info(parsedargs)
        if parsedargs:
            rolename = parsedargs
            role_pos = None;
        else:
            raise exceptions.CommandError("Invalid arguments specified, or order is incorrect!")
        
        role_pos = server.role_hierarchy[len(server.role_hierarchy)-1]
        '''for role in server.roles:
            #probably shouldn't assume they put their Muted role at the bottom but it's ok
            #since we default just put it above @everyone!
            if role.name == "Muted":
                role_pos = server.role_hierarchy[len(server.role_hierarchy)-2]

            #and I quote: this was a dumb idea'''

        role_permissions = server.default_role
        role_permissions = role_permissions.permissions
        role_permissions.change_nickname = True

        try:
            role = await self.create_role(server, name=rolename, permissions=role_permissions, colour=discord.Colour(int('9d0000', 16)), mentionable=True)
        except:
            raise exceptions.CommandError("Creating role failed!")

        try:
            await self.move_role(server, role, role_pos.position)
        except:
            log.error("Could not move role.")

        if message.mentions:
            for member in message.mentions:
                try:
                    await self.add_roles(member, role)
                except:
                    raise exceptions.CommandError("Role created, but failed to add %s to the role." % member.name);
        return Response("Created role and added %s member(s)!" % len(message.mentions), delete_after=30)

    async def cmd_removerole(self, message, server, role_mentions):
        """
        Usage:
            {command_prefix}removeteam <role mention>

        Removes a team completely
        """
        if message.role_mentions:
            for role in message.role_mentions:
                try:
                    await self.delete_role(server, role)
                except:
                    raise exceptions.CommandError("Could not delete %s!" % role.name)
                return Response("Deleted %s team(s)" % len(message.role_mentions), delete_after=30)
        else:
            raise exceptions.CommandError("No team specified!")

    async def cmd_addmember(self, message, server, role_mentions, leftover_args):
        """
        Usage:
            {command_prefix}addmember <user mentions> (role mentions) (role name)

        Adds one or more members to one or more roles. You can choose to use either role mentions (to make people angry) or just the name of the role itself.
        """
        args = ' '.join(leftover_args)
        log.info(args)
        parsedargs = re.sub('<@!?\d{17,18}>', '', args).strip()
        parsedargs = re.sub('<@&!?\d{17,18}>', '', args).strip()
        log.info(parsedargs)
        if (not message.role_mentions and not parsedargs) or not message.mentions:
            raise exceptions.CommandError("Invalid arguments specified!")
        for member in message.mentions:
            if parsedargs:
                for role in server.roles:
                    if re.search('^' + parsedargs + '$', role.name):
                        try:
                            await self.add_roles(member, role)
                        except:
                            raise exceptions.CommandError("Failed to add %s to %s" % (member.name, role.name))
                    else:
                        raise exceptions.CommandError("Role not found! Did you spell it wrong?")
            elif message.role_mentions:
                for role in message.role_mentions:
                    try:
                        await self.add_roles(member, role)
                    except:
                        raise exceptions.CommandError("Failed to add %s to %s" % (member.name, role.name))
        return Response("Added members to roles.", delete_after=30)

    async def cmd_removemember(self, message, server, role_mentions, mentions, leftover_args):
        """
        Usage:
            {command_prefix}removemember <user mentions> (role mentions) (role name)

        Removes one or more members from one or more roles. You can choose to use either role mentions (to make people angry) or just the name of the role itself.
        """
        args = ' '.join(leftover_args)
        log.info(args)
        parsedargs = re.sub('<@!?\d{17,18}>', '', args).strip()
        parsedargs = re.sub('<@&!?\d{17,18}>', '', args).strip()
        if (not message.role_mentions and not parsedargs) or not message.mentions:
            raise exceptions.CommandError("Invalid arguments specified!")
        for member in message.mentions:
            if parsedargs:
                for role in server.roles:
                    if re.search('^' + parsedargs + '$', role.name):
                        try:
                            await self.remove_roles(member, role)
                        except:
                            raise exceptions.CommandError("Failed to remove %s to %s" % (member.name, role.name))
                    else:
                        raise exceptions.CommandError("Role not found! Did you spell it wrong?")
            elif message.role_mentions:
                for role in message.role_mentions:
                    try:
                        await self.remove_roles(member, role)
                    except:
                        raise exceptions.CommandError("Failed to remove %s to %s" % (member.name, role.name))
        return Response("Removed members from roles.", delete_after=30)

    async def cmd_stats(self, channel, player):
        """
        Usage:
            {command_prefix}stats
        Displays bot stats.
        """
        content = discord.Embed(colour=0x1abc9c)
        content.set_author(name="Sigma v" + BOTVERSION, icon_url=self.user.avatar_url)
        content.set_footer(text="Sugoi!")
        content.set_thumbnail(url=self.user.avatar_url)
        content.add_field(name="Author", value="Neon#4792")
        content.add_field(name="BotID", value=self.user.id)
        content.add_field(name="Songs Played", value=player.songs_played)
        content.add_field(name="Messages", value=str(self.message_count) + ' (' + '%.2f'%(self.message_count / (time.time()-self.uptime)) +'/sec)')
        process = psutil.Process(os.getpid())
        mem = process.memory_full_info()
        mem = mem.uss / 1000000
        content.add_field(name="Memory Usage", value='%.2f'%(mem) + "MB")
        ctime = float(time.time()-self.uptime)
        day = ctime // (24 * 3600)
        ctime = ctime % (24 * 3600)
        hour = ctime // 3600
        ctime %= 3600
        minutes = ctime // 60
        content.add_field(name="Uptime", value="%d days\n%d hours\n%d minutes" % (day, hour, minutes))
        await self.safe_send_message(channel, content, expire_in=60)

    async def cmd_kick(self, message, server, mentions):
        #do something here
        pass

    async def cmd_resetplaylist(self, player, channel):
        """
        Usage:
            {command_prefix}resetplayer

        Resets all songs in the server's autoplaylist
        """
        player.autoplaylist = list(set(self.autoplaylist))
        return Response(self.str.get('cmd-resetplaylist-response', '\N{OK HAND SIGN}'), delete_after=15)

    async def cmd_help(self, message, channel, command=None):
        """
        Usage:
            {command_prefix}help [command]

        Prints a help message.
        If a command is specified, it prints a help message for that command.
        Otherwise, it lists the available commands.
        """
        self.commands = []
        self.is_all = False
        prefix = self.config.command_prefix

        if command:
            if command.lower() == 'all':
                self.is_all = True
                await self.gen_cmd_list(message, list_all_cmds=True)

            else:
                cmd = getattr(self, 'cmd_' + command, None)
                if cmd and not hasattr(cmd, 'dev_cmd'):
                    return Response(
                        "```\n{}```".format(
                            dedent(cmd.__doc__)
                        ).format(command_prefix=self.config.command_prefix),
                        delete_after=60
                    )
                else:
                    raise exceptions.CommandError(self.str.get('cmd-help-invalid', "No such command"), expire_in=10)

        elif message.author.id == self.config.owner_id:
            await self.gen_cmd_list(message, list_all_cmds=True)

        else:
            await self.gen_cmd_list(message)

        desc = '```\n' + ', '.join(self.commands) + '\n```\n' + self.str.get(
            'cmd-help-response', 'For information about a particular command, run `{}help [command]`\n'
                                 'For further help, see https://just-some-bots.github.io/MusicBot/').format(self.user.name, prefix)
        if not self.is_all:
            desc += self.str.get('cmd-help-all', '\nOnly showing commands you can use, for a list of all commands, run `{}help all`').format(prefix)

        return Response(desc, reply=True, delete_after=60)

    async def cmd_blacklist(self, message, user_mentions, option, something):
        """
        Usage:
            {command_prefix}blacklist [ + | - | add | remove ] @UserName [@UserName2 ...]

        Add or remove users to the blacklist.
        Blacklisted users are forbidden from using bot commands.
        """

        if not user_mentions:
            raise exceptions.CommandError("No users listed.", expire_in=20)

        if option not in ['+', '-', 'add', 'remove']:
            raise exceptions.CommandError(
                self.str.get('cmd-blacklist-invalid', 'Invalid option "{0}" specified, use +, -, add, or remove').format(option), expire_in=20
            )

        for user in user_mentions.copy():
            if user.id == self.config.owner_id:
                print("[Commands:Blacklist] The owner cannot be blacklisted.")
                user_mentions.remove(user)

        old_len = len(self.blacklist)

        if option in ['+', 'add']:
            self.blacklist.update(user.id for user in user_mentions)

            write_file(self.config.blacklist_file, self.blacklist)

            return Response(
                self.str.get('cmd-blacklist-added', '{0} users have been added to the blacklist').format(len(self.blacklist) - old_len),
                reply=True, delete_after=10
            )

        else:
            if self.blacklist.isdisjoint(user.id for user in user_mentions):
                return Response(self.str.get('cmd-blacklist-none', 'None of those users are in the blacklist.'), reply=True, delete_after=10)

            else:
                self.blacklist.difference_update(user.id for user in user_mentions)
                write_file(self.config.blacklist_file, self.blacklist)

                return Response(
                    self.str.get('cmd-blacklist-removed', '{0} users have been removed from the blacklist').format(old_len - len(self.blacklist)),
                    reply=True, delete_after=10
                )

    async def cmd_id(self, author, user_mentions):
        """
        Usage:
            {command_prefix}id [@user]

        Tells the user their id or the id of another user.
        """
        if not user_mentions:
            return Response(self.str.get('cmd-id-self', 'Your ID is `{0}`').format(author.id), reply=True, delete_after=35)
        else:
            usr = user_mentions[0]
            return Response(self.str.get('cmd-id-other', '**{0}**s ID is `{1}`').format(usr.name, usr.id), reply=True, delete_after=35)

    async def cmd_save(self, player):
        """
        Usage:
            {command_prefix}save

        Saves the current song to the autoplaylist.
        """
        if player.current_entry and not isinstance(player.current_entry, StreamPlaylistEntry):
            url = player.current_entry.url

            if url not in self.autoplaylist:
                self.autoplaylist.append(url)
                write_file(self.config.auto_playlist_file, self.autoplaylist)
                log.debug("Appended {} to autoplaylist".format(url))
                return Response(self.str.get('cmd-save-success', 'Added <{0}> to the autoplaylist.').format(url))
            else:
                raise exceptions.CommandError(self.str.get('cmd-save-exists', 'This song is already in the autoplaylist.'))
        else:
            raise exceptions.CommandError(self.str.get('cmd-save-invalid', 'There is no valid song playing.'))

    @owner_only
    async def cmd_joinserver(self, message, server_link=None):
        """
        Usage:
            {command_prefix}joinserver invite_link

        Asks the bot to join a server.  Note: Bot accounts cannot use invite links.
        """

        if self.user.bot:
            url = await self.generate_invite_link()
            return Response(
                self.str.get('cmd-joinserver-response', "Click here to add me to a server: \n{}").format(url),
                reply=True, delete_after=30
            )

    async def cmd_karaoke(self, player, channel, author):
        """
        Usage:
            {command_prefix}karaoke

        Activates karaoke mode. During karaoke mode, only groups with the BypassKaraokeMode
        permission in the config file can queue music.
        """
        player.karaoke_mode = not player.karaoke_mode
        return Response("\N{OK HAND SIGN} Karaoke mode is now " + ['disabled', 'enabled'][player.karaoke_mode], delete_after=15)

    async def _do_playlist_checks(self, permissions, player, author, testobj):
        num_songs = sum(1 for _ in testobj)

        # I have to do exe extra checks anyways because you can request an arbitrary number of search results
        if not permissions.allow_playlists and num_songs > 1:
            raise exceptions.PermissionsError(self.str.get('playlists-noperms', "You are not allowed to request playlists"), expire_in=30)

        if permissions.max_playlist_length and num_songs > permissions.max_playlist_length:
            raise exceptions.PermissionsError(
                self.str.get('playlists-big', "Playlist has too many entries ({0} > {1})").format(num_songs, permissions.max_playlist_length),
                expire_in=30
            )

        # This is a little bit weird when it says (x + 0 > y), I might add the other check back in
        if permissions.max_songs and player.playlist.count_for_user(author) + num_songs > permissions.max_songs:
            raise exceptions.PermissionsError(
                self.str.get('playlists-limit', "Playlist entries + your already queued songs reached limit ({0} + {1} > {2})").format(
                    num_songs, player.playlist.count_for_user(author), permissions.max_songs),
                expire_in=30
            )
        return True

    async def cmd_play(self, message, player, channel, author, permissions, leftover_args, song_url):
        """
        Usage:
            {command_prefix}play song_link
            {command_prefix}play text to search for
            {command_prefix}play spotify_uri

        Adds the song to the playlist.  If a link is not provided, the first
        result from a youtube search is added to the queue.

        If enabled in the config, the bot will also support Spotify URIs, however
        it will use the metadata (e.g song name and artist) to find a YouTube
        equivalent of the song. Streaming from Spotify is not possible.
        """

        song_url = song_url.strip('<>')

        await self.send_typing(channel)

        if leftover_args:
            song_url = ' '.join([song_url, *leftover_args])
        leftover_args = None  # prevent some crazy shit happening down the line

        # Make sure forward slashes work properly in search queries
        linksRegex = '((http(s)*:[/][/]|www.)([a-z]|[A-Z]|[0-9]|[/.]|[~])*)'
        pattern = re.compile(linksRegex)
        matchUrl = pattern.match(song_url)
        song_url = song_url.replace('/', '%2F') if matchUrl is None else song_url

        # Rewrite YouTube playlist URLs if the wrong URL type is given
        playlistRegex = r'watch\?v=.+&(list=[^&]+)'
        matches = re.search(playlistRegex, song_url)
        groups = matches.groups() if matches is not None else []
        song_url = "https://www.youtube.com/playlist?" + groups[0] if len(groups) > 0 else song_url

        if song_url.startswith('spotify:'):  # treat it as probably a spotify URI
            if self.config._spotify:
                song_url = song_url.split(":", 1)[1]
                try:

                    if song_url.startswith('track:'):
                        song_url = song_url.split(":", 1)[1]
                        res = await self.spotify.get_track(song_url)
                        song_url = res['artists'][0]['name'] + ' ' + res['name']  # spooky

                    elif song_url.startswith('album:'):
                        song_url = song_url.split(":", 1)[1]
                        res = await self.spotify.get_album(song_url)
                        await self._do_playlist_checks(permissions, player, author, res['tracks']['items'])
                        procmesg = await self.safe_send_message(channel, self.str.get('cmd-play-spotify-album-process', 'Processing album `{0}`').format(res['name']))
                        for i in res['tracks']['items']:
                            song_url = i['name'] + ' ' + i['artists'][0]['name']
                            log.debug('Processing {0}'.format(song_url))
                            await self.cmd_play(message, player, channel, author, permissions, leftover_args, song_url)
                        await self.safe_delete_message(procmesg)
                        return Response(self.str.get('cmd-play-spotify-album-queued', "Enqueued `{0}` with **{1}** songs.").format(res['name'], len(res['tracks']['items'])))

                    elif song_url.startswith('user:') and 'playlist:' in song_url:
                        user = song_url.split(":",)[1]
                        song_url = song_url.split(":", 3)[3]
                        res = await self.spotify.get_playlist(user, song_url)
                        await self._do_playlist_checks(permissions, player, author, res['tracks']['items'])
                        procmesg = await self.safe_send_message(channel, self.str.get('cmd-play-spotify-playlist-process', 'Processing playlist `{0}`').format(res['name']))
                        for i in res['tracks']['items']:
                            song_url = i['track']['name'] + ' ' + i['track']['artists'][0]['name']
                            log.debug('Processing {0}'.format(song_url))
                            await self.cmd_play(message, player, channel, author, permissions, leftover_args, song_url)
                        await self.safe_delete_message(procmesg)
                        return Response(self.str.get('cmd-play-spotify-playlist-queued', "Enqueued `{0}` with **{1}** songs.").format(res['name'], len(res['tracks']['items'])))

                    else:
                        raise exceptions.CommandError(self.str.get('cmd-play-spotify-unsupported', 'That is not a supported Spotify URI.'), expire_in=30)

                except exceptions.SpotifyError:
                    raise exceptions.CommandError(self.str.get('cmd-play-spotify-invalid', 'You either provided an invalid URI, or there was a problem.'))
            else:
                raise exceptions.CommandError(self.str.get('cmd-play-spotify-unavailable', 'The bot is not setup to support Spotify URIs. Check your config.'))

        async with self.aiolocks[_func_() + ':' + author.id]:
            if permissions.max_songs and player.playlist.count_for_user(author) >= permissions.max_songs:
                raise exceptions.PermissionsError(
                    self.str.get('cmd-play-limit', "You have reached your enqueued song limit ({0})").format(permissions.max_songs), expire_in=30
                )

            if player.karaoke_mode and not permissions.bypass_karaoke_mode:
                raise exceptions.PermissionsError(
                    self.str.get('karaoke-enabled', "Karaoke mode is enabled, please try again when its disabled!"), expire_in=30
                )

            try:
                info = await self.downloader.extract_info(player.playlist.loop, song_url, download=False, process=False)
            except Exception as e:
                if 'unknown url type' in str(e):
                    song_url = song_url.replace(':', '')  # it's probably not actually an extractor
                    info = await self.downloader.extract_info(player.playlist.loop, song_url, download=False, process=False)
                else:
                    raise exceptions.CommandError(e, expire_in=30)

            if not info:
                raise exceptions.CommandError(
                    self.str.get('cmd-play-noinfo', "That video cannot be played. Try using the {0}stream command.").format(self.config.command_prefix),
                    expire_in=30
                )

            log.debug(info)

            if info.get('extractor', '') not in permissions.extractors and permissions.extractors:
                raise exceptions.PermissionsError(
                    self.str.get('cmd-play-badextractor', "You do not have permission to play media from this service."), expire_in=30
                )

            # abstract the search handling away from the user
            # our ytdl options allow us to use search strings as input urls
            if info.get('url', '').startswith('ytsearch'):
                # print("[Command:play] Searching for \"%s\"" % song_url)
                info = await self.downloader.extract_info(
                    player.playlist.loop,
                    song_url,
                    download=False,
                    process=True,    # ASYNC LAMBDAS WHEN
                    on_error=lambda e: asyncio.ensure_future(
                        self.safe_send_message(channel, "```\n%s\n```" % e, expire_in=120), loop=self.loop),
                    retry_on_error=True
                )

                if not info:
                    raise exceptions.CommandError(
                        self.str.get('cmd-play-nodata', "Error extracting info from search string, youtubedl returned no data. "
                                                        "You may need to restart the bot if this continues to happen."), expire_in=30
                    )

                if not all(info.get('entries', [])):
                    # empty list, no data
                    log.debug("Got empty list, no data")
                    return

                # TODO: handle 'webpage_url' being 'ytsearch:...' or extractor type
                song_url = info['entries'][0]['webpage_url']
                info = await self.downloader.extract_info(player.playlist.loop, song_url, download=False, process=False)
                # Now I could just do: return await self.cmd_play(player, channel, author, song_url)
                # But this is probably fine

            # TODO: Possibly add another check here to see about things like the bandcamp issue
            # TODO: Where ytdl gets the generic extractor version with no processing, but finds two different urls

            if 'entries' in info:
                await self._do_playlist_checks(permissions, player, author, info['entries'])

                num_songs = sum(1 for _ in info['entries'])

                if info['extractor'].lower() in ['youtube:playlist', 'soundcloud:set', 'bandcamp:album']:
                    try:
                        return await self._cmd_play_playlist_async(player, channel, author, permissions, song_url, info['extractor'])
                    except exceptions.CommandError:
                        raise
                    except Exception as e:
                        log.error("Error queuing playlist", exc_info=True)
                        raise exceptions.CommandError(self.str.get('cmd-play-playlist-error', "Error queuing playlist:\n`{0}`").format(e), expire_in=30)

                t0 = time.time()

                # My test was 1.2 seconds per song, but we maybe should fudge it a bit, unless we can
                # monitor it and edit the message with the estimated time, but that's some ADVANCED SHIT
                # I don't think we can hook into it anyways, so this will have to do.
                # It would probably be a thread to check a few playlists and get the speed from that
                # Different playlists might download at different speeds though
                wait_per_song = 1.2

                procmesg = await self.safe_send_message(
                    channel,
                    self.str.get('cmd-play-playlist-gathering-1', 'Gathering playlist information for {0} songs{1}').format(
                        num_songs,
                        self.str.get('cmd-play-playlist-gathering-2', ', ETA: {0} seconds').format(fixg(
                            num_songs * wait_per_song)) if num_songs >= 10 else '.'))

                # We don't have a pretty way of doing this yet.  We need either a loop
                # that sends these every 10 seconds or a nice context manager.
                await self.send_typing(channel)

                # TODO: I can create an event emitter object instead, add event functions, and every play list might be asyncified
                #       Also have a "verify_entry" hook with the entry as an arg and returns the entry if its ok

                entry_list, position = await player.playlist.import_from(song_url, channel=channel, author=author)

                tnow = time.time()
                ttime = tnow - t0
                listlen = len(entry_list)
                drop_count = 0

                if permissions.max_song_length:
                    for e in entry_list.copy():
                        if e.duration > permissions.max_song_length:
                            player.playlist.entries.remove(e)
                            entry_list.remove(e)
                            drop_count += 1
                            # Im pretty sure there's no situation where this would ever break
                            # Unless the first entry starts being played, which would make this a race condition
                    if drop_count:
                        print("Dropped %s songs" % drop_count)

                log.info("Processed {} songs in {} seconds at {:.2f}s/song, {:+.2g}/song from expected ({}s)".format(
                    listlen,
                    fixg(ttime),
                    ttime / listlen if listlen else 0,
                    ttime / listlen - wait_per_song if listlen - wait_per_song else 0,
                    fixg(wait_per_song * num_songs))
                )

                await self.safe_delete_message(procmesg)

                if not listlen - drop_count:
                    raise exceptions.CommandError(
                        self.str.get('cmd-play-playlist-maxduration', "No songs were added, all songs were over max duration (%ss)") % permissions.max_song_length,
                        expire_in=30
                    )

                reply_text = self.str.get('cmd-play-playlist-reply', "Enqueued **%s** songs to be played. Position in queue: %s")
                btext = str(listlen - drop_count)

            else:
                if info.get('extractor', '').startswith('youtube:playlist'):
                    try:
                        info = await self.downloader.extract_info(player.playlist.loop, 'https://www.youtube.com/watch?v=%s' % info.get('url', ''), download=False, process=False)
                    except Exception as e:
                        raise exceptions.CommandError(e, expire_in=30)

                if permissions.max_song_length and info.get('duration', 0) > permissions.max_song_length:
                    raise exceptions.PermissionsError(
                        self.str.get('cmd-play-song-limit', "Song duration exceeds limit ({0} > {1})").format(info['duration'], permissions.max_song_length),
                        expire_in=30
                    )

                try:
                    entry, position = await player.playlist.add_entry(song_url, channel=channel, author=author)

                except exceptions.WrongEntryTypeError as e:
                    if e.use_url == song_url:
                        log.warning("Determined incorrect entry type, but suggested url is the same.  Help.")

                    log.debug("Assumed url \"%s\" was a single entry, was actually a playlist" % song_url)
                    log.debug("Using \"%s\" instead" % e.use_url)

                    return await self.cmd_play(player, channel, author, permissions, leftover_args, e.use_url)

                reply_text = self.str.get('cmd-play-song-reply', "Enqueued `%s` to be played. Position in queue: %s")
                btext = entry.title


            if position == 1 and player.is_stopped:
                position = self.str.get('cmd-play-next', 'Up next!')
                reply_text %= (btext, position)

            else:
                try:
                    time_until = await player.playlist.estimate_time_until(position, player)
                    reply_text += self.str.get('cmd-play-eta', ' - estimated time until playing: %s')
                except:
                    traceback.print_exc()
                    time_until = ''

                reply_text %= (btext, position, ftimedelta(time_until))

        return Response(reply_text, delete_after=30)

    async def _cmd_play_playlist_async(self, player, channel, author, permissions, playlist_url, extractor_type):
        """
        Secret handler to use the async wizardry to make playlist queuing non-"blocking"
        """

        await self.send_typing(channel)
        info = await self.downloader.extract_info(player.playlist.loop, playlist_url, download=False, process=False)

        if not info:
            raise exceptions.CommandError(self.str.get('cmd-play-playlist-invalid', "That playlist cannot be played."))

        num_songs = sum(1 for _ in info['entries'])
        t0 = time.time()

        busymsg = await self.safe_send_message(
            channel, self.str.get('cmd-play-playlist-process', "Processing {0} songs...").format(num_songs))  # TODO: From playlist_title
        await self.send_typing(channel)

        entries_added = 0
        if extractor_type == 'youtube:playlist':
            try:
                entries_added = await player.playlist.async_process_youtube_playlist(
                    playlist_url, channel=channel, author=author)
                # TODO: Add hook to be called after each song
                # TODO: Add permissions

            except Exception:
                log.error("Error processing playlist", exc_info=True)
                raise exceptions.CommandError(self.str.get('cmd-play-playlist-queueerror', 'Error handling playlist {0} queuing.').format(playlist_url), expire_in=30)

        elif extractor_type.lower() in ['soundcloud:set', 'bandcamp:album']:
            try:
                entries_added = await player.playlist.async_process_sc_bc_playlist(
                    playlist_url, channel=channel, author=author)
                # TODO: Add hook to be called after each song
                # TODO: Add permissions

            except Exception:
                log.error("Error processing playlist", exc_info=True)
                raise exceptions.CommandError(self.str.get('cmd-play-playlist-queueerror', 'Error handling playlist {0} queuing.').format(playlist_url), expire_in=30)


        songs_processed = len(entries_added)
        drop_count = 0
        skipped = False

        if permissions.max_song_length:
            for e in entries_added.copy():
                if e.duration > permissions.max_song_length:
                    try:
                        player.playlist.entries.remove(e)
                        entries_added.remove(e)
                        drop_count += 1
                    except:
                        pass

            if drop_count:
                log.debug("Dropped %s songs" % drop_count)

            if player.current_entry and player.current_entry.duration > permissions.max_song_length:
                await self.safe_delete_message(self.server_specific_data[channel.server]['last_np_msg'])
                self.server_specific_data[channel.server]['last_np_msg'] = None
                skipped = True
                player.skip()
                entries_added.pop()

        await self.safe_delete_message(busymsg)

        songs_added = len(entries_added)
        tnow = time.time()
        ttime = tnow - t0
        wait_per_song = 1.2
        # TODO: actually calculate wait per song in the process function and return that too

        # This is technically inaccurate since bad songs are ignored but still take up time
        log.info("Processed {}/{} songs in {} seconds at {:.2f}s/song, {:+.2g}/song from expected ({}s)".format(
            songs_processed,
            num_songs,
            fixg(ttime),
            ttime / num_songs if num_songs else 0,
            ttime / num_songs - wait_per_song if num_songs - wait_per_song else 0,
            fixg(wait_per_song * num_songs))
        )

        if not songs_added:
            basetext = self.str.get('cmd-play-playlist-maxduration', "No songs were added, all songs were over max duration (%ss)") % permissions.max_song_length
            if skipped:
                basetext += self.str.get('cmd-play-playlist-skipped', "\nAdditionally, the current song was skipped for being too long.")

            raise exceptions.CommandError(basetext, expire_in=30)

        return Response(self.str.get('cmd-play-playlist-reply-secs', "Enqueued {0} songs to be played in {1} seconds").format(
            songs_added, fixg(ttime, 1)), delete_after=30)

    async def cmd_stream(self, player, channel, author, permissions, song_url):
        """
        Usage:
            {command_prefix}stream song_link

        Enqueue a media stream.
        This could mean an actual stream like Twitch or shoutcast, or simply streaming
        media without predownloading it.  Note: FFmpeg is notoriously bad at handling
        streams, especially on poor connections.  You have been warned.
        """

        song_url = song_url.strip('<>')

        if permissions.max_songs and player.playlist.count_for_user(author) >= permissions.max_songs:
            raise exceptions.PermissionsError(
                self.str.get('cmd-stream-limit', "You have reached your enqueued song limit ({0})").format(permissions.max_songs), expire_in=30
            )

        if player.karaoke_mode and not permissions.bypass_karaoke_mode:
            raise exceptions.PermissionsError(
                self.str.get('karaoke-enabled', "Karaoke mode is enabled, please try again when its disabled!"), expire_in=30
            )

        await self.send_typing(channel)
        await player.playlist.add_stream_entry(song_url, channel=channel, author=author)

        return Response(self.str.get('cmd-stream-success', "Streaming."), delete_after=6)

    async def cmd_search(self, message, player, channel, author, permissions, leftover_args):
        """
        Usage:
            {command_prefix}search [service] [number] query

        Searches a service for a video and adds it to the queue.
        - service: any one of the following services:
            - youtube (yt) (default if unspecified)
            - soundcloud (sc)
            - yahoo (yh)
        - number: return a number of video results and waits for user to choose one
          - defaults to 3 if unspecified
          - note: If your search query starts with a number,
                  you must put your query in quotes
            - ex: {command_prefix}search 2 "I ran seagulls"
        The command issuer can use reactions to indicate their response to each result.
        """

        if permissions.max_songs and player.playlist.count_for_user(author) > permissions.max_songs:
            raise exceptions.PermissionsError(
                self.str.get('cmd-search-limit', "You have reached your playlist item limit ({0})").format(permissions.max_songs),
                expire_in=30
            )

        if player.karaoke_mode and not permissions.bypass_karaoke_mode:
            raise exceptions.PermissionsError(
                self.str.get('karaoke-enabled', "Karaoke mode is enabled, please try again when its disabled!"), expire_in=30
            )

        def argcheck():
            if not leftover_args:
                # noinspection PyUnresolvedReferences
                raise exceptions.CommandError(
                    self.str.get('cmd-search-noquery', "Please specify a search query.\n%s") % dedent(
                        self.cmd_search.__doc__.format(command_prefix=self.config.command_prefix)),
                    expire_in=60
                )

        argcheck()

        try:
            leftover_args = shlex.split(' '.join(leftover_args))
        except ValueError:
            raise exceptions.CommandError(self.str.get('cmd-search-noquote', "Please quote your search query properly."), expire_in=30)

        service = 'youtube'
        items_requested = 3
        max_items = 10  # this can be whatever, but since ytdl uses about 1000, a small number might be better
        services = {
            'youtube': 'ytsearch',
            'soundcloud': 'scsearch',
            'yahoo': 'yvsearch',
            'yt': 'ytsearch',
            'sc': 'scsearch',
            'yh': 'yvsearch'
        }

        if leftover_args[0] in services:
            service = leftover_args.pop(0)
            argcheck()

        if leftover_args[0].isdigit():
            items_requested = int(leftover_args.pop(0))
            argcheck()

            if items_requested > max_items:
                raise exceptions.CommandError(self.str.get('cmd-search-searchlimit', "You cannot search for more than %s videos") % max_items)

        # Look jake, if you see this and go "what the fuck are you doing"
        # and have a better idea on how to do this, i'd be delighted to know.
        # I don't want to just do ' '.join(leftover_args).strip("\"'")
        # Because that eats both quotes if they're there
        # where I only want to eat the outermost ones
        if leftover_args[0][0] in '\'"':
            lchar = leftover_args[0][0]
            leftover_args[0] = leftover_args[0].lstrip(lchar)
            leftover_args[-1] = leftover_args[-1].rstrip(lchar)

        search_query = '%s%s:%s' % (services[service], items_requested, ' '.join(leftover_args))

        search_msg = await self.send_message(channel, self.str.get('cmd-search-searching', "Searching for videos..."))
        await self.send_typing(channel)

        try:
            info = await self.downloader.extract_info(player.playlist.loop, search_query, download=False, process=True)

        except Exception as e:
            await self.safe_edit_message(search_msg, str(e), send_if_fail=True)
            return
        else:
            await self.safe_delete_message(search_msg)

        if not info:
            return Response(self.str.get('cmd-search-none', "No videos found."), delete_after=30)

        for e in info['entries']:
            result_message = await self.safe_send_message(channel, self.str.get('cmd-search-result', "Result {0}/{1}: {2}").format(
                info['entries'].index(e) + 1, len(info['entries']), e['webpage_url']))

            reactions = ['\u2705', '\U0001F6AB', '\U0001F3C1']
            for r in reactions:
                await self.add_reaction(result_message, r)
            res = await self.wait_for_reaction(reactions, user=author, timeout=30, message=result_message)

            if not res:
                await self.safe_delete_message(result_message)
                return

            if res.reaction.emoji == '\u2705':  # check
                await self.safe_delete_message(result_message)
                await self.cmd_play(message, player, channel, author, permissions, [], e['webpage_url'])
                return Response(self.str.get('cmd-search-accept', "Alright, coming right up!"), delete_after=30)
            elif res.reaction.emoji == '\U0001F6AB':  # cross
                await self.safe_delete_message(result_message)
                continue
            else:
                await self.safe_delete_message(result_message)
                break

        return Response(self.str.get('cmd-search-decline', "Oh well :("), delete_after=30)

    async def cmd_np(self, player, channel, server, message):
        """
        Usage:
            {command_prefix}np

        Displays the current song in chat.
        """

        if player.current_entry:
            if self.server_specific_data[server]['last_np_msg']:
                await self.safe_delete_message(self.server_specific_data[server]['last_np_msg'])
                self.server_specific_data[server]['last_np_msg'] = None

            # TODO: Fix timedelta garbage with util function
            song_progress = ftimedelta(timedelta(seconds=player.progress))
            song_total = ftimedelta(timedelta(seconds=player.current_entry.duration))

            streaming = isinstance(player.current_entry, StreamPlaylistEntry)
            prog_str = ('`[{progress}]`' if streaming else '`[{progress}/{total}]`').format(
                progress=song_progress, total=song_total
            )
            prog_bar_str = ''

            # percentage shows how much of the current song has already been played
            percentage = 0.0
            if player.current_entry.duration > 0:
                percentage = player.progress / player.current_entry.duration

            # create the actual bar
            progress_bar_length = 30
            for i in range(progress_bar_length):
                if (percentage < 1 / progress_bar_length * i):
                    prog_bar_str += '□'
                else:
                    prog_bar_str += '■'

            action_text = self.str.get('cmd-np-action-streaming', 'Streaming') if streaming else self.str.get('cmd-np-action-playing', 'Playing')
            thumbnail = player.current_entry.filename_thumbnail

            if player.current_entry.meta.get('channel', False) and player.current_entry.meta.get('author', False):
                np_text = self.str.get('cmd-np-reply-author', "Now {action}: **{title}** added by **{author}**\nProgress: {progress_bar} {progress}\n\N{WHITE RIGHT POINTING BACKHAND INDEX} <{url}>").format(
                    action=action_text,
                    title=player.current_entry.title,
                    author=player.current_entry.meta['author'].name,
                    progress_bar=prog_bar_str,
                    progress=prog_str,
                    url=player.current_entry.url
                )
            else:

                np_text = self.str.get('cmd-np-reply-noauthor', "Now {action}: **{title}**\nProgress: {progress_bar} {progress}\n\N{WHITE RIGHT POINTING BACKHAND INDEX} <{url}>").format(

                    action=action_text,
                    title=player.current_entry.title,
                    progress_bar=prog_bar_str,
                    progress=prog_str,
                    url=player.current_entry.url
                )

            if thumbnail:
                self.server_specific_data[server]['last_np_msg'] = await self.safe_send_file(channel, np_text, thumbnail)
            else:
                self.server_specific_data[server]['last_np_msg'] = await self.safe_send_message(channel, np_text)
                await self._manual_delete_check(message)
        else:
            return Response(
                self.str.get('cmd-np-none', 'There are no songs queued! Queue something with {0}play.') .format(self.config.command_prefix),
                delete_after=30
            )

    async def cmd_summon(self, channel, server, author, voice_channel):
        """
        Usage:
            {command_prefix}summon

        Call the bot to the summoner's voice channel.
        """

        if not author.voice_channel:
            raise exceptions.CommandError(self.str.get('cmd-summon-novc', 'You are not in a voice channel!'))

        voice_client = self.voice_client_in(server)
        if voice_client and server == author.voice_channel.server:
            await voice_client.move_to(author.voice_channel)
            return

        # move to _verify_vc_perms?
        chperms = author.voice_channel.permissions_for(server.me)

        if not chperms.connect:
            log.warning("Cannot join channel '{0}', no permission.".format(author.voice_channel.name))
            raise exceptions.CommandError(
                self.str.get('cmd-summon-noperms-connect', "Cannot join channel `{0}`, no permission to connect.").format(author.voice_channel.name),
                expire_in=25
            )

        elif not chperms.speak:
            log.warning("Cannot join channel '{0}', no permission to speak.".format(author.voice_channel.name))
            raise exceptions.CommandError(
                self.str.get('cmd-summon-noperms-speak', "Cannot join channel `{0}`, no permission to speak.").format(author.voice_channel.name),
                expire_in=25
            )

        log.info("Joining {0.server.name}/{0.name}".format(author.voice_channel))

        player = await self.get_player(author.voice_channel, create=True, deserialize=self.config.persistent_queue)

        if player.is_stopped:
            player.play()

        if self.config.auto_playlist:
            await self.on_player_finished_playing(player)

        return Response(self.str.get('cmd-summon-reply', 'Connected to `{0.name}`').format(author.voice_channel))

    async def cmd_pause(self, player):
        """
        Usage:
            {command_prefix}pause

        Pauses playback of the current song.
        """

        if player.is_playing:
            player.pause()
            return Response(self.str.get('cmd-pause-reply', 'Paused music in `{0.name}`').format(player.voice_client.channel))

        else:
            raise exceptions.CommandError(self.str.get('cmd-pause-none', 'Player is not playing.'), expire_in=30)

    async def cmd_resume(self, player):
        """
        Usage:
            {command_prefix}resume

        Resumes playback of a paused song.
        """

        if player.is_paused:
            player.resume()
            return Response(self.str.get('cmd-resume-reply', 'Resumed music in `{0.name}`').format(player.voice_client.channel), delete_after=15)

        else:
            raise exceptions.CommandError(self.str.get('cmd-resume-none', 'Player is not paused.'), expire_in=30)

    async def cmd_shuffle(self, channel, player):
        """
        Usage:
            {command_prefix}shuffle

        Shuffles the server's queue.
        """

        player.playlist.shuffle()

        cards = ['\N{BLACK SPADE SUIT}', '\N{BLACK CLUB SUIT}', '\N{BLACK HEART SUIT}', '\N{BLACK DIAMOND SUIT}']
        random.shuffle(cards)

        hand = await self.send_message(channel, ' '.join(cards))
        await asyncio.sleep(0.6)

        for x in range(4):
            random.shuffle(cards)
            await self.safe_edit_message(hand, ' '.join(cards))
            await asyncio.sleep(0.6)

        await self.safe_delete_message(hand, quiet=True)
        return Response(self.str.get('cmd-shuffle-reply', "Shuffled `{0}`'s queue.").format(player.voice_client.channel.server), delete_after=15)

    async def cmd_clear(self, player, author):
        """
        Usage:
            {command_prefix}clear

        Clears the playlist.
        """

        player.playlist.clear()
        return Response(self.str.get('cmd-clear-reply', "Cleared `{0}`'s queue").format(player.voice_client.channel.server), delete_after=20)

    async def cmd_remove(self, user_mentions, message, author, permissions, channel, player, index=None):
        """
        Usage:
            {command_prefix}remove [# in queue]

        Removes queued songs. If a number is specified, removes that song in the queue, otherwise removes the most recently queued song.
        """

        if not player.playlist.entries:
            raise exceptions.CommandError(self.str.get('cmd-remove-none', "There's nothing to remove!"), expire_in=20)

        if user_mentions:
            for user in user_mentions:
                if author.id == self.config.owner_id or permissions.remove or author == user:
                    try:
                        entry_indexes = [e for e in player.playlist.entries if e.meta.get('author', None) == user]
                        for entry in entry_indexes:
                            player.playlist.entries.remove(entry)
                        entry_text = '%s ' % len(entry_indexes) + 'item'
                        if len(entry_indexes) > 1:
                            entry_text += 's'
                        return Response(self.str.get('cmd-remove-reply', "Removed `{0}` added by `{1}`").format(entry_text, user.name).strip())

                    except ValueError:
                        raise exceptions.CommandError(self.str.get('cmd-remove-missing', "Nothing found in the queue from user `%s`") % user.name, expire_in=20)

                raise exceptions.PermissionsError(
                    self.str.get('cmd-remove-noperms', "You do not have the valid permissions to remove that entry from the queue, make sure you're the one who queued it or have instant skip permissions"), expire_in=20)

        if not index:
            index = len(player.playlist.entries)

        try:
            index = int(index)
        except (TypeError, ValueError):
            raise exceptions.CommandError(self.str.get('cmd-remove-invalid', "Invalid number. Use {}queue to find queue positions.").format(self.config.command_prefix), expire_in=20)

        if index > len(player.playlist.entries):
            raise exceptions.CommandError(self.str.get('cmd-remove-invalid', "Invalid number. Use {}queue to find queue positions.").format(self.config.command_prefix), expire_in=20)

        if author.id == self.config.owner_id or permissions.remove or author == player.playlist.get_entry_at_index(index - 1).meta.get('author', None):
            entry = player.playlist.delete_entry_at_index((index - 1))
            await self._manual_delete_check(message)
            if entry.meta.get('channel', False) and entry.meta.get('author', False):
                return Response(self.str.get('cmd-remove-reply-author', "Removed entry `{0}` added by `{1}`").format(entry.title, entry.meta['author'].name).strip())
            else:
                return Response(self.str.get('cmd-remove-reply-noauthor', "Removed entry `{0}`").format(entry.title).strip())
        else:
            raise exceptions.PermissionsError(
                self.str.get('cmd-remove-noperms', "You do not have the valid permissions to remove that entry from the queue, make sure you're the one who queued it or have instant skip permissions"), expire_in=20
            )

    async def cmd_skip(self, player, channel, author, message, permissions, voice_channel, param=''):
        """
        Usage:
            {command_prefix}skip [force/f]

        Skips the current song when enough votes are cast.
        Owners and those with the instaskip permission can add 'force' or 'f' after the command to force skip.
        """

        if player.is_stopped:
            raise exceptions.CommandError(self.str.get('cmd-skip-none', "Can't skip! The player is not playing!"), expire_in=20)

        if not player.current_entry:
            if player.playlist.peek():
                if player.playlist.peek()._is_downloading:
                    return Response(self.str.get('cmd-skip-dl', "The next song (`%s`) is downloading, please wait.") % player.playlist.peek().title)

                elif player.playlist.peek().is_downloaded:
                    print("The next song will be played shortly.  Please wait.")
                else:
                    print("Something odd is happening.  "
                          "You might want to restart the bot if it doesn't start working.")
            else:
                print("Something strange is happening.  "
                      "You might want to restart the bot if it doesn't start working.")

        if param.lower() in ['force', 'f']:
            if author.id == self.config.owner_id \
                or permissions.instaskip \
                    or (self.config.allow_author_skip and author == player.current_entry.meta.get('author', None)):

                player.skip()  # TODO: check autopause stuff here
                await self._manual_delete_check(message)
                return Response(self.str.get('cmd-skip-force', 'Force skipped `{}`.').format(player.current_entry.title), reply=True, delete_after=30)
            else:
                raise exceptions.PermissionsError(self.str.get('cmd-skip-force-noperms', 'You do not have permission to force skip.'), expire_in=30)

        # TODO: ignore person if they're deaf or take them out of the list or something?
        # Currently is recounted if they vote, deafen, then vote

        num_voice = sum(1 for m in voice_channel.voice_members if not (
            m.deaf or m.self_deaf or m == self.user))

        num_skips = player.skip_state.add_skipper(author.id, message)

        skips_remaining = min(
            self.config.skips_required,
            math.ceil(self.config.skip_ratio_required / (1 / num_voice))  # Number of skips from config ratio
        ) - num_skips

        if skips_remaining <= 0:
            player.skip()  # check autopause stuff here
            return Response(
                self.str.get('cmd-skip-reply-skipped-1', 'Your skip for `{0}` was acknowledged.\nThe vote to skip has been passed.{1}').format(
                    player.current_entry.title,
                    self.str.get('cmd-skip-reply-skipped-2', ' Next song coming up!') if player.playlist.peek() else ''
                ),
                reply=True,
                delete_after=20
            )

        else:
            # TODO: When a song gets skipped, delete the old x needed to skip messages
            return Response(
                self.str.get('cmd-skip-reply-voted-1', 'Your skip for `{0}` was acknowledged.\n**{1}** more {2} required to vote to skip this song.').format(
                    player.current_entry.title,
                    skips_remaining,
                    self.str.get('cmd-skip-reply-voted-2', 'person is') if skips_remaining == 1 else self.str.get('cmd-skip-reply-voted-3', 'people are')
                ),
                reply=True,
                delete_after=20
            )

    async def cmd_volume(self, message, player, new_volume=None):
        """
        Usage:
            {command_prefix}volume (+/-)[volume]

        Sets the playback volume. Accepted values are from 1 to 100.
        Putting + or - before the volume will make the volume change relative to the current volume.
        """

        if not new_volume:
            return Response(self.str.get('cmd-volume-current', 'Current volume: `%s%%`') % int(player.volume * 100), reply=True, delete_after=20)

        relative = False
        if new_volume[0] in '+-':
            relative = True

        try:
            new_volume = int(new_volume)

        except ValueError:
            raise exceptions.CommandError(self.str.get('cmd-volume-invalid', '`{0}` is not a valid number').format(new_volume), expire_in=20)

        vol_change = None
        if relative:
            vol_change = new_volume
            new_volume += (player.volume * 100)

        old_volume = int(player.volume * 100)

        if 0 < new_volume <= 100:
            player.volume = new_volume / 100.0

            return Response(self.str.get('cmd-volume-reply', 'Updated volume from **%d** to **%d**') % (old_volume, new_volume), reply=True, delete_after=20)

        else:
            if relative:
                raise exceptions.CommandError(
                    self.str.get('cmd-volume-unreasonable-relative', 'Unreasonable volume change provided: {}{:+} -> {}%.  Provide a change between {} and {:+}.').format(
                        old_volume, vol_change, old_volume + vol_change, 1 - old_volume, 100 - old_volume), expire_in=20)
            else:
                raise exceptions.CommandError(
                    self.str.get('cmd-volume-unreasonable-absolute', 'Unreasonable volume provided: {}%. Provide a value between 1 and 100.').format(new_volume), expire_in=20)

    @owner_only
    async def cmd_option(self, player, option, value):
        """
        Usage:
            {command_prefix}option [option] [on/y/enabled/off/n/disabled]

        Changes a config option without restarting the bot. Changes aren't permanent and
        only last until the bot is restarted. To make permanent changes, edit the
        config file.

        Valid options:
            autoplaylist, save_videos, now_playing_mentions, auto_playlist_random, auto_pause,
            delete_messages, delete_invoking, write_current_song

        For information about these options, see the option's comment in the config file.
        """

        option = option.lower()
        value = value.lower()
        bool_y = ['on', 'y', 'enabled']
        bool_n = ['off', 'n', 'disabled']
        generic = ['save_videos', 'now_playing_mentions', 'auto_playlist_random',
                   'auto_pause', 'delete_messages', 'delete_invoking',
                   'write_current_song']  # these need to match attribute names in the Config class
        if option in ['autoplaylist', 'auto_playlist']:
            if value in bool_y:
                if self.config.auto_playlist:
                    raise exceptions.CommandError(self.str.get('cmd-option-autoplaylist-enabled', 'The autoplaylist is already enabled!'))
                else:
                    if not self.autoplaylist:
                        raise exceptions.CommandError(self.str.get('cmd-option-autoplaylist-none', 'There are no entries in the autoplaylist file.'))
                    self.config.auto_playlist = True
                    await self.on_player_finished_playing(player)
            elif value in bool_n:
                if not self.config.auto_playlist:
                    raise exceptions.CommandError(self.str.get('cmd-option-autoplaylist-disabled', 'The autoplaylist is already disabled!'))
                else:
                    self.config.auto_playlist = False
            else:
                raise exceptions.CommandError(self.str.get('cmd-option-invalid-value', 'The value provided was not valid.'))
            return Response("The autoplaylist is now " + ['disabled', 'enabled'][self.config.auto_playlist] + '.')
        else:
            is_generic = [o for o in generic if o == option]  # check if it is a generic bool option
            if is_generic and (value in bool_y or value in bool_n):
                name = is_generic[0]
                log.debug('Setting attribute {0}'.format(name))
                setattr(self.config, name, True if value in bool_y else False)  # this is scary but should work
                attr = getattr(self.config, name)
                res = "The option {0} is now ".format(option) + ['disabled', 'enabled'][attr] + '.'
                log.warning('Option overriden for this session: {0}'.format(res))
                return Response(res)
            else:
                raise exceptions.CommandError(self.str.get('cmd-option-invalid-param' ,'The parameters provided were invalid.'))

    async def cmd_queue(self, channel, player):
        """
        Usage:
            {command_prefix}queue

        Prints the current song queue.
        """

        lines = []
        unlisted = 0
        andmoretext = '* ... and %s more*' % ('x' * len(player.playlist.entries))

        if player.current_entry:
            # TODO: Fix timedelta garbage with util function
            song_progress = ftimedelta(timedelta(seconds=player.progress))
            song_total = ftimedelta(timedelta(seconds=player.current_entry.duration))
            prog_str = '`[%s/%s]`' % (song_progress, song_total)

            if player.current_entry.meta.get('channel', False) and player.current_entry.meta.get('author', False):
                lines.append(self.str.get('cmd-queue-playing-author', "Currently playing: `{0}` added by `{1}` {2}\n").format(
                    player.current_entry.title, player.current_entry.meta['author'].name, prog_str))
            else:
                lines.append(self.str.get('cmd-queue-playing-noauthor', "Currently playing: `{0}` {1}\n").format(player.current_entry.title, prog_str))


        for i, item in enumerate(player.playlist, 1):
            if item.meta.get('channel', False) and item.meta.get('author', False):
                nextline = self.str.get('cmd-queue-entry-author', '{0} -- `{1}` by `{2}`').format(i, item.title, item.meta['author'].name).strip()
            else:
                nextline = self.str.get('cmd-queue-entry-noauthor', '{0} -- `{1}`').format(i, item.title).strip()

            currentlinesum = sum(len(x) + 1 for x in lines)  # +1 is for newline char

            if (currentlinesum + len(nextline) + len(andmoretext) > DISCORD_MSG_CHAR_LIMIT) or (i > self.config.queue_length):
                if currentlinesum + len(andmoretext):
                    unlisted += 1
                    continue

            lines.append(nextline)

        if unlisted:
            lines.append(self.str.get('cmd-queue-more', '\n... and %s more') % unlisted)

        if not lines:
            lines.append(
                self.str.get('cmd-queue-none', 'There are no songs queued! Queue something with {}play.').format(self.config.command_prefix))

        message = '\n'.join(lines)
        return Response(message, delete_after=30)

    async def cmd_clean(self, message, channel, server, author, search_range=50):
        """
        Usage:
            {command_prefix}clean [range]

        Removes up to [range] messages the bot has posted in chat. Default: 50, Max: 1000
        """

        try:
            float(search_range)  # lazy check
            search_range = min(int(search_range), 1000)
        except:
            return Response(self.str.get('cmd-clean-invalid', "Invalid parameter. Please provide a number of messages to search."), reply=True, delete_after=8)

        await self.safe_delete_message(message, quiet=True)

        def is_possible_command_invoke(entry):
            valid_call = any(
                entry.content.startswith(prefix) for prefix in [self.config.command_prefix])  # can be expanded
            return valid_call and not entry.content[1:2].isspace()

        delete_invokes = True
        delete_all = channel.permissions_for(author).manage_messages or self.config.owner_id == author.id

        def check(message):
            if is_possible_command_invoke(message) and delete_invokes:
                return delete_all or message.author == author
            return message.author == self.user

        if self.user.bot:
            if channel.permissions_for(server.me).manage_messages:
                deleted = await self.purge_from(channel, check=check, limit=search_range, before=message)
                return Response(self.str.get('cmd-clean-reply', 'Cleaned up {0} message{1}.').format(len(deleted), 's' * bool(deleted)), delete_after=15)

    async def cmd_pldump(self, channel, song_url):
        """
        Usage:
            {command_prefix}pldump url

        Dumps the individual urls of a playlist
        """

        try:
            info = await self.downloader.extract_info(self.loop, song_url.strip('<>'), download=False, process=False)
        except Exception as e:
            raise exceptions.CommandError("Could not extract info from input url\n%s\n" % e, expire_in=25)

        if not info:
            raise exceptions.CommandError("Could not extract info from input url, no data.", expire_in=25)

        if not info.get('entries', None):
            # TODO: Retarded playlist checking
            # set(url, webpageurl).difference(set(url))

            if info.get('url', None) != info.get('webpage_url', info.get('url', None)):
                raise exceptions.CommandError("This does not seem to be a playlist.", expire_in=25)
            else:
                return await self.cmd_pldump(channel, info.get(''))

        linegens = defaultdict(lambda: None, **{
            "youtube":    lambda d: 'https://www.youtube.com/watch?v=%s' % d['id'],
            "soundcloud": lambda d: d['url'],
            "bandcamp":   lambda d: d['url']
        })

        exfunc = linegens[info['extractor'].split(':')[0]]

        if not exfunc:
            raise exceptions.CommandError("Could not extract info from input url, unsupported playlist type.", expire_in=25)

        with BytesIO() as fcontent:
            for item in info['entries']:
                fcontent.write(exfunc(item).encode('utf8') + b'\n')

            fcontent.seek(0)
            await self.send_file(channel, fcontent, filename='playlist.txt', content="Here's the url dump for <%s>" % song_url)

        return Response("Sent a message with a playlist file.", delete_after=20)

    async def cmd_listids(self, server, author, leftover_args, cat='all'):
        """
        Usage:
            {command_prefix}listids [categories]

        Lists the ids for various things.  Categories are:
           all, users, roles, channels
        """

        cats = ['channels', 'roles', 'users']

        if cat not in cats and cat != 'all':
            return Response(
                "Valid categories: " + ' '.join(['`%s`' % c for c in cats]),
                reply=True,
                delete_after=25
            )

        if cat == 'all':
            requested_cats = cats
        else:
            requested_cats = [cat] + [c.strip(',') for c in leftover_args]

        data = ['Your ID: %s' % author.id]

        for cur_cat in requested_cats:
            rawudata = None

            if cur_cat == 'users':
                data.append("\nUser IDs:")
                rawudata = ['%s #%s: %s' % (m.name, m.discriminator, m.id) for m in server.members]

            elif cur_cat == 'roles':
                data.append("\nRole IDs:")
                rawudata = ['%s: %s' % (r.name, r.id) for r in server.roles]

            elif cur_cat == 'channels':
                data.append("\nText Channel IDs:")
                tchans = [c for c in server.channels if c.type == discord.ChannelType.text]
                rawudata = ['%s: %s' % (c.name, c.id) for c in tchans]

                rawudata.append("\nVoice Channel IDs:")
                vchans = [c for c in server.channels if c.type == discord.ChannelType.voice]
                rawudata.extend('%s: %s' % (c.name, c.id) for c in vchans)

            if rawudata:
                data.extend(rawudata)

        with BytesIO() as sdata:
            sdata.writelines(d.encode('utf8') + b'\n' for d in data)
            sdata.seek(0)

            # TODO: Fix naming (Discord20API-ids.txt)
            await self.send_file(author, sdata, filename='%s-ids-%s.txt' % (server.name.replace(' ', '_'), cat))

        return Response("Sent a message with a list of IDs.", delete_after=20)


    async def cmd_perms(self, author, user_mentions, channel, server, permissions):
        """
        Usage:
            {command_prefix}perms [@user]

        Sends the user a list of their permissions, or the permissions of the user specified.
        """

        lines = ['Command permissions in %s\n' % server.name, '```', '```']

        if user_mentions:
            user = user_mentions[0]
            permissions = self.permissions.for_user(user)

        for perm in permissions.__dict__:
            if perm in ['user_list'] or permissions.__dict__[perm] == set():
                continue

            lines.insert(len(lines) - 1, "%s: %s" % (perm, permissions.__dict__[perm]))

        await self.safe_send_message(author, '\n'.join(lines))
        return Response("\N{OPEN MAILBOX WITH RAISED FLAG}", delete_after=20)


    @owner_only
    async def cmd_setname(self, leftover_args, name):
        """
        Usage:
            {command_prefix}setname name

        Changes the bot's username.
        Note: This operation is limited by discord to twice per hour.
        """

        name = ' '.join([name, *leftover_args])

        try:
            await self.edit_profile(username=name)

        except discord.HTTPException:
            raise exceptions.CommandError(
                "Failed to change name. Did you change names too many times?  "
                "Remember name changes are limited to twice per hour.")

        except Exception as e:
            raise exceptions.CommandError(e, expire_in=20)

        return Response("Set the bot's username to **{0}**".format(name), delete_after=20)

    async def cmd_setnick(self, server, channel, leftover_args, nick):
        """
        Usage:
            {command_prefix}setnick nick

        Changes the bot's nickname.
        """

        if not channel.permissions_for(server.me).change_nickname:
            raise exceptions.CommandError("Unable to change nickname: no permission.")

        nick = ' '.join([nick, *leftover_args])

        try:
            await self.change_nickname(server.me, nick)
        except Exception as e:
            raise exceptions.CommandError(e, expire_in=20)

        return Response("Set the bot's nickname to `{0}`".format(nick), delete_after=20)

    @owner_only
    async def cmd_setavatar(self, message, url=None):
        """
        Usage:
            {command_prefix}setavatar [url]

        Changes the bot's avatar.
        Attaching a file and leaving the url parameter blank also works.
        """

        if message.attachments:
            thing = message.attachments[0]['url']
        elif url:
            thing = url.strip('<>')
        else:
            raise exceptions.CommandError("You must provide a URL or attach a file.", expire_in=20)

        try:
            with aiohttp.Timeout(10):
                async with self.aiosession.get(thing) as res:
                    await self.edit_profile(avatar=await res.read())

        except Exception as e:
            raise exceptions.CommandError("Unable to change avatar: {}".format(e), expire_in=20)

        return Response("Changed the bot's avatar.", delete_after=20)


    async def cmd_disconnect(self, server):
        await self.disconnect_voice_client(server)
        return Response("Disconnected from `{0.name}`".format(server), delete_after=20)

    async def cmd_restart(self, channel):
        await self.safe_send_message(channel, "\N{WAVING HAND SIGN} Restarting. If you have updated your bot "
            "or its dependencies, you need to restart the bot properly, rather than using this command.")

        player = self.get_player_in(channel.server)
        if player and player.is_paused:
            player.resume()

        await self.disconnect_all_voice_clients()
        raise exceptions.RestartSignal()

    async def cmd_shutdown(self, channel):
        await self.safe_send_message(channel, "\N{WAVING HAND SIGN}")
        
        player = self.get_player_in(channel.server)
        if player and player.is_paused:
            player.resume()
        
        await self.disconnect_all_voice_clients()
        raise exceptions.TerminateSignal()

    async def cmd_leaveserver(self, val, leftover_args):
        """
        Usage:
            {command_prefix}leaveserver <name/ID>

        Forces the bot to leave a server.
        When providing names, names are case-sensitive.
        """
        if leftover_args:
            val = ' '.join([val, *leftover_args])

        t = self.get_server(val)
        if t is None:
            t = discord.utils.get(self.servers, name=val)
            if t is None:
                raise exceptions.CommandError('No server was found with the ID or name as `{0}`'.format(val))
        await self.leave_server(t)
        return Response('Left the server: `{0.name}` (Owner: `{0.owner.name}`, ID: `{0.id}`)'.format(t))

    @dev_only
    async def cmd_breakpoint(self, message):
        log.critical("Activating debug breakpoint")
        return

    @dev_only
    async def cmd_objgraph(self, channel, func='most_common_types()'):
        import objgraph

        await self.send_typing(channel)

        if func == 'growth':
            f = StringIO()
            objgraph.show_growth(limit=10, file=f)
            f.seek(0)
            data = f.read()
            f.close()

        elif func == 'leaks':
            f = StringIO()
            objgraph.show_most_common_types(objects=objgraph.get_leaking_objects(), file=f)
            f.seek(0)
            data = f.read()
            f.close()

        elif func == 'leakstats':
            data = objgraph.typestats(objects=objgraph.get_leaking_objects())

        else:
            data = eval('objgraph.' + func)

        return Response(data, codeblock='py')

    @dev_only
    async def cmd_debug(self, message, _player, *, data):
        codeblock = "```py\n{}\n```"
        result = None

        if data.startswith('```') and data.endswith('```'):
            data = '\n'.join(data.rstrip('`\n').split('\n')[1:])

        code = data.strip('` \n')

        try:
            result = eval(code)
        except:
            try:
                exec(code)
            except Exception as e:
                traceback.print_exc(chain=False)
                return Response("{}: {}".format(type(e).__name__, e))

        if asyncio.iscoroutine(result):
            result = await result

        return Response(codeblock.format(result))

    async def on_message(self, message):
        await self.wait_until_ready()
        self.message_count += 1

        message_content = message.content.strip()

        if "281807963147075584" in message.raw_mentions and message.author != self.user:  
            parsedmessage = re.sub('<@!?\d{18}>', '', message_content).strip()
            msg = ["Hello!", "Hiya!", "Hi <3", "Did someone say my name?", "That's my name!", "You called for me?", "What's up, %s?" % message.author.mention, "Boo.", "Hi there, %s. Need me to kill anyone?" % message.author.mention]
            botsay = random.choice(msg)

            await self.safe_send_message(message.channel, botsay)

        if not message_content.startswith(self.config.command_prefix):
            return

        # Rearranged the condition checks to first split the command into the command and arguments, then check if command is in bound option
        command, *args = message_content.split(' ')  # Uh, doesn't this break prefixes with spaces in them (it doesn't, config parser already breaks them)
        command = command[len(self.config.command_prefix):].lower().strip()

        if self.config.bound_channels and message.channel.id not in self.config.bound_channels and not message.channel.is_private and command in self.config.bound_commands:
            return  # if I want to log this I just move it under the prefix check
        
        # log.info(message.author.voice_channel.id)
        # log.info(self.voice_client.server.channel.id)
        # if message.author.voice_channel.id and command in self.config.bound_commands and message.author.voice_channel.id not in self.
        #    return  
        # Experimental reimplementation of preventing commands from working unless you are in the VC

        if message.author == self.user:
            log.warning("Ignoring command from myself ({})".format(message.content))
            return

        command, *args = message_content.split(' ')  # Uh, doesn't this break prefixes with spaces in them (it doesn't, config parser already breaks them)
        command = command[len(self.config.command_prefix):].lower().strip()

        handler = getattr(self, 'cmd_' + command, None)
        if not handler:
            return

        if message.channel.is_private:
            if not (message.author.id == self.config.owner_id and command == 'joinserver'):
                await self.send_message(message.channel, 'You cannot use this bot in private messages.')
                return

        if message.author.id in self.blacklist and message.author.id != self.config.owner_id:
            log.warning("User blacklisted: {0.id}/{0!s} ({1})".format(message.author, command))
            return

        else:
            log.info("{0.id}/{0!s}: {1}".format(message.author, message_content.replace('\n', '\n... ')))

        user_permissions = self.permissions.for_user(message.author)

        argspec = inspect.signature(handler)
        params = argspec.parameters.copy()

        sentmsg = response = None

        # noinspection PyBroadException
        try:
            if user_permissions.ignore_non_voice and command in user_permissions.ignore_non_voice:
                await self._check_ignore_non_voice(message)

            handler_kwargs = {}
            if params.pop('message', None):
                handler_kwargs['message'] = message

            if params.pop('channel', None):
                handler_kwargs['channel'] = message.channel

            if params.pop('author', None):
                handler_kwargs['author'] = message.author

            if params.pop('server', None):
                handler_kwargs['server'] = message.server

            if params.pop('player', None):
                handler_kwargs['player'] = await self.get_player(message.channel)

            if params.pop('_player', None):
                handler_kwargs['_player'] = self.get_player_in(message.server)

            if params.pop('permissions', None):
                handler_kwargs['permissions'] = user_permissions

            if params.pop('user_mentions', None):
                handler_kwargs['user_mentions'] = list(map(message.server.get_member, message.raw_mentions))

            if params.pop('channel_mentions', None):
                handler_kwargs['channel_mentions'] = list(map(message.server.get_channel, message.raw_channel_mentions))

            if params.pop('voice_channel', None):
                handler_kwargs['voice_channel'] = message.server.me.voice_channel

            if params.pop('leftover_args', None):
                handler_kwargs['leftover_args'] = args

            args_expected = []
            for key, param in list(params.items()):

                # parse (*args) as a list of args
                if param.kind == param.VAR_POSITIONAL:
                    handler_kwargs[key] = args
                    params.pop(key)
                    continue

                # parse (*, args) as args rejoined as a string
                # multiple of these arguments will have the same value
                if param.kind == param.KEYWORD_ONLY and param.default == param.empty:
                    handler_kwargs[key] = ' '.join(args)
                    params.pop(key)
                    continue

                doc_key = '[{}={}]'.format(key, param.default) if param.default is not param.empty else key
                args_expected.append(doc_key)

                # Ignore keyword args with default values when the command had no arguments
                if not args and param.default is not param.empty:
                    params.pop(key)
                    continue

                # Assign given values to positional arguments
                if args:
                    arg_value = args.pop(0)
                    handler_kwargs[key] = arg_value
                    params.pop(key)

            if message.author.id != self.config.owner_id:
                if user_permissions.command_whitelist and command not in user_permissions.command_whitelist:
                    raise exceptions.PermissionsError(
                        "This command is not enabled for your group ({}).".format(user_permissions.name),
                        expire_in=20)

                elif user_permissions.command_blacklist and command in user_permissions.command_blacklist:
                    raise exceptions.PermissionsError(
                        "This command is disabled for your group ({}).".format(user_permissions.name),
                        expire_in=20)

            # Invalid usage, return docstring
            if params:
                docs = getattr(handler, '__doc__', None)
                if not docs:
                    docs = 'Usage: {}{} {}'.format(
                        self.config.command_prefix,
                        command,
                        ' '.join(args_expected)
                    )

                docs = dedent(docs)
                await self.safe_send_message(
                    message.channel,
                    '```\n{}\n```'.format(docs.format(command_prefix=self.config.command_prefix)),
                    expire_in=60
                )
                return

            response = await handler(**handler_kwargs)
            if response and isinstance(response, Response):
                if not isinstance(response.content, discord.Embed) and self.config.embeds:
                    content = self._gen_embed()
                    content.title = command
                    content.description = response.content
                else:
                    content = response.content

                if response.reply:
                    if isinstance(content, discord.Embed):
                        content.description = '{} {}'.format(message.author.mention, content.description if content.description is not discord.Embed.Empty else '')
                    else:
                        content = '{}: {}'.format(message.author.mention, content)

                sentmsg = await self.safe_send_message(
                    message.channel, content,
                    expire_in=response.delete_after if self.config.delete_messages and command not in self.config.retain_commands else 0,
                    also_delete=message if self.config.delete_invoking and command not in self.config.retain_commands else None
                )

        except (exceptions.CommandError, exceptions.HelpfulError, exceptions.ExtractionError) as e:
            log.error("Error in {0}: {1.__class__.__name__}: {1.message}".format(command, e), exc_info=True)

            expirein = e.expire_in if self.config.delete_messages else None
            alsodelete = message if self.config.delete_invoking else None

            if self.config.embeds:
                content = self._gen_embed()
                content.add_field(name='Error', value=e.message, inline=False)
                content.colour = 13369344
            else:
                content = '```\n{}\n```'.format(e.message)

            await self.safe_send_message(
                message.channel,
                content,
                expire_in=expirein,
                also_delete=alsodelete
            )

        except exceptions.Signal:
            raise

        except Exception:
            log.error("Exception in on_message", exc_info=True)
            if self.config.debug_mode:
                await self.safe_send_message(message.channel, '```\n{}\n```'.format(traceback.format_exc()))

        finally:
            if not sentmsg and not response and self.config.delete_invoking:
                await asyncio.sleep(5)
                await self.safe_delete_message(message, quiet=True)

    async def gen_cmd_list(self, message, list_all_cmds=False):
        for att in dir(self):
            # This will always return at least cmd_help, since they needed perms to run this command
            if att.startswith('cmd_') and not hasattr(getattr(self, att), 'dev_cmd'):
                user_permissions = self.permissions.for_user(message.author)
                command_name = att.replace('cmd_', '').lower()
                whitelist = user_permissions.command_whitelist
                blacklist = user_permissions.command_blacklist
                if list_all_cmds:
                    self.commands.append('{}{}'.format(self.config.command_prefix, command_name))

                elif blacklist and command_name in blacklist:
                    pass

                elif whitelist and command_name not in whitelist:
                    pass

                else:
                    self.commands.append("{}{}".format(self.config.command_prefix, command_name))

    async def on_voice_state_update(self, before, after):
        if not self.init_ok:
            return # Ignore stuff before ready

        state = VoiceStateUpdate(before, after)

        if state.broken:
            log.voicedebug("Broken voice state update")
            return

        if state.resuming:
            log.debug("Resumed voice connection to {0.server.name}/{0.name}".format(state.voice_channel))

        if not state.changes:
            log.voicedebug("Empty voice state update, likely a session id change")
            return # Session id change, pointless event

        ################################

        log.voicedebug("Voice state update for {mem.id}/{mem!s} on {ser.name}/{vch.name} -> {dif}".format(
            mem = state.member,
            ser = state.server,
            vch = state.voice_channel,
            dif = state.changes
        ))

        if not state.is_about_my_voice_channel:
            return # Irrelevant channel

        if state.joining or state.leaving:
            log.info("{0.id}/{0!s} has {1} {2}/{3}".format(
                state.member,
                'joined' if state.joining else 'left',
                state.server,
                state.my_voice_channel
            ))

        if not self.config.auto_pause:
            return

        autopause_msg = "{state} in {channel.server.name}/{channel.name} {reason}"

        auto_paused = self.server_specific_data[after.server]['auto_paused']
        player = await self.get_player(state.my_voice_channel)

        if state.joining and state.empty() and player.is_playing:
            log.info(autopause_msg.format(
                state = "Pausing",
                channel = state.my_voice_channel,
                reason = "(joining empty channel)"
            ).strip())

            self.server_specific_data[after.server]['auto_paused'] = True
            player.pause()
            return

        if not state.is_about_me:
            if not state.empty(old_channel=state.leaving):
                if auto_paused and player.is_paused:
                    log.info(autopause_msg.format(
                        state = "Unpausing",
                        channel = state.my_voice_channel,
                        reason = ""
                    ).strip())

                    self.server_specific_data[after.server]['auto_paused'] = False
                    player.resume()
            else:
                if not auto_paused and player.is_playing:
                    log.info(autopause_msg.format(
                        state = "Pausing",
                        channel = state.my_voice_channel,
                        reason = "(empty channel)"
                    ).strip())

                    self.server_specific_data[after.server]['auto_paused'] = True
                    player.pause()
        else: 
            if not state.empty():
                if auto_paused and player.is_paused:
                    log.info(autopause_msg.format(
                        state = "Unpausing",
                        channel = state.my_voice_channel,
                        reason = ""
                    ).strip())
 
                    self.server_specific_data[after.server]['auto_paused'] = False
                    player.resume()

    async def on_server_update(self, before:discord.Server, after:discord.Server):
        if before.region != after.region:
            log.warning("Server \"%s\" changed regions: %s -> %s" % (after.name, before.region, after.region))

            await self.reconnect_voice_client(after)


    async def on_server_join(self, server:discord.Server):
        log.info("Bot has been joined server: {}".format(server.name))

        if not self.user.bot:
            alertmsg = "<@{uid}> Hi I'm a musicbot please mute me."

            if server.id == "81384788765712384" and not server.unavailable: # Discord API
                playground = server.get_channel("94831883505905664") or discord.utils.get(server.channels, name='playground') or server
                await self.safe_send_message(playground, alertmsg.format(uid="98295630480314368")) # fake abal

            elif server.id == "129489631539494912" and not server.unavailable: # Rhino Bot Help
                bot_testing = server.get_channel("134771894292316160") or discord.utils.get(server.channels, name='bot-testing') or server
                await self.safe_send_message(bot_testing, alertmsg.format(uid="98295630480314368")) # also fake abal

        log.debug("Creating data folder for server %s", server.id)
        pathlib.Path('data/%s/' % server.id).mkdir(exist_ok=True)

    async def on_server_remove(self, server: discord.Server):
        log.info("Bot has been removed from server: {}".format(server.name))
        log.debug('Updated server list:')
        [log.debug(' - ' + s.name) for s in self.servers]

        if server.id in self.players:
            self.players.pop(server.id).kill()


    async def on_server_available(self, server: discord.Server):
        if not self.init_ok:
            return # Ignore pre-ready events

        log.debug("Server \"{}\" has become available.".format(server.name))

        player = self.get_player_in(server)

        if player and player.is_paused:
            av_paused = self.server_specific_data[server]['availability_paused']

            if av_paused:
                log.debug("Resuming player in \"{}\" due to availability.".format(server.name))
                self.server_specific_data[server]['availability_paused'] = False
                player.resume()


    async def on_server_unavailable(self, server: discord.Server):
        log.debug("Server \"{}\" has become unavailable.".format(server.name))

        player = self.get_player_in(server)

        if player and player.is_playing:
            log.debug("Pausing player in \"{}\" due to unavailability.".format(server.name))
            self.server_specific_data[server]['availability_paused'] = True
            player.pause()
