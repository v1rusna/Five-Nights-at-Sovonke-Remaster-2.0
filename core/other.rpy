# -*- coding: utf-8 -*-
# core/other.rpy
init -12 python in v1FNaSR:
    import threading as _threading
    try:
        from collections.abc import MutableSequence as _MutableSequence
    except ImportError:
        from collections import MutableSequence as _MutableSequence

    class GlobalState(native_object):
        lock = _threading.RLock()
        _flags = dict()

        @classmethod
        def get(cls, key, default=None):
            with cls.lock:
                return cls._flags.get(key, default)

        @classmethod
        def set(cls, key, value):
            with cls.lock:
                cls._flags[key] = value

        @classmethod
        def set_if_absent(cls, key, value):
            with cls.lock:
                if key in cls._flags:
                    return False

                cls._flags[key] = value
                return True

        @classmethod
        def clear(cls):
            with cls.lock:
                cls._flags.clear()

        @classmethod
        def get_len(cls):
            with cls.lock:
                return len(cls._flags)

        @classmethod
        def items(cls):
            with cls.lock:
                return iter(tuple(iter_items(cls._flags)))

        @classmethod
        def values(cls):
            with cls.lock:
                return iter(tuple(iter_values(cls._flags)))

        @classmethod
        def keys(cls):
            with cls.lock:
                return iter(tuple(iter_keys(cls._flags)))

    class BaseAI(native_object):
        def __init__(self):
            super(BaseAI, self).__init__()
            self._current_location = None

        @property
        def current_location(self):
            return self._current_location

        def move(self, location, ignore_door=False, allow_migrate=False):
            if not isinstance(location, Location):
                raise FNaSRTypeError("`location` must be an instance of the 'Location' class, not '{}'".format(type(location)))
            if self._current_location is location:
                return
            if location.location_system is None:
                raise FNaSRException("The location '{}' is not registered in any of the location systems".format(location.id))
            if not location.location_system.has_location(location.id):
                raise FNaSRException("The location with ID '{}' refers to a LocationSystem in which it is not registered".format(location.id))
            if self._current_location is not None and not allow_migrate and self._current_location.location_system != location.location_system:
                raise FNaSRException("The current({}) and new({}) locations belong to different location systems".format(self._current_location.id, location.id))
            if not ignore_door and location.door is not None and not location.door.is_open:
                raise DoorClose(location.id)
            self._current_location = location
            location.on_enter(self)

    class _MissingType(native_object):
        __slots__ = ()
        
        _instance = None

        def __new__(cls):
            if cls._instance is None:
                cls._instance = native_object.__new__(cls)
            return cls._instance

        def __repr__(self):
            return "<MISSING>"

        def __bool__(self):
            return False

        __nonzero__ = __bool__

    MISSING = _MissingType()

    class InfoObject(native_object):
        __slots__ = ("_v1data",)

        def __init__(self, **kwargs):
            native_object.__setattr__(self, "_v1data", {})
            self.update(kwargs)

        def __setattr__(self, name, value):
            name = to_text(name)

            if name.startswith("_"):
                raise FNaSRAttributeError("Атрибут {0!r} не существует.".format(name))

            self._v1data[name] = value

        def __getattr__(self, name):
            name = to_text(name)

            try:
                return self._v1data[name]
            except KeyError:
                raise FNaSRAttributeError(
                    "Атрибут {0!r} не существует.".format(name)
                )

        def __delattr__(self, name):
            name = to_text(name)

            try:
                del self._v1data[name]
            except KeyError:
                raise FNaSRAttributeError(
                    "Атрибут {0!r} не существует.".format(name)
                )

        def __getitem__(self, key):
            return self._v1data[key]

        def __setitem__(self, key, value):
            self._v1data[key] = value

        def __delitem__(self, key):
            del self._v1data[key]

        def __contains__(self, key):
            return key in self._v1data

        def __iter__(self):
            return iter(self._v1data)

        def __len__(self):
            return len(self._v1data)

        def get(self, key, default=None):
            return self._v1data.get(key, default)

        def setdefault(self, key, default=None):
            return self._v1data.setdefault(key, default)

        def pop(self, key, *args):
            return self._v1data.pop(key, *args)

        def popitem(self):
            return self._v1data.popitem()

        def clear(self):
            self._v1data.clear()

        def update(self, *args, **kwargs):
            self._v1data.update(*args, **kwargs)

        def keys(self):
            return self._v1data.keys()

        def values(self):
            return self._v1data.values()

        def items(self):
            return self._v1data.items()

        def iterkeys(self):
            return iter_keys(self._v1data)

        def itervalues(self):
            return iter_values(self._v1data)

        def iteritems(self):
            return iter_items(self._v1data)

        def copy(self):
            return self.__class__(**self._v1data)

        def has_key(self, key):
            return key in self._v1data

        def __repr__(self):
            return "{0}({1!r})".format(
                self.__class__.__name__,
                self._v1data
            )

    class UIUpdater(native_object):
        MIN_INTERVAL = 1.0 / 60.0
        MAX_INTERVAL = 1.0
        DEFAULT_INTERVAL = 1.0 / 10.0

        _interval = DEFAULT_INTERVAL
        _new_interval = None

        _time_since_update = MAX_INTERVAL

        _ui_dirty = False

        _lock = _threading.Lock()

        @classmethod
        def set_interval(cls, new_interval):
            if not is_number(new_interval):
                raise FNaSRTypeError("'new_interval' должен быть числом, получено: {}".format(type(new_interval)))

            new_interval = float(new_interval)

            if not cls.MIN_INTERVAL <= new_interval <= cls.MAX_INTERVAL:
                raise FNaSRValueError("'new_interval' должен быть в диапазоне от {} до {} секунд, получено: {}".format(cls.MIN_INTERVAL,cls.MAX_INTERVAL,new_interval))

            with cls._lock:
                cls._new_interval = new_interval

        @classmethod
        def update_ui(cls):
            with cls._lock:
                cls._ui_dirty = True

        @classmethod
        def draw(cls, dt):
            with cls._lock:
                if dt > 0:
                    cls._time_since_update = min(cls._time_since_update + dt, cls.MAX_INTERVAL)

                if cls._new_interval is not None:
                    cls._interval = cls._new_interval
                    cls._new_interval = None

                if not cls._ui_dirty or cls._time_since_update < cls._interval:
                    return

                cls._ui_dirty = False
                cls._time_since_update = 0.0

            cls._restart_interaction()

        @staticmethod
        def _restart_interaction():
            if is_main_thread():
                renpy.restart_interaction()
            else:
                main_executor.submit(renpy.restart_interaction)

        @classmethod
        def reset(cls):
            with cls._lock:
                cls._interval = cls.DEFAULT_INTERVAL
                cls._new_interval = None
                cls._time_since_update = cls.MAX_INTERVAL
                cls._ui_dirty = False

    def update_ui():
        UIUpdater.update_ui()

    class MultiLock(native_object):
        __slots__ = ("_blockers", "_lock",)

        def __init__(self):
            self._blockers = set()
            self._lock = _threading.RLock()

        def block(self, blocker):
            if blocker is None:
                raise FNaSRValueError("blocker cannot be None")

            with self._lock:
                self._blockers.add(blocker)

        def unblock(self, blocker):
            with self._lock:
                if blocker not in self._blockers:
                    return False

                self._blockers.remove(blocker)
                return True

        @property
        def blocked(self):
            with self._lock:
                return bool(self._blockers)

        @property
        def blockers(self):
            with self._lock:
                return frozenset(self._blockers)

        def clear(self):
            with self._lock:
                self._blockers.clear()

    class Check(native_object):
        @staticmethod
        def expect(value, predicate, name, expected, exc_type):
            if not predicate(value):
                raise exc_type("'{}' должен быть {}, получено: {} ({!r})".format(name, expected, type(value), value))

        @classmethod
        def many_expect(cls, *args):
            for item in args:
                if isinstance(item, (list, tuple)):
                    cls.expect(*item)
                elif isinstance(item, dict):
                    cls.expect(**item)
                else:
                    raise FNaSRTypeError("The value must be a tuple, list, or dict; received: {}".format(type(item)))

        @classmethod
        def expect_type(cls, value, predicate, name, expected):
            cls.expect(value, predicate, name, expected, FNaSRTypeError)

        @classmethod
        def expect_value(cls, value, predicate, name, expected):
            cls.expect(value, predicate, name, expected, FNaSRValueError)

        def __call__(self, *args, **kwargs):
            self.expect(*args, **kwargs)

    check = Check()

    class Game(native_object):
        def __init__(self):
            self._pause_fn = (list(), list())
            self._is_pause = False
            self._lock = _threading.RLock()

        @property
        def is_pause(self):
            return self._is_pause

        def add_paused_fn(self, fn):
            check.expect_type(fn, callable, "fn", "вызываемым")
            with self._lock:
                self._pause_fn[0].append(fn)

        def add_unpaused_fn(self, fn):
            check.expect_type(fn, callable, "fn", "вызываемым")
            with self._lock:
                self._pause_fn[1].append(fn)

        def on_pause(self):
            with self._lock:
                if self._is_pause:
                    return
                self._is_pause = True
                fns = tuple(self._pause_fn[0])
            for fn in fns:
                fn()

        def on_unpause(self):
            with self._lock:
                if not self._is_pause:
                    return
                self._is_pause = False
                fns = tuple(self._pause_fn[1])
            for fn in fns:
                fn()

    game = Game()

