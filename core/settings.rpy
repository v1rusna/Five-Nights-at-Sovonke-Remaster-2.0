# -*- coding: utf-8 -*-
# core/settings.rpy
init -5 python in v1FNaSR:
    import copy as _copy_module
    import threading as _threading

    _SUPPORTED_TYPES = (
        float, bool, type(None),
        list, dict, set, tuple
    ) + string_types + integer_types

    class SettingError(FNaSRException):
        pass

    class Settings(native_object):
        __slots__ = ("_settings", "_save_fns", "_load_fns", "_set_value_fns", "_lock",)

        def __init__(self):
            self._settings = dict()
            self._save_fns = list()
            self._load_fns = list()
            self._set_value_fns = dict()
            self._lock = _threading.RLock()


        @main_thread_only
        def add_save_fn(self, fn):
            self._check_fn(fn)
            self._save_fns.append(fn)

        @main_thread_only
        def add_load_fn(self, fn):
            self._check_fn(fn)
            self._load_fns.append(fn)

        @main_thread_only
        def save(self):
            self._run_fns(self._save_fns, "save")

        @main_thread_only
        def load(self):
            self._run_fns(self._load_fns, "load")


        @main_thread_only
        def create_setting(self, name, value, set_value_fn=None):
            self._check_name(name)
            self._check_reserved(name)
            self._check_value(value)
            if set_value_fn is not None:
                self._check_fn(set_value_fn)

            persistent_name = self._get_persistent_name(name)

            with self._lock:
                if name in self._settings:
                    raise FNaSRValueError("Настройка '{}' уже существует.".format(name))

                if persistent_name not in renpy.store.persistent.__dict__:
                    self._set_value(persistent_name, value)

                self._settings[name] = self._copy(value)

                if set_value_fn is not None:
                    self._set_value_fns[persistent_name] = set_value_fn
                    self._apply_value_fn(persistent_name, getattr(renpy.store.persistent, persistent_name))

        @main_thread_only
        def delete_setting(self, name):
            with self._lock:
                persistent_name = self._require(name)

                try:
                    delattr(renpy.store.persistent, persistent_name)
                except AttributeError:
                    pass
                except Exception as e:
                    raise SettingError("Не удалось удалить настройку '{}': {}: {}".format(name, type(e), e))

                del self._settings[name]
                self._set_value_fns.pop(persistent_name, None)

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
                return self._copy(getattr(renpy.store.persistent, self._get_persistent_name(name), default))

        @main_thread_only
        def set_setting(self, name, new_value):
            with self._lock:
                self._set_value(self._require(name), new_value)

        @main_thread_only
        def reset_setting(self, name):
            with self._lock:
                persistent_name = self._require(name)
                self._set_value(persistent_name, self._settings[name])

        @main_thread_only
        def reset_all_settings(self):
            with self._lock:
                for name, default in iter_items(self._settings):
                    try:
                        self._set_value(self._get_persistent_name(name), default)
                    except Exception:
                        log.error("Settings.reset_all_settings | {!r}".format(name))


        @main_thread_only
        def increment(self, name, value=1):
            self._change_number(name, value, 1)

        @main_thread_only
        def decrement(self, name, value=1):
            self._change_number(name, value, -1)

        @main_thread_only
        def append(self, name, item):
            self._call_container_method(name, item, ("append", "add"))

        @main_thread_only
        def remove(self, name, item):
            self._call_container_method(name, item, ("remove", "discard"))

        def value_in(self, name, value):
            with self._lock:
                return value in getattr(renpy.store.persistent, self._require(name))


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

        @classmethod
        def _check_value(cls, value, _seen=None):
            if not isinstance(value, _SUPPORTED_TYPES):
                raise FNaSRTypeError("Значение для настройки должно быть стандартным типом данных, получено: {}".format(type(value)))

            if not isinstance(value, (list, tuple, set, dict)):
                return

            if _seen is None:
                _seen = set()

            value_id = id(value)
            if value_id in _seen:
                return
            _seen.add(value_id)

            if isinstance(value, dict):
                for key, item in iter_items(value):
                    cls._check_value(key, _seen)
                    cls._check_value(item, _seen)
            else:
                for item in value:
                    cls._check_value(item, _seen)

        @staticmethod
        def _check_fn(fn):
            if not callable(fn):
                raise FNaSRTypeError("'fn' должен быть вызываемым, получено: {}".format(type(fn)))

        @staticmethod
        def _run_fns(storage, label):
            for fn in tuple(storage):
                try:
                    fn()
                except Exception:
                    log.error("Settings.{} | {}".format(label, repr(fn)))

        @staticmethod
        def _copy(item):
            return _copy_module.deepcopy(item)

        def _require(self, name):
            self._check_name(name)
            if name not in self._settings:
                raise FNaSRValueError("Настройка '{}' не найдена.".format(name))
            return self._get_persistent_name(name)

        def _set_value(self, persistent_name, value):
            self._check_value(value)
            value = self._copy(value)

            try:
                setattr(renpy.store.persistent, persistent_name, value)
            except Exception as e:
                raise SettingError("Не удалось изменить настройку '{}': {}: {}".format(persistent_name, type(e), e))

            self._apply_value_fn(persistent_name, self._copy(value))

        def _change_number(self, name, value, sign):
            if not is_number(value):
                raise FNaSRTypeError("'value' должен быть числом, получено: {}".format(type(value)))

            with self._lock:
                persistent_name = self._require(name)
                current = getattr(renpy.store.persistent, persistent_name)

                if not (is_strict_integer(current) or isinstance(current, float)):
                    raise FNaSRTypeError("Настройка должна быть числом, получено: {}".format(type(current)))

                self._set_value(persistent_name, current + sign * value)

        def _call_container_method(self, name, item, method_names):
            with self._lock:
                persistent_name = self._require(name)
                value = self._copy(getattr(renpy.store.persistent, persistent_name))

                for method_name in method_names:
                    fn = getattr(value, method_name, None)

                    if callable(fn):
                        fn(item)
                        self._set_value(persistent_name, value)
                        return

                raise FNaSRTypeError("Настройка должна реализовывать {}, получено: {}".format(
                    " или ".join("'{}'".format(m) for m in method_names), type(value)))

        def _apply_value_fn(self, persistent_name, value):
            fn = self._set_value_fns.get(persistent_name)
            if fn is None:
                return

            try:
                fn(self._copy(value))
            except Exception as e:
                raise SettingError("Не удалось применить настройку '{}': {}: {}".format(persistent_name, type(e), e))


        def __getattr__(self, attr):
            if attr.startswith("_"):
                raise FNaSRAttributeError("Settings object has no attribute {!r}".format(attr))

            with self._lock:
                if attr not in self._settings:
                    raise FNaSRAttributeError("Settings object has no attribute {!r}".format(attr))

                try:
                    return self._copy(getattr(renpy.store.persistent, self._get_persistent_name(attr)))
                except AttributeError:
                    raise SettingError("'renpy.store.persistent' has no setting {!r}.".format(attr))

        def __setattr__(self, attr, value):
            if attr in self.__slots__:
                native_object.__setattr__(self, attr, value)
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

    add_start_fn(settings.load, order=1)
    add_quit_fn(settings.save, order=1)

init python in v1FNaSR:
    def _change_nights_gone(new_value):
        if renpy.game.context().init_phase:
            return
        require_system("night").import_progress(new_value)

    settings.create_setting("game_difficulty", 2)
    settings.create_setting("nights_gone", list(), _change_nights_gone)
    settings.create_setting("key_map", dict((["tablet", {"K_SPACE"}], ["bulb", {"K_z"}], ["door", {"K_x"}], ["move_start", {"K_w"}], ["move_stop", {"K_s"}],)))


    debug.add_element(
        DebugSection(
            DebugText(
                lambda context: "Настроек: {}".format(len(settings)),
                style="v1_text_16_style_FNaSR"
            ),
            *[
                DebugButton(
                    lambda context, name=name: " {}: {}".format(name, settings.get_setting(name)).replace("{", "{{").replace("}", "}}"),
                    lambda context, name=name: settings.reset_setting(name)
                )
                for name in settings
            ],
            order=4
        ),
        group="System"
    )

    del _change_nights_gone
