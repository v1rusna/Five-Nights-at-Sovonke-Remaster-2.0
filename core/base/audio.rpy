# -*- coding: utf-8 -*-
# core/base/audio.rpy
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


init python in v1FNaSR:
    audio.register_channel("music", "music", loop=True)
    audio.register_channel("sound", "sound", loop=False)
    add_quit_fn(lambda: audio.stop_all(0.5))
