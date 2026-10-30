# visual.rpy
init python in v1FNaSR:
    import threading as _threading

    # EXPERIMENTAL
    class Visual(object):
        __slots__ = ("_elements", "_lock",)

        def __init__(self):
            self._elements = dict()
            self._lock = _threading.RLock()

        @staticmethod
        def _get_tag(name, kwargs):
            tag = kwargs.get("tag")

            if tag is None:
                tag = name.split(" ", 1)[0]

            return tag

        def _get_key(self, name, kwargs):
            return (kwargs.get("layer"), self._get_tag(name, kwargs))

        def get(self, tag, layer):
            with self._lock:
                return self._elements.get((layer, tag))

        @main_thread_only
        def show(self, name, **kwargs):
            key = self._get_key(name, kwargs)

            with self._lock:
                renpy.show(name, **kwargs)
                self._elements[key] = name

        @main_thread_only
        def ensure_shown(self, name, **kwargs):
            key = self._get_key(name, kwargs)

            with self._lock:
                if key not in self._elements:
                    self.show(name, **kwargs)

        @main_thread_only
        def has_layer(self, layer):
            with self._lock:
                return any(key[0] == layer for key in self._elements)

        @main_thread_only
        def hide(self, name, transition=None, **kwargs):
            key = self._get_key(name, kwargs)

            with self._lock:
                renpy.hide(name, **kwargs)
                self._elements.pop(key, None)

                if transition is not None:
                    renpy.with_statement(transition)

        @main_thread_only
        def hide_all(self, transition=None):
            with self._lock:
                for layer, tag in tuple(self._elements):
                    renpy.hide(tag, layer=layer)
                    del self._elements[(layer, tag)]
                if transition is not None:
                    renpy.with_statement(transition)

        @main_thread_only
        def hide_layer(self, layer):
            with self._lock:
                elements = tuple(self._elements.items())

                for (l, tag), name in elements:
                    if l == layer:
                        renpy.hide(tag, layer=l)
                        del self._elements[(l, tag)]

        def clear(self):
            with self._lock:
                self._elements.clear()

        def get_elements(self, layer=MISSING):
            with self._lock:
                return tuple(
                    (name, l, tag)
                    for (l, tag), name in self._elements.items()
                    if layer is MISSING or layer == l
                )

        def is_show(self, name, layer=MISSING, tag=MISSING,):
            if tag is MISSING:
                tag = name.split(" ", 1)[0]

            with self._lock:
                if layer is not MISSING:
                    return self._elements.get((layer, tag)) == name

                return any(t == tag and n == name
                            for (l, t), n in self._elements.items())

        def has_layer(self, layer):
            with self._lock:
                return any(
                    l == layer
                    for l, tag in self._elements
                )

        def items(self):
            with self._lock:
                return iter_items(tuple(self._elements.items()))

        def keys(self):
            with self._lock:
                return iter_keys(tuple(self._elements.keys()))

        def values(self):
            with self._lock:
                return iter_values(tuple(self._elements.values()))

        def __contains__(self, name):
            if isinstance(name, (list, tuple)):
                if not len(name) or len(name) > 3:
                    return False
                return self.is_show(*name)
            return self.is_show(name)

        def __len__(self):
            with self._lock:
                return len(self._elements)

        def __iter__(self):
            with self._lock:
                return iter(tuple(self._elements))

        def __repr__(self):
            with self._lock:
                return "{}({!r})".format(type(self).__name__, self._elements)

        def __bool__(self):
            return len(self) > 0

        __nonzero__ = __bool__

    visual = Visual()

    add_quit_fn(visual.hide_all)
