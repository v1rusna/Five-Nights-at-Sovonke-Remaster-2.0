# -*- coding: utf-8 -*-
# event.rpy
init -5 python in v1FNaSR:
    import _fnmatch
    import _threading

    class EventRecord(object):
        __slots__ = ("handler", "once", "priority", "id",)

        _counter = 0
        _counter_lock = _threading.Lock() 

        @classmethod
        def _get_id(cls):
            with cls._counter_lock:
                counter = EventRecord._counter
                EventRecord._counter += 1
            return counter

        def __init__(self, handler, once, priority):
            self.handler = handler
            self.once = once
            self.priority = priority
            self.id = self._get_id()


    class EventEmitter(object):
        def __init__(self):
            self._handlers = {}
            self._lock = _threading.RLock() 

        @property
        def patterns(self):
            with self._lock:
                return self._handlers.keys()

        def on(self, pattern, handler, priority=0):
            if not callable(handler):
                raise FNaSRTypeError("handler must be callable")

            rec = EventRecord(handler, False, priority)

            with self._lock:
                self._handlers.setdefault(pattern, []).append(rec)

        def once(self, pattern, handler, priority=0):
            if not callable(handler):
                raise FNaSRTypeError("handler must be callable")

            rec = EventRecord(handler, True, priority)

            with self._lock:
                self._handlers.setdefault(pattern, []).append(rec)

        def off(self, pattern=None, handler=None):
            """
            off() — удалить всё
            off(pattern) — удалить все обработчики такого паттерна
            off(pattern, handler) — удалить конкретный обработчик
            """
            with self._lock:
                if pattern is None:
                    self._handlers.clear()
                    return

                if pattern not in self._handlers:
                    return

                if handler is None:
                    del self._handlers[pattern]
                    return

                lst = self._handlers[pattern]
                new_list = [r for r in lst if r.handler is not handler]
                if new_list:
                    self._handlers[pattern] = new_list
                else:
                    del self._handlers[pattern]

        def clear(self):
            with self._lock:
                self._handlers.clear()


        def emit(self, event_name, *args, **kwargs):
            """
            Возвращает список результатов обработчиков.
            """
            with self._lock:
                matches = []

                for pattern, handlers in self._handlers.items():
                    if _fnmatch.fnmatchcase(event_name, pattern):
                        for rec in handlers:
                            matches.append(rec)

                matches.sort(key=lambda r: (-r.priority, r.id))

            if not matches:
                return []

            results = []
            to_remove = []

            for rec in matches:
                try:
                    res = rec.handler(*args, **kwargs)
                    results.append(res)
                except Exception:
                    raise

                if rec.once:
                    to_remove.append(rec)

            if to_remove:
                with self._lock:
                    for rec in to_remove:
                        for pattern, lst in list(self._handlers.items()):
                            if rec in lst:
                                lst.remove(rec)
                                if not lst:
                                    del self._handlers[pattern]

            return results

