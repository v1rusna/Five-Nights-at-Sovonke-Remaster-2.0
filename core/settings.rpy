# settings.rpy
init -5 python in v1FNaSR:
    import copy as _copy_module
    import threading as _threading

    _SETTINGS_SUPPORTED_DATA_TYPES = (
        float, bool, type(None),
        list, dict, set, tuple
    ) + string_types + integer_types

    class SettingError(FNaSRException):
        pass

    class Settings(object):
        __slots__ = ("_settings", "_save_fns", "_load_fns", "_lock",)

        def __init__(self):
            self._settings = dict()
            self._save_fns = list()
            self._load_fns = list()
            self._lock = _threading.RLock()


        @main_thread_only
        def add_save_fn(self, fn):
            self._add_fn(self._save_fns, fn)

        @main_thread_only
        def add_load_fn(self, fn):
            self._add_fn(self._load_fns, fn)

        @main_thread_only
        def save(self):
            self._run_fns(self._save_fns, "save")

        @main_thread_only
        def load(self):
            self._run_fns(self._load_fns, "load")


        @main_thread_only
        def create_setting(self, name, value):
            self._check_name(name)
            self._check_reserved(name)
            self._check_value(value)

            persistent_name = self._get_persistent_name(name)

            with self._lock:
                if name in self._settings:
                    raise FNaSRValueError("Настройка '{}' уже существует.".format(name))

                if not hasattr(renpy.persistent, persistent_name):
                    self._set_value(persistent_name, value)

                self._settings[name] = self._copy(value)

        @main_thread_only
        def delete_setting(self, name):
            self._check_name(name)

            with self._lock:
                persistent_name = self._require(name)

                try:
                    if hasattr(renpy.persistent, persistent_name):
                        delattr(renpy.persistent, persistent_name)
                except Exception as e:
                    raise SettingError("Не удалось удалить настройку '{}': {}".format(name, e))

                del self._settings[name]

        def has_setting(self, name):
            if not is_string(name):
                return False
            with self._lock:
                return name in self._settings

        def get_setting(self, name, default=None):
            if not is_string(name):
                return default
            with self._lock:
                if name not in self._settings:
                    return default
                return self._copy(getattr(renpy.persistent, self._get_persistent_name(name), default))

        @main_thread_only
        def set_setting(self, name, new_value):
            self._check_name(name)

            with self._lock:
                persistent_name = self._require(name)
                self._set_value(persistent_name, new_value)

        @main_thread_only
        def reset_setting(self, name):
            self._check_name(name)

            with self._lock:
                persistent_name = self._require(name)
                self._set_value(persistent_name, self._copy(self._settings[name]))

        @main_thread_only
        def reset_all_settings(self):
            with self._lock:
                for name, default in iter_items(self._settings):
                    try:
                        self._set_value(self._get_persistent_name(name), self._copy(default))
                    except Exception:
                        log.error("Settings.reset_all_settings | {!r}".format(name))


        @main_thread_only
        def increment(self, name, value=1):
            self._change_number(name, value, "increment", 1)

        @main_thread_only
        def decrement(self, name, value=1):
            self._change_number(name, value, "decrement", -1)

        @main_thread_only
        def append(self, name, item):
            self._call_container_method(name, item, ("append", "add"))

        @main_thread_only
        def remove(self, name, item):
            self._call_container_method(name, item, ("remove", "discard"))

        def value_in(self, name, value):
            self._check_name(name)

            with self._lock:
                s = getattr(renpy.persistent, self._require(name))
                is_in = value in s

            return is_in


        @staticmethod
        def _get_persistent_name(name):
            return "v1_setting_{}_FNaSR".format(name)

        @staticmethod
        def _check_name(name):
            if not is_string(name):
                raise FNaSRTypeError("Название настройки должно быть строкой, получено: {}".format(type(name)))

        @classmethod
        def _check_reserved(cls, name):
            if name.startswith("_") or hasattr(cls, name):
                raise FNaSRValueError("Имя настройки '{}' зарезервировано.".format(name))

        @staticmethod
        def _check_value(value, _seen=None):
            if _seen is None:
                _seen = set()

            if not isinstance(value, _SETTINGS_SUPPORTED_DATA_TYPES):
                raise FNaSRTypeError("Значение для настройки должно быть стандартным типом данных, получено: {}".format(type(value)))

            if not isinstance(value, (list, tuple, set, dict)):
                return

            value_id = id(value)

            if value_id in _seen:
                return

            _seen.add(value_id)

            if isinstance(value, dict):
                for key, item in iter_items(value):
                    Settings._check_value(key, _seen)
                    Settings._check_value(item, _seen)
            else:
                for item in value:
                    Settings._check_value(item, _seen)

        @staticmethod
        def _add_fn(storage, fn):
            if not callable(fn):
                raise FNaSRTypeError("'fn' должен быть вызываемым, пришло: {}".format(type(fn)))
            storage.append(fn)

        @staticmethod
        def _run_fns(storage, label):
            for fn in tuple(storage):
                try:
                    fn()
                except Exception:
                    log.error("Settings.{} | {}".format(label, repr(fn)))

        def _require(self, name):
            if name not in self._settings:
                raise FNaSRValueError("Настройка '{}' не найдена.".format(name))
            return self._get_persistent_name(name)

        def _set_value(self, persistent_name, value):
            self._check_value(value)
            value = self._copy(value)

            try:
                setattr(renpy.persistent, persistent_name, value)
            except Exception as e:
                raise SettingError("Не удалось изменить настройку '{}': {}".format(persistent_name, e))

        def _copy(self, item):
            return _copy_module.deepcopy(item)

        def _change_number(self, name, value, method_name, sign):
            self._check_name(name)
            if not is_number(value):
                raise FNaSRTypeError("'value' должен быть числом, получено: {}".format(type(value)))

            with self._lock:
                persistent_name = self._require(name)
                s = getattr(renpy.persistent, persistent_name)

                fn = getattr(s, method_name, None)
                if not callable(fn):
                    if is_strict_integer(s):
                        self._set_value(persistent_name, s + sign * value)
                    elif isinstance(s, float):
                        self._set_value(persistent_name, s + sign * float(value))
                    else:
                        raise FNaSRTypeError("Настройка должна быть числом или объектом с реализацией '{}', получено: {}".format(method_name, type(s)))
                    return

            fn(value)

        def _call_container_method(self, name, item, method_names):
            self._check_name(name)

            with self._lock:
                s = getattr(renpy.persistent, self._require(name))

            for method_name in method_names:
                fn = getattr(s, method_name, None)
                if callable(fn):
                    fn(item)
                    return

            raise FNaSRTypeError("Настройка должна реализовывать {}, получено: {}".format(
                " или ".join("'{}'".format(m) for m in method_names), type(s)))


        def __getattr__(self, attr):
            if attr.startswith("_"):
                raise FNaSRAttributeError("Settings object has no attribute {!r}".format(attr))

            with self._lock:
                if attr not in self._settings:
                    raise FNaSRAttributeError("Settings object has no attribute {!r}".format(attr))

                try:
                    return self._copy(getattr(renpy.persistent, self._get_persistent_name(attr)))
                except AttributeError:
                    raise SettingError("'renpy.persistent' has no setting {!r}.".format(attr))

        def __setattr__(self, attr, value):
            if attr in self.__slots__:
                object.__setattr__(self, attr, value)
                return
            with self._lock:
                if attr not in self._settings:
                    raise FNaSRAttributeError("Settings object has no attribute {!r}".format(attr))
                self.set_setting(attr, value)

        def __iter__(self):
            with self._lock:
                names = sorted(self._settings)
            return iter(names)

        def __contains__(self, item):
            return self.has_setting(item)

        def __len__(self):
            with self._lock:
                return len(self._settings)

    settings = Settings()

    settings.create_setting("game_difficulty", 2)
    settings.create_setting("nights_gone", list())
    settings.create_setting("key_map", dict((["tablet", {"K_SPACE"}], ["bulb", {"K_z"}], ["door", {"K_x"}], ["move_start", {"K_w"}], ["move_stop", {"K_s"}],)))

    add_start_fn(settings.load, order=1)
    add_quit_fn(settings.save, order=1)

init python in v1FNaSR:
    def _v1_settings_debug(context):
        info = []
        for name in settings:
            value = settings.get_setting(name)
            info.append(" {}: {}".format(name, value).replace("{", "{{").replace("}", "}}"))
        return "\n".join(info)

    debug.add_element(
        DebugSection(
            DebugText(lambda context: "Настроек: {}".format(len(settings)), style="v1_text_16_style_FNaSR"),
            DebugText(_v1_settings_debug),
            order=4
        ),
        group="System"
    )
