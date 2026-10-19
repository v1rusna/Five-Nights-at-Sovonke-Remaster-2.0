# audio.rpy
init -5 python in v1FNaSR:
    import threading as _threading

    class AudioManager(object):
        __slots__ = ("_channels", "_last_played", "_lock", "_default_channel",)

        def __init__(self, default_channel="music"):
            self._channels = dict()
            self._last_played = dict()
            self._lock = _threading.RLock()

            self._default_channel = self._normalize_name(default_channel)

        @staticmethod
        def _normalize_name(name):
            if not is_string(name):
                raise FNaSRTypeError("Название канала должно быть строкой, получено: {}".format(type(name)))

            return to_text(name).replace(" ", "_")

        def _channel_key(self, channel):
            if channel is None:
                return self._default_channel

            return self._normalize_name(channel)

        @main_thread_only
        def register_channel(self, name, mixer, overwrite=False, **kwargs):
            name = self._normalize_name(name)
            renpy_name = "v1_{}_FNaSR".format(name)

            with self._lock:
                if not overwrite and name in self._channels:
                    raise FNaSRRegisterError("Звуковой канал '{}' уже зарегистрирован".format(name))

                renpy.music.register_channel(renpy_name, mixer, **kwargs)

                self._channels[name] = renpy_name

            return renpy_name

        def get_channel(self, channel=None):
            key = self._channel_key(channel)

            with self._lock:
                renpy_name = self._channels.get(key)

            if renpy_name is None:
                raise FNaSRKeyError("Звуковой канал '{}' не зарегистрирован".format(key))

            return renpy_name

        @main_thread_only
        def play(self, filename, channel=None, **kwargs):
            key = self._channel_key(channel)
            renpy_name = self.get_channel(key)

            renpy.music.play(filename, renpy_name, **kwargs)

            with self._lock:
                self._last_played[key] = filename

        @main_thread_only
        def stop(self, channel=None, **kwargs):
            renpy_name = self.get_channel(channel)
            renpy.music.stop(renpy_name, **kwargs)

        @main_thread_only
        def stop_all(self, fadeout=0.0):
            with self._lock:
                channels = tuple(self._channels.values())

            for channel in channels:
                renpy.music.stop(channel, fadeout=fadeout)

        def get_last_played(self, channel=None):
            key = self._channel_key(channel)

            with self._lock:
                return self._last_played.get(key)

        def has_channel(self, channel):
            key = self._channel_key(channel)

            with self._lock:
                return key in self._channels

    class AmbienceManager(object):
        def __init__(self):
            self._ls = None

        def sync_player(self, player, fadein=0.5, fadeout=0.5):
            if self._ls is None:
                self._ls = require_system("location")
                
            ls = self._ls
            
            location = player.current_location
            old_location = ls.get_location(player.previous_location_id)
            ambience_list = None
            played_channel = []

            if player.is_open_tablet:
                selected_location = ls.require_location(player.current_location.tablet.selected)
                ambience_list = selected_location.ambience
            else:
                ambience_list = location.ambience

            for s_data in ambience_list:
                sound, play_in_camera, channel = s_data
                last_played = audio.get_last_played(channel)

                if player.is_open_tablet:
                    if play_in_camera and sound != last_played:
                        main_executor.submit(audio.play, sound, channel, fadein=fadein)
                else:
                    if sound != last_played:
                        main_executor.submit(audio.play, sound, channel, fadein=fadein)
                played_channel.append(channel)

            if old_location is not None:
                for s_data in old_location.ambience:
                    _, _, channel = s_data
                    if channel not in played_channel:
                        main_executor.submit(audio.stop, channel, fadeout=fadeout)


    audio = AudioManager()
    ambience_manager = AmbienceManager()

init python in v1FNaSR:
    audio.register_channel("music", "music", loop=True)
    audio.register_channel("sound", "sound", loop=False)
    add_quit_fn(lambda: audio.stop_all(0.5))














# audio.rpy

init -5 python in v1FNaSR:

    import threading as _threading

    class AmbienceManager(object):
        __slots__ = ("_active_channels", "_lock")

        def __init__(self):
            self._active_channels = {}
            self._lock = _threading.RLock()

        def _get_desired_channels(self, player):
            location = player.current_location

            if location is None:
                return {}

            in_camera = player.is_open_tablet

            if in_camera:
                tablet = location.tablet

                if tablet is None:
                    raise FNaSRException("Планшет открыт, но в локации '{}' отсутствует объект Tablet.".format(location.id))

                selected = tablet.selected

                if selected is None:
                    return {}

                location_system = location.location_system

                if location_system is None:
                    raise FNaSRException("Локация '{}' не зарегистрирована в LocationSystem.".format(location.id))

                location = location_system.require_location(selected)

            desired = {}

            for sound, play_in_camera, channel in location.ambience:

                if in_camera and not play_in_camera:
                    continue

                if not audio.has_channel(channel):
                    raise FNaSRKeyError("Звуковой канал '{}' не зарегистрирован.".format(channel))

                if channel in desired:
                    raise FNaSRValueError("Канал '{}' используется несколькими звуками ambience локации '{}'.".format(channel, location.id))

                desired[channel] = sound

            return desired

        def sync_player(self, player, fadein=0.5, fadeout=0.5):
            player_system = get_system("player")

            if player_system is not None:
                if player_system.current_player is not player:
                    return

            desired = self._get_desired_channels(player)

            with self._lock:
                current = self._active_channels

                for channel in tuple(current):
                    if channel not in desired:
                        main_executor.submit(
                            audio.stop,
                            channel,
                            fadeout=fadeout
                        )

                for channel, sound in iter_items(desired):
                    if current.get(channel, MISSING) == sound:
                        continue

                    main_executor.submit(
                        audio.play,
                        sound,
                        channel,
                        fadein=fadein,
                        fadeout=fadeout
                    )

                self._active_channels = dict(desired)

        def stop_all(self, fadeout=0.5):
            with self._lock:
                channels = tuple(self._active_channels)

                for channel in channels:
                    main_executor.submit(
                        audio.stop,
                        channel,
                        fadeout=fadeout
                    )

                self._active_channels.clear()

        def get_active_channels(self):
            with self._lock:
                return dict(self._active_channels)

    ambience_manager = AmbienceManager()
