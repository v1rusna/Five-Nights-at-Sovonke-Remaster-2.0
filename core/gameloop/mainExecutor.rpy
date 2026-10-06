# mainExecutor.rpy
init python in v1FNaSR:
    import threading as _threading
    import collections as _collections

    class FNaSRExecutorClosedError(FNaSRException):
        pass

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
                except BaseException as exc:
                    future._set_exception(exc)
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
            main_executor.run_pending()
            renpy.redraw(self, 0.05) 
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
