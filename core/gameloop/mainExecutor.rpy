# mainExecutor.rpy
init python in v1FNaSR:
    import threading as _threading
    import collections as _collections
    import sys as _sys

    def dump_renpy_exception_classes():
        for modname in ("renpy.game", "renpy.exports", "renpy.display.core", "renpy.execution"):
            module = _sys.modules.get(modname)
            if module is None:
                continue
            for name in sorted(dir(module)):
                obj = getattr(module, name, None)
                if isinstance(obj, type) and issubclass(obj, BaseException):
                    print("{} :: {}.{} <- {}".format(
                        modname, obj.__module__, name, ", ".join(b.__name__ for b in obj.__bases__)))
        print("v1FNaSR control: " + ", ".join(c.__name__ for c in _CONTROL_EXCEPTIONS))

    def _discover_control_exceptions():
        game = renpy.game
        found = []
        for name in dir(game):
            obj = getattr(game, name, None)
            if (isinstance(obj, type)
                    and issubclass(obj, BaseException)
                    and obj.__module__ == game.__name__):
                found.append(obj)
        return tuple(found)

    class FNaSRExecutorClosedError(FNaSRException):
        pass

    class FNaSRControlTransferError(FNaSRException):
        def __init__(self, original):
            FNaSRException.__init__(self, "Задача прервана управляющим исключением Ren'Py: {}".format(type(original).__name__))
            self.original = original

    class ControlExceptionRegistry(object):
        _FORBIDDEN_MODULES = ("builtins", "__builtin__", "exceptions")

        def __init__(self, base):
            base = tuple(base)
            if not base:
                raise FNaSRException("Не найдены управляющие исключения в renpy.game: MainThreadExecutor не сможет корректно передавать управление сценарием.")
            self._lock = _threading.Lock()
            self._base = base
            self._user = ()
            self._snapshot = base

        def _validate(self, cls):
            if not (isinstance(cls, type) and issubclass(cls, BaseException)):
                raise FNaSRTypeError("Управляющее исключение должно быть классом-наследником BaseException, а не '{}'".format(cls))
            if cls.__module__ in self._FORBIDDEN_MODULES:
                raise FNaSRTypeError("Встроенный класс '{}' нельзя объявить управляющим: он перехватил бы обычные ошибки пользовательского кода".format(cls.__name__))
            if isinstance(cls, FNaSRException):
                raise FNaSRTypeError("Класс '{}' наследуется от 'FNaSRException'".format(cls.__name__))

        def register(self, *classes):
            for cls in classes:
                self._validate(cls)
            with self._lock:
                added = [c for c in classes if c not in self._base and c not in self._user]
                if added:
                    self._user = self._user + tuple(added)
                    self._snapshot = self._base + self._user

        def unregister(self, cls):
            with self._lock:
                if cls in self._base:
                    raise FNaSRTypeError("Базовое исключение '{}' нельзя снять с регистрации".format(cls.__name__))
                if cls not in self._user:
                    raise FNaSRException("Исключение '{}' не зарегистрировано".format(cls.__name__))
                self._user = tuple(c for c in self._user if c is not cls)
                self._snapshot = self._base + self._user

        def types(self):
            return self._snapshot

        def base_types(self):
            return self._base

        def user_types(self):
            return self._user

        def is_control(self, exc):
            return isinstance(exc, self._snapshot)

    control_exceptions = ControlExceptionRegistry(_discover_control_exceptions())

    def control_exception(cls):
        control_exceptions.register(cls)
        return cls

    class MainThreadExecutor(object):
        def __init__(self):
            self._queue = _collections.deque()
            self._lock = _threading.Lock()

        def submit(self, fn, *args, **kwargs):
            if not callable(fn):
                raise FNaSRTypeError("fn должен быть вызываемым объектом, а не '{}'".format(type(fn)))

            future = _Future()

            with self._lock:
                if not is_initialized():
                    raise FNaSRExecutorClosedError("Мод не был запущен, использование MainThreadExecutor невозможно")

                self._queue.append((future, fn, args, kwargs))

            return future

        def run_pending(self):
            if not is_main_thread():
                raise FNaSRMainThreadError("run_pending() must not be called from anywhere other than the main thread.")
            while True:
                with self._lock:
                    if not self._queue:
                        return
                    future, fn, args, kwargs = self._queue.popleft()
                try:
                    result = fn(*args, **kwargs)
                except control_exceptions.types() as exc:
                    future._set_interrupted(exc)
                    raise
                except Exception as exc:
                    future._set_exception(exc)
                except BaseException as exc:
                    future._set_interrupted(exc)
                    raise
                else:
                    future._set_result(result)

        def submit_and_wait(self, fn, *args, **kwargs):
            if is_main_thread():
                raise FNaSRMainThreadError("submit_and_wait() cannot be called from main thread.")
            future = self.submit(fn, *args, **kwargs)
            return future.result()

        def clear(self):
            with self._lock:
                while self._queue:
                    future, fn, args, kwargs = self._queue.popleft()
                    future._set_exception(FNaSRExecutorClosedError("MainThreadExecutor был остановлен."))

    class _Future(object):
        def __init__(self):
            self._event = _threading.Event()
            self._result = None
            self._exception = None

        def _set_result(self, value):
            self._result = value
            self._event.set()

        def _set_exception(self, exc):
            self._exception = exc
            self._event.set()

        def _set_interrupted(self, exc):
            self._exception = FNaSRControlTransferError(exc)
            self._event.set()

        def result(self, timeout=None):
            if not self._event.wait(timeout):
                raise FNaSRTimeoutError("Future result timed out.")
            if self._exception is not None:
                raise self._exception
            return self._result

        def done(self):
            return self._event.is_set()

    main_executor = MainThreadExecutor()

    class ExecutorPump(renpy.Displayable):
        def render(self, width, height, st, at):
            renpy.redraw(self, 0.05)
            main_executor.run_pending()
            return renpy.Render(0, 0)

        def event(self, ev, x, y, st):
            return None

    class PumpContext(object):
        def __init__(self):
            self._refs = 0
            self._lock = _threading.Lock()

        @property
        def active(self):
            with self._lock:
                return self._refs > 0

        @main_thread_only
        def start(self):
            with self._lock:
                self._refs += 1
                first = self._refs == 1

            if first:
                renpy.show_screen("V1ExecutorPumpScreenFNaSR")
                renpy.pause(0.0)

        @main_thread_only
        def stop(self):
            with self._lock:
                if self._refs == 0:
                    return

                self._refs -= 1

                if self._refs != 0:
                    return

            renpy.hide_screen("V1ExecutorPumpScreenFNaSR")

        def __enter__(self):
            self.start()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.stop()
            return False

    pump_context = PumpContext()

    def _v1_start_pump_context():
        while not pump_context.active:
            pump_context.start()

    def _v1_stop_pump_context():
        while pump_context.active:
            pump_context.stop()

    add_start_fn(main_executor.clear)
    add_start_fn(_v1_start_pump_context)

    add_quit_fn(main_executor.clear)
    add_quit_fn(_v1_stop_pump_context)

    del _v1_start_pump_context
    del _v1_stop_pump_context

init:
    screen V1ExecutorPumpScreenFNaSR:
        add v1FNaSR.ExecutorPump()