init python in v1FNaSR:
    def _noop_update(dt):
        pass

    class TutorialObject(GameObject):
        __slots__ = (
            "_pm", "_em", "_ts",
            "_stage", "_current_time", "_target_time",
        )

        _instance = None

        def __new__(cls):
            if cls._instance is None:
                cls._instance = native_object.__new__(cls)
            return cls._instance

        def __init__(self):
            super(TutorialObject, self).__init__()
            self._setattr("_stage", 1)
            self._setattr("_current_time", 0.0)
            self._setattr("_target_time", None)
            self._setattr("_pm", None)
            self._setattr("_em", None)
            self._setattr("_ts", None)

            self._stage_table = {
                1: self._stage_1,
            }

        def start(self):
            loaded = require_system("night").loaded
            if loaded.id != "tutorial":
                self.update = _noop_update
                return

            self.update = self._tutorial_update
            self._pm = require_system("player")
            self._em = require_system("enemy")
            self._ts = require_system("time")

            for enemy in self._em.iter_current_group:
                enemy.enabled = False
                enemy.is_invisible = False

            self._ts.is_game_time_enabled = False

        def _tutorial_update(self, dt):
            self._stage_table[self._stage](dt)

        def reset(self):
            super(TutorialObject, self).reset()
            self.update = _noop_update

        def _stage_1(self, dt):
            if self._target_time is not None:
                self._current_time += dt
                if self._current_time >= self._target_time:
                    self._target_time = None
                    self._current_time = 0.0
                    self._stage += 1
                    main_executor.submit(visual.hide, "black")
                    return


            player = self._pm.current_player
            player.move(-11)
            main_executor.submit(audio.play, None, "sound", loop=False) # TODO: Указать звук шагов
            main_executor.submit(visual.show, "black") # TODO: Добавить анимацию
            self._target_time = 1.0

    require_system("cycle").register(TutorialObject())

    add_quit_fn(GlobalState.clear)

    debug.add_element(
        DebugSection(
            DebugText(lambda context: "GlobalState: {}".format(GlobalState.get_len()), style="v1_text_16_style_FNaSR"),
            DebugText(lambda context: "\n".join("'{}': {}".format(k, repr(v)) for k, v in GlobalState.items())),
            order=3
        ),
        group="System"
    )
