# other.rpy
init -10 python in v1FNaSR:              
    class GlobalState(object):
        _flags = dict()
        @classmethod
        def get(cls, key, default=None):
            return cls._flags.get(key, default)

        @classmethod
        def set(cls, key, value):
            cls._flags[key] = value

        @classmethod
        def clear(cls):
            cls._flags.clear()

        @classmethod
        def len(cls):
            return len(cls._flags)

        

    class _MissingType(object):
        """
        Sentinel для «значение не задано».
        Используется вместо None, чтобы не путать «нет дефолта» и «дефолт = None».
        """
        _instance = None

        def __new__(cls):
            if cls._instance is None:
                cls._instance = object.__new__(cls)
            return cls._instance

        def __repr__(self):
            return "<MISSING>"

        def __bool__(self):
            return False

        # Python 2
        __nonzero__ = __bool__

    MISSING = _MissingType()

    class InfoObject(object):
        def __init__(self, **kwargs):
            object.__setattr__(self, "_v1data", {})
            self.update(kwargs)

        # ---------------------------------------------------------
        # Attribute access
        # ---------------------------------------------------------

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

        # ---------------------------------------------------------
        # Dict-style access
        # ---------------------------------------------------------

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

        # ---------------------------------------------------------
        # Dict API
        # ---------------------------------------------------------

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

        # Python 2
        def iterkeys(self):
            return iter_keys(self._v1data)

        def itervalues(self):
            return iter_values(self._v1data)

        def iteritems(self):
            return iter_items(self._v1data)

        # ---------------------------------------------------------
        # Helpers
        # ---------------------------------------------------------

        def copy(self):
            return self.__class__(**self._v1data)

        def has_key(self, key):
            return key in self._v1data

        def __repr__(self):
            return "{0}({1!r})".format(
                self.__class__.__name__,
                self._v1data
            )

init python in v1FNaSR:
    add_quit_fn(GlobalState.clear)

    debug.add_element(DebugSection(
        DebugText(lambda context: "GlobalState: {}".format(GlobalState.len()), order=0, style="v1_text_16_style_FNaSR"),
        DebugText(lambda context: "\n".join("'{}': {}".format(k, repr(v)) for k, v in iter_items(GlobalState._flags)), order=1),
    order=3), group="System")

