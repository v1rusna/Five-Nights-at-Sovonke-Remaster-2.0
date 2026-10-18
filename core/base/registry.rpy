# registry.rpy
init -11 python in v1FNaSR:
    import threading as _threading

    def _default_screen_handler(screen_list, state, **kwargs):
        if state == "show":
            for screen_name in screen_list:
                renpy.show_screen(screen_name, **kwargs)
            return

        if state == "hide":
            for screen_name in screen_list:
                renpy.hide_screen(screen_name, **kwargs)

    def single_screen_interaction(index=0):
        def inner(screen_list, state, **kwargs):
            if state == "show":
                renpy.show_screen(screen_list[index], **kwargs)
            elif state == "hide":
                renpy.hide_screen(screen_list[index], **kwargs)
        return inner


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

