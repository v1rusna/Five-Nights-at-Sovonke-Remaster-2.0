# settings.rpy
init -5 python in v1FNaSR:
    import threading as _threading

    class SettingError(FNaSRException):
        pass

    class Settings(object):
        __slots__ = ("_settings","_fns","_lock",)

        def __init__(self):
            self._settings = set()
            self._fns = dict([("save", list(),), ("load", list(),)])
            self._lock = _threading.RLock()

        @main_thread_only
        def add_save_fn(self, fn):
            if not callable(fn):
                raise FNaSRTypeError("'fn' должен быть вызываемым, пришло: {}".format(type(fn)))

            self._fns["save"].append(fn)

        @main_thread_only
        def add_load_fn(self, fn):
            if not callable(fn):
                raise FNaSRTypeError("'fn' должен быть вызываемым, пришло: {}".format(type(fn)))

            self._fns["load"].append(fn)

        @main_thread_only
        def save(self):
            for fn in tuple(self._fns["save"]):
                try:
                    fn(self)
                except Exception:
                    log.error("Settings.save | {}".format(repr(fn)))

        @main_thread_only
        def load(self):
            for fn in tuple(self._fns["load"]):
                try:
                    fn(self)
                except Exception:
                    log.error("Settings.load | {}".format(repr(fn)))

        @main_thread_only
        def create_setting(self, name, value):
            if not is_string(name):
                raise FNaSRTypeError("Название настройки должно быть строкой, получено: {}".format(type(name)))

            persistent_name = self._get_persistent_name(name)

            with self._lock:
                if name in self._settings:
                    raise FNaSRValueError("Настройка '{}' уже существует.".format(name))
                try:
                    if not hasattr(renpy.persistent, persistent_name):
                        setattr(renpy.persistent, persistent_name, value)
                except Exception as e:
                    raise SettingError("Не удалось создать настройку '{}': {}".format(name, e))

                self._settings.add(name)

        @main_thread_only
        def delete_setting(self, name):
            if not is_string(name):
                raise FNaSRTypeError("Название настройки должно быть строкой, получено: {}".format(type(name)))

            persistent_name = self._get_persistent_name(name)

            with self._lock:
                if name not in self._settings:
                    raise FNaSRValueError("Настройка '{}' не найдена.".format(name))

                try:
                    if hasattr(renpy.persistent, persistent_name):
                        delattr(renpy.persistent, persistent_name)
                except Exception as e:
                    raise SettingError("Не удалось удалить настройку '{}': {}".format(name, e))

                self._settings.discard(name)

        def get_setting(self, name, default=None):
            with self._lock:
                if name not in self._settings:
                    return default

                s = getattr(renpy.persistent, self._get_persistent_name(name), default)

            return self._copy(s)

        @main_thread_only
        def set_setting(self, name, new_value):
            if not is_string(name):
                raise FNaSRTypeError("Название настройки должно быть строкой, получено: {}".format(type(name)))

            persistent_name = self._get_persistent_name(name)

            with self._lock:
                if name not in self._settings:
                    raise FNaSRValueError("Настройка '{}' не найдена.".format(name))

                self._set_value(persistent_name, new_value)

        @main_thread_only
        def increment(self, name, value=1):
            if not is_number(value):
                raise FNaSRTypeError("'value' должен быть числом, получено: {}".format(type(value)))

            persistent_name = self._get_persistent_name(name)

            with self._lock:
                if name not in self._settings:
                    raise FNaSRValueError("Настройка '{}' не найдена.".format(name))

                s = getattr(renpy.persistent, self._get_persistent_name(name))

                fn = getattr(s, "increment", None)
                if callable(fn):
                    s.increment(value)
                    return

                if is_strict_integer(s):
                    self._set_value(persistent_name, s+value)
                    return
                elif isinstance(s, float):
                    self._set_value(persistent_name, s+float(value))
                    return

                raise FNaSRTypeError("Настройка должна быть числом или объектом с реализацией 'increment', получено: {}".format(type(s)))

        @main_thread_only
        def decrement(self, name, value=1):
            if not is_number(value):
                raise FNaSRTypeError("'value' должен быть числом, получено: {}".format(type(value)))

            persistent_name = self._get_persistent_name(name)

            with self._lock:
                if name not in self._settings:
                    raise FNaSRValueError("Настройка '{}' не найдена.".format(name))

                s = getattr(renpy.persistent, self._get_persistent_name(name))

                fn = getattr(s, "decrement", None)
                if callable(fn):
                    s.decrement(value)
                    return

                if is_strict_integer(s):
                    self._set_value(persistent_name, s-value)
                    return
                elif isinstance(s, float):
                    self._set_value(persistent_name, s-float(value))
                    return

                raise FNaSRTypeError("Настройка должна быть числом или объектом с реализацией 'decrement', получено: {}".format(type(s)))

        @main_thread_only
        def append(self, name, item):
            persistent_name = self._get_persistent_name(name)

            with self._lock:
                if name not in self._settings:
                    raise FNaSRValueError("Настройка '{}' не найдена.".format(name))

                s = getattr(renpy.persistent, self._get_persistent_name(name))

                fn = getattr(s, "append", None)
                if callable(fn):
                    s.append(item)
                    return

                fn = getattr(s, "add", None)
                if callable(fn):
                    s.add(item)
                    return

                raise FNaSRTypeError("Настройка реализовывать 'append' или 'add', получено: {}".format(type(s)))

        @main_thread_only
        def remove(self, name, item):
            persistent_name = self._get_persistent_name(name)

            with self._lock:
                if name not in self._settings:
                    raise FNaSRValueError("Настройка '{}' не найдена.".format(name))

                s = getattr(renpy.persistent, self._get_persistent_name(name))

                fn = getattr(s, "remove", None)
                if callable(fn):
                    s.remove(item)
                    return

                fn = getattr(s, "discard", None)
                if callable(fn):
                    s.discard(item)
                    return

                raise FNaSRTypeError("Настройка реализовывать 'remove' или 'discard', получено: {}".format(type(s)))

        def value_in(self, name, value):
            persistent_name = self._get_persistent_name(name)

            with self._lock:
                if name not in self._settings:
                    raise FNaSRValueError("Настройка '{}' не найдена.".format(name))

                s = getattr(renpy.persistent, self._get_persistent_name(name))

            return value in s

        def has_setting(self, name):
            with self._lock:
                hs = name in self._settings
            return hs

        def _get_persistent_name(self, name):
            return "v1_setting_{}_FNaSR".format(name)

        def _set_value(self, persistent_name, value):
            try:
                setattr(renpy.persistent, persistent_name, value)
            except Exception as e:
                raise SettingError("Не удалось изменить настройку '{}': {}".format(persistent_name, e))

        def _copy(self, item):
            if isinstance(item, dict):
                return dict(item)
            if isinstance(item, list):
                return list(item) # Может заменить на tuple?
            if isinstance(item, set):
                return set(item) # Может заменить на tuple?
            return item

        def __getattr__(self, attr):
            with self._lock:
                if attr not in self._settings:
                    raise FNaSRAttributeError("Settings object has no attribute {!r}".format(attr))

                s = getattr(renpy.persistent, self._get_persistent_name(attr))

            return self._copy(s)

        def __setattr__(self, attr, value):
            if attr in ("_settings","_fns","_lock",):
                object.__setattr__(self, attr, value)
                return
            try:
                self.set_setting(attr, value)
            except Exception as e:
                raise FNaSRAttributeError(e)

        def __iter__(self):
            with self._lock:
                iter_settings = iter(sorted(self._settings))
            return iter_settings

        def __contains__(self, item):
            return self.has_setting(item)

    settings = Settings()

    settings.create_setting("game_difficulty", 2)
    settings.create_setting("nights_gone", list())

    add_start_fn(settings.load)
    add_quit_fn(settings.save)
            
