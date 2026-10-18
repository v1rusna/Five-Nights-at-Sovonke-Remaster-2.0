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

    audio = AudioManager()

init python in v1FNaSR:
    audio.register_channel("music", "music", loop=True)
    audio.register_channel("sound", "sound", loop=False)
    add_quit_fn(lambda: audio.stop_all(0.5))
