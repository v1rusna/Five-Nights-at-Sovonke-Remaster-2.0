# registry.rpy
init -7 python in v1FNaSR:
    def _default_screen_handler(screen_list, state, **kwargs):
        if state == "show":
            for screen_name in screen_list:
                renpy.show_screen(screen_name, **kwargs)
            return

        if state == "hide":
            for screen_name in screen_list:
                renpy.hide_screen(screen_name, **kwargs)


    class _Registry(object):
        def __init__(self, item_name, duplicate_error, missing_error):
            self._items = {}
            self._item_name = item_name
            self._duplicate_error = duplicate_error
            self._missing_error = missing_error

        def _check_edit(self):
            if not renpy.game.context().init_phase:
                raise FNaSRRegisterError(
                    "Редактирование {} возможно только во время "
                    "инициализации игры".format(self._item_name)
                )

        def _check_register(self, key, overwrite):
            self._check_edit()
            if not overwrite and key in self._items:
                raise FNaSRRegisterError(self._duplicate_error.format(key))

        def register(self, key, value, overwrite=False):
            self._check_register(key, overwrite)
            self._items[key] = value

        def delete(self, key):
            self._check_edit()
            if key not in self._items:
                raise FNaSRRegisterError(
                    self._missing_error.format(key)
                )

            del self._items[key]

        def get(self, key, default=None):
            return self._items.get(key, default)

        def has(self, key):
            return key in self._items

        def keys(self):
            return list(iter_keys(self._items))

        def values(self):
            return list(iter_values(self._items))

    class _ScreensRegistry(_Registry):

        def __init__(
            self,
            item_name,
            duplicate_error,
            missing_error,
            not_iterable_error
        ):
            super(_ScreensRegistry, self).__init__(item_name, duplicate_error, missing_error)
            self._not_iterable_error = not_iterable_error

        def _normalize_screen_names(self, screen_names):
            if is_string(screen_names):
                screen_names = (screen_names,)

            if not isinstance(screen_names, Iterable):
                raise FNaSRRegisterError(self._not_iterable_error.format(type(screen_names)))

            return tuple(screen_names)

        def _normalize_callback(self, callback):
            if callback is None:
                callback = _default_screen_handler

            if not callable(callback):
                raise FNaSRTypeError("callback должен быть вызываемым объектом, передано '{}'".format(repr(callback)))

            return callback

        def register(self, key, screen_names, overwrite=False, callback=None):
            self._check_register(key, overwrite)

            screen_names = self._normalize_screen_names(screen_names)
            callback = self._normalize_callback(callback)

            self._items[key] = (screen_names, callback)

        def get_names(self, key, default=None):
            data = self._items.get(key)

            if data is None:
                return default

            return data[0]

        def edit(self, key, new_screen_names=MISSING, new_callback=MISSING):
            self._check_edit()

            if key not in self._items:
                raise FNaSRRegisterError(self._missing_error.format(key))

            screen_names, callback = self._items[key]

            if new_screen_names is not MISSING:
                screen_names = self._normalize_screen_names(new_screen_names)

            if new_callback is not MISSING:
                callback = self._normalize_callback(new_callback)

            self._items[key] = (screen_names, callback)

    def register_system(system_name, system, overwrite=False):
        with _store_lock:
            _store["systems"].register(system_name, system, overwrite)

    def delete_system(system_name):
        with _store_lock:
            _store["systems"].delete(system_name)

    def get_system(system_name, default=None):
        with _store_lock:
            return _store["systems"].get(system_name, default)

    def require_system(system_name):
        with _store_lock:
            system = _store["systems"].get(system_name)
        if system is None:
            raise FNaSRNotFound("System '{}' is not registered.".format(system_name))
        return system

    def has_system(system_name):
        with _store_lock:
            return _store["systems"].has(system_name)

    def get_system_list():
        with _store_lock:
            return _store["systems"].keys()

    
    def register_screen(screen_key, screen_names, overwrite=False, callback=None):
        with _store_lock:
            _store["screens"].register(screen_key, screen_names, overwrite, callback)

    def delete_screen(screen_key):
        with _store_lock:
            _store["screens"].delete(screen_key)

    def edit_screen(screen_key, new_screen_names=MISSING, new_callback=MISSING):
        with _store_lock:
            _store["screens"].edit(screen_key, new_screen_names, new_callback)

    def get_screen_data(screen_key, default=None):
        with _store_lock:
            return _store["screens"].get(screen_key, default)

    def get_screen_names(screen_key, default=None):
        with _store_lock:
            return _store["screens"].get_names(screen_key, default)

    def has_screen(screen_key):
        with _store_lock:
            return _store["screens"].has(screen_key)

    def show_screen(screen_key, **kwargs):
        with _store_lock:
            screen_data = _store["screens"].get(screen_key)

        if screen_data is None:
            raise FNaSRRegisterError("Экран по ключу '{}' не найден".format(screen_key))

        screens, callback = screen_data
        callback(screens, "show", **kwargs)

    def hide_screen(screen_key, **kwargs):
        with _store_lock:
            screen_data = _store["screens"].get(screen_key)

        if screen_data is None:
            raise FNaSRRegisterError("Экран по ключу '{}' не найден".format(screen_key))

        screens, callback = screen_data
        callback(screens, "hide", **kwargs)

    def hide_all_screen(directly=False, **kwargs):
        with _store_lock:
            screen_data = _store["screens"].values()

        for screens, callback in screen_data:
            if directly:
                _default_screen_handler(screens, "hide", **kwargs)
            else:
                callback(screens, "hide", **kwargs)

    def replace_screen(original_screen_name, name_new_screen):
        if is_initialized():
            raise FNaSRRegisterError("Нельзя заменять экраны после начала игры.")

        with _store_lock:
            if original_screen_name in _store["replace_screen"]:
                raise FNaSRRegisterError("Экран '{}' уже был заменен.".format(original_screen_name))

        screens = renpy.display.screen.screens

        try:
            original_screen = screens[(original_screen_name, None)]
        except KeyError:
            raise FNaSRRegisterError("Исходный экран '{}' не найден.".format(original_screen_name))

        try:
            replacement_screen = screens[(name_new_screen, None)]
        except KeyError:
            raise FNaSRRegisterError("Экран-замена '{}' не найден.".format(name_new_screen))

        renpy.display.screen.screens[(original_screen_name, None)] = replacement_screen

        with _store_lock:
            _store["replace_screen"][original_screen_name] = (name_new_screen, original_screen)

    def restore_screen(original_screen_name):
        if is_initialized():
            raise FNaSRRegisterError("Нельзя изменять экраны после начала игры.")

        with _store_lock:
            data = _store["replace_screen"].get(original_screen_name)

        if data is None:
            raise FNaSRRegisterError("Экран '{}' не был заменен.".format(original_screen_name))

        _, original_screen = data

        renpy.display.screen.screens[(original_screen_name, None)] = original_screen

        with _store_lock:
            del _store["replace_screen"][original_screen_name]

    def restore_all_screens():
        if is_initialized():
            raise FNaSRRegisterError("Нельзя изменять экраны после начала игры.")

        with _store_lock:
            snapshot = dict(_store["replace_screen"])

        errors = []

        for original_name, data in iter_items(snapshot):
            replacement_name, original_screen = data

            try:
                renpy.display.screen.screens[(original_name, None)] = original_screen
            except Exception as e:
                errors.append((original_name, replacement_name, e))
                continue

            with _store_lock:
                _store["replace_screen"].pop(original_name,None)

        if errors:
            message = "При восстановлении экранов произошли исключения:\n"

            for original_name, replacement_name, error in errors:
                message += "{} <- {}: {}\n".format(original_name,replacement_name,error)

            raise FNaSRException(message)

    def is_replaced_screen(screen_name):
        with _store_lock:
            return screen_name in _store["replace_screen"]


    def register_channel(name, mixer, overwrite=False, **kwargs):
        name = name.replace(" ", "_")
        vname = "v1_{}_FNaSR".format(name)

        with _store_lock:
            if not overwrite and name in _store["sound_channels"]:
                raise FNaSRRegisterError("Звуковой канал '{}' уже зарегистрирован".format(name))

        renpy.music.register_channel(vname, mixer, **kwargs)

        with _store_lock:
            _store["sound_channels"][name] = vname

    def play(filename, channel=None, **kwargs):
        channel = get_channel(channel)
        if channel is None:
            channel = "v1_music_FNaSR"
        renpy.music.play(filename, channel, **kwargs)

    def stop(channel=None, **kwargs):
        channel = get_channel(channel)
        if channel is None:
            channel = "v1_music_FNaSR"
        renpy.music.stop(channel, **kwargs)

    def get_channel(channel):
        with _store_lock:
            if channel not in _store["sound_channels"]:
                if channel is None:
                    return
                raise FNaSRKeyError("Звуковой канал '{}' не зарегистрирован".format(channel))
            else:
                channel = _store["sound_channels"][channel]
        return channel

    def stop_all(fadeout):
        with _store_lock:
            channels = tuple(iter_values(_store["sound_channels"]))

        for channel in channels:
            renpy.music.stop(channel, fadeout=fadeout)

init python:
    v1FNaSR.register_channel("music", "music", loop=True)
    v1FNaSR.register_channel("sound", "sound", loop=False)
    v1FNaSR.add_quit_fn(lambda: v1FNaSR.hide_all_screen(True))
    v1FNaSR.add_quit_fn(lambda: v1FNaSR.stop_all(0.5))
    v1FNaSR.add_quit_fn(v1FNaSR.restore_all_screens)

