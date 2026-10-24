# other.rpy
init -12 python in v1FNaSR:
    import threading as _threading
    try:
        from collections.abc import MutableSequence as _MutableSequence
    except ImportError:
        from collections import MutableSequence as _MutableSequence

    class GlobalState(object):
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

    class BaseAI(object):
        def __init__(self):
            super(BaseAI, self).__init__()
            self._current_location = None

        @property
        def current_location(self):
            return self._current_location

        def move(self, location, allow_migrate=False):
            if not isinstance(location, Location):
                raise FNaSRTypeError("`location` must be an instance of the 'Location' class, not '{}'".format(type(location)))
            if self._current_location is location:
                return
            if location.location_system is None:
                raise FNaSRException("The location '{}' is not registered in any of the location systems")
            if not location.location_system.has_location(location.id):
                raise FNaSRException("The location with ID '{}' refers to a LocationSystem in which it is not registered".format(location.id))
            if self._current_location is not None and not allow_migrate and self._current_location.location_system != location.location_system:
                raise FNaSRException("The current({}) and new({}) locations belong to different location systems".format(self._current_location.id, location.id))
            if location.door is not None and not location.door.is_open:
                raise DoorClose(location.id)
            self._current_location = location
            location.on_enter(self)

    class _MissingType(object):
        _instance = None

        def __new__(cls):
            if cls._instance is None:
                cls._instance = object.__new__(cls)
            return cls._instance

        def __repr__(self):
            return "<MISSING>"

        def __bool__(self):
            return False

        __nonzero__ = __bool__

    MISSING = _MissingType()

    class InfoObject(object):
        __slots__ = ("_v1data",)

        def __init__(self, **kwargs):
            object.__setattr__(self, "_v1data", {})
            self.update(kwargs)

        def __setattr__(self, name, value):
            name = to_text(name)

            if name == "_v1data":
                object.__setattr__(self, name, value)
                return

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

    class ElementContainer(_MutableSequence):
        __slots__ = ("_elements",)

        def __init__(self, initial=None):
            self._elements = list(initial) if initial is not None else []

        def insert(self, index, value):
            self._elements.insert(index, value)

        if PY2:
            def clear(self):
                del self._elements[:]

        def _add(self, item):
            if isinstance(item, (list, tuple)):
                self._elements.extend(item)
            else:
                self._elements.append(item)
            return self

        def _sub(self, item):
            items_to_remove = item if isinstance(item, (list, tuple)) else [item]
            for x in items_to_remove:
                while x in self._elements:
                    self._elements.remove(x)
            return self

        def __add__(self, item):
            self._add(item)

        def __sub__(self, item):
            self._sub(item)

        def __isub__(self, item):
            return self._sub(item)

        def __getitem__(self, index):
            if isinstance(index, slice):
                return self.__class__(self._elements[index])
            return self._elements[index]

        def __setitem__(self, index, value):
            self._elements[index] = value

        def __delitem__(self, index):
            del self._elements[index]

        def __len__(self):
            return len(self._elements)

        def __repr__(self):
            return "ElementContainer({})".format(self._elements)

init python in v1FNaSR:
    add_quit_fn(GlobalState.clear)

    debug.add_element(
        DebugSection(
            DebugText(lambda context: "GlobalState: {}".format(GlobalState.get_len()), style="v1_text_16_style_FNaSR"),
            DebugText(lambda context: "\n".join("'{}': {}".format(k, repr(v)) for k, v in GlobalState.items())),
            order=3
        ),
        group="System"
    )
