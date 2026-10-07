#compat.rpy
init -6 python in v1FNaSR:

    import sys as _sys

    PY2 = _sys.version_info[0] == 2
    PY3 = not PY2

    if PY2:
        import __builtin__ as _builtins_module
        from collections import Iterable
        import Queue # noqa: py2 stdlib
    else:
        import builtins as _builtins_module
        from collections.abc import Iterable
        import queue as Queue

    native_str = _builtins_module.str

    if PY2:
        text_type = _builtins_module.unicode  # noqa: F821
        integer_types = (_builtins_module.int, _builtins_module.long)  # noqa: F821
    else:
        text_type = _builtins_module.str
        integer_types = (_builtins_module.int,)

    if PY2:
        exec("""
def reraise(tp, value, tb=None):
    raise tp, value, tb
""")
    else:
        def reraise(tp, value, tb=None):
            if value is None:
                value = tp()
            if getattr(value, "__traceback__", None) is not tb:
                raise value.with_traceback(tb)
            raise value

    binary_type = bytes

    string_types = (native_str, text_type) if PY2 else (text_type,)

    def get_builtin(attr, default=None):
        """
        Возвращает атрибут builtins-модуля по имени.
        """
        return getattr(_builtins_module, attr, default)


    def to_text(value, errors="strict"):
        """
        Приводит произвольное значение к тексту (unicode в Py2, str в Py3).
        """
        if value is None:
            return text_type(value)

        if isinstance(value, text_type):
            return value

        if isinstance(value, binary_type):
            return value.decode("utf-8", errors)

        if PY2:
            to_unicode = getattr(value, "__unicode__", None)

            if to_unicode is not None:
                return to_unicode()

            return to_text(native_str(value), errors)

        return text_type(value)


    def to_bytes(value, encoding="utf-8", errors="strict"):
        """
        Приводит произвольное значение к байтам.
        """
        if isinstance(value, binary_type):
            return value

        if isinstance(value, text_type):
            return value.encode(encoding, errors)

        return to_bytes(to_text(value), encoding, errors)


    def iter_items(mapping):
        """
        Ленивый итератор по (key, value)-парам.
        """
        method = getattr(mapping, "iteritems", None)

        if method is not None:
            return method()

        return iter(mapping.items())


    def iter_keys(mapping):
        """Аналог iter_items() для ключей."""
        method = getattr(mapping, "iterkeys", None)

        if method is not None:
            return method()

        return iter(mapping.keys())


    def iter_values(mapping):
        """Аналог iter_values() для значений."""
        method = getattr(mapping, "itervalues", None)

        if method is not None:
            return method()

        return iter(mapping.values())


    def is_string(value):
        """
        isinstance(value, string_types), вынесенное в отдельную функцию
        ради читаемости вызывающего кода и единого места правки.
        """
        return isinstance(value, string_types)


    def is_integer(value):
        """isinstance(value, integer_types)."""
        return isinstance(value, integer_types)


    def is_strict_integer(value):
        """
        Как is_integer(), но отвергает bool.
        """
        return is_integer(value) and not isinstance(value, bool)

    def is_number(value):
        return is_strict_integer(value) or isinstance(value, float)

    def with_metaclass(meta, *bases):
        """
        Создаёт базовый класс с заданным метаклассом; работает одинаково
        в Python 2 и Python 3.

        Использование:

            class Foo(with_metaclass(MyMeta, Base1, Base2)):
                ...
        """
        class _MetaclassBridge(meta):
            def __new__(cls, name, this_bases, namespace):
                return meta(native_str(name), bases, namespace)

            if not PY2:
                @classmethod
                def __prepare__(cls, name, this_bases):
                    return meta.__prepare__(native_str(name), bases)

        return type.__new__(
            _MetaclassBridge,
            native_str("temporary_class"),
            (),
            {}
        )


    def get_mro(cls):
        mro = getattr(cls, "__mro__", None)

        if mro is not None:
            return mro

        result = []
        seen = set()

        def _walk(current):
            if current in seen:
                return

            seen.add(current)
            result.append(current)

            for base in getattr(current, "__bases__", ()):
                _walk(base)

        _walk(cls)

        return tuple(result)
