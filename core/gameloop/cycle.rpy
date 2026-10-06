
# cycle.rpy
init -2 python in v1FNaSR:
    import sys as _sys
    import time as _time
    import threading as _threading
    import traceback as _traceback
    import collections as _collections

    def make_reset_method(default_dict):
        if not default_dict:
            return lambda self: None

        lines = []
        for attr, val in iter_items(default_dict):
            if isinstance(val, ResetLogic):
                lines.append("if self.%s is not None:" % attr)
                lines.append("    self.%s.reset()" % attr)

            elif isinstance(val, set):
                lines.append("self.%s.clear()" % attr)
                if val:
                    lines.append("self.%s.update(%r)" % (attr, val))

            elif isinstance(val, frozenset):
                lines.append("self.%s = %r" % (attr, val))

            elif isinstance(val, list):
                lines.append("del self.%s[:]" % attr)
                if val:
                    lines.append("self.%s.extend(%r)" % (attr, val))

            elif isinstance(val, dict):
                lines.append("self.%s.clear()" % attr)
                if val:
                    lines.append("self.%s.update(%r)" % (attr, val))

            else:
                lines.append("self.%s = %r" % (attr, val))

        code = "def reset(self):\n    " + "\n    ".join(lines)
        
        namespace = {}
        exec(code, namespace)
        return namespace['reset']

    class FNaSRCycleError(FNaSRRuntimeError):
        pass

    class CycleState(object):
        STOPPED = "stopped"
        STARTING = "starting"
        RUNNING = "running"
        STOPPING = "stopping"
        FAILED = "failed"

    class ErrorPolicy(object):
        LOG_AND_CONTINUE = "log_and_continue"
        DISABLE_OBJECT = "disable_object"
        STOP_CYCLE = "stop_cycle"

    class ResetLogic(object):
        """
        Класс для автоматической генерации метода reset для сброса состояния до первоначального при создании объекта
        _reset_to_default - это словарь на который опирается reset, содержание должно быть: 'attr': self.attr
        _reset_to_default должен сформироваться до первого вызова reset, желательно чтобы он был готов после __init__
        """
        __slots__ = ("_fast_reset", "_reset_to_default")

        def __init__(self):
            self._reset_to_default = dict()

        def _setattr(self, attr, val, use_object=False):
            if not hasattr(self, "_reset_to_default"):
                self._reset_to_default = dict()

            if use_object:
                object.__setattr__(self, attr, val)
            else:
                setattr(self, attr, val)

            default_val = getattr(self, attr)

            if isinstance(default_val, set):
                default_val = set(default_val)
            elif isinstance(default_val, list):
                default_val = list(default_val)
            elif isinstance(default_val, dict):
                default_val = dict(default_val)

            self._reset_to_default[attr] = default_val
            self._fast_reset = None

        def reset(self):
            fast_reset = getattr(self, "_fast_reset", None)
            if fast_reset is None:
                default = getattr(self, "_reset_to_default", None)
                if not isinstance(default, dict):
                    return

                fast_reset = make_reset_method(default)
                self._fast_reset = fast_reset

            try:
                fast_reset(self)
            except Exception as e:
                renpy.log("FNaSR | ResetLogic | fast_reset error: {}".format(e))
                raise

    class GameObject(ResetLogic):
        __slots__ = (
            "_accumulated_time",
            "_enabled",
            "_consecutive_errors",
            "current_refresh_time",
        )

        def __init__(self):
            super(GameObject, self).__init__()
            
            self._setattr("_accumulated_time", 0.0)
            self._setattr("_enabled", True)
            self.current_refresh_time = 0.0

        @property
        def enabled(self):
            return self._enabled

        @enabled.setter
        def enabled(self, value):
            self._enabled = bool(value)

        def start(self):
            pass

        def update(self):
            pass

        def tick_update(self, dt, refresh_time):
            self.current_refresh_time = refresh_time
            self._accumulated_time += dt

            while self._consume_refresh(refresh_time):
                self.update()

        def _consume_refresh(self, refresh_time):
            if refresh_time <= 0:
                raise FNaSRCycleError("'refresh_time' must be strictly positive.")

            if self._accumulated_time < refresh_time:
                return False

            self._accumulated_time -= refresh_time
            return True

        def on_error(self, exc_info):
            pass

    class GameCycle(object):
        def __init__(self, fps_controller, refresh_time=1.0,
                    error_policy=ErrorPolicy.DISABLE_OBJECT,
                    max_consecutive_errors=1):

            self._fps_controller = fps_controller
            self._refresh_time = refresh_time

            self._error_policy = error_policy
            self._max_consecutive_errors = max_consecutive_errors

            self._objects = list()
            self._pending_add = list()
            self._pending_remove = list()
            self._objects_lock = _threading.Lock()

            self._state = CycleState.STOPPED
            self._state_lock = _threading.RLock()

            self._stop_event = _threading.Event()
            self._thread = None
            self._run_in_current_thread = False

            self._error_log = _collections.deque(maxlen=200)
            self._fatal_exc_info = None

            self._freeze_event = _threading.Event()

        @property
        def fps(self):
            return self._fps_controller.current_fps

        @property
        def fps_controller(self):
            return self._fps_controller

        @property
        def refresh_time(self):
            return self._refresh_time

        @refresh_time.setter
        def refresh_time(self, value):
            value = float(value)

            if value <= 0:
                raise FNaSRCycleError("'refresh_time' must be strictly positive.")

            self._refresh_time = value

        # ---- object registry -------------------------------------------------

        def register(self, obj):
            if not hasattr(obj, "tick_update"):
                raise FNaSRAttributeError("объект '{}' должен иметь метод 'tick_update'".format(repr(obj)))
            with self._objects_lock:
                with self._state_lock:
                    running = self._state != CycleState.STOPPED
                if running:
                    if obj in self._objects or obj in self._pending_add:
                        raise FNaSRValueError("Объект '{0}' уже зарегистрирован".format(repr(obj)))
                    self._pending_add.append(obj)
                else:
                    if obj in self._objects:
                        raise FNaSRValueError("Объект '{0}' уже зарегистрирован".format(repr(obj)))
                    self._objects.append(obj)

        def unregister(self, obj):
            with self._objects_lock:
                with self._state_lock:
                    running = self._state != CycleState.STOPPED
                if running:
                    self._pending_remove.append(obj)
                else:
                    try:
                        self._objects.remove(obj)
                    except ValueError:
                        raise FNaSRValueError("Объект '{0}' не зарегистрирован".format(repr(obj)))

        def is_registered(self, obj):
            return (obj in self._objects and obj not in self._pending_remove) or (obj in self._pending_add and obj not in self._pending_remove)

        def _apply_pending_objects(self):
            with self._objects_lock:
                to_add, self._pending_add = self._pending_add, []
                to_remove, self._pending_remove = self._pending_remove, []
            for obj in to_add:
                if obj not in self._objects:
                    self._objects.append(obj)
                    self._safe_call(obj, "start")
            for obj in to_remove:
                if obj in self._objects:
                    self._objects.remove(obj)
                    self._safe_call(obj, "reset")

        # ---- error handling -----------------------------------------------

        def _safe_call(self, obj, method_name, *args):
            method = getattr(obj, method_name, None)
            if method is None:
                return
            try:
                method(*args)
            except Exception:
                self._handle_object_error(obj, _sys.exc_info())

        def _handle_object_error(self, obj, exc_info):
            text = "Объект {0} вызвал исключение:\n{1}".format(repr(obj), "".join(_traceback.format_exception(*exc_info)))
            self._error_log.append(text)

            on_error = getattr(obj, "on_error", None)
            if on_error is not None:
                try:
                    on_error(exc_info)
                except Exception:
                    self._error_log.append("on_error объекта {0} сам выбросил исключение:\n{1}".format(repr(obj), _traceback.format_exc()))

            if self._error_policy == ErrorPolicy.STOP_CYCLE:
                self._fatal_exc_info = exc_info
                self._stop_event.set()
                return

            if self._error_policy == ErrorPolicy.DISABLE_OBJECT:
                count = getattr(obj, "_consecutive_errors", 0) + 1
                try:
                    obj._consecutive_errors = count
                except Exception:
                    pass
                if count >= self._max_consecutive_errors:
                    try:
                        obj.enabled = False
                    except Exception:
                        pass

        @property
        def errors(self):
            return list(self._error_log)

        # ---- lifecycle ------------------------------------------------------

        @property
        def state(self):
            with self._state_lock:
                return self._state

        def start(self, threaded=True):
            with self._state_lock:
                self._error_log.clear()
                if self._state != CycleState.STOPPED:
                    raise FNaSRCycleError("Нельзя запустить GameCycle из состояния '{0}'".format(self._state))
                self._state = CycleState.STARTING
                self._stop_event.clear()
                self._fatal_exc_info = None

            if threaded:
                self._run_in_current_thread = False
                self._thread = ThreadWithCatch(target=self._run, name="FNaSR-GameCycle")
                self._thread.daemon = True
                self._thread.start()
            else:
                self._run_in_current_thread = True
                self._run()

        def stop(self, wait=False, timeout=None):
            error_text = None
            with self._state_lock:
                if self._error_log:
                    error_text = "\n".join(self._error_log)
                if self._state == CycleState.STOPPED:
                    return
                self._stop_event.set()
            if wait:
                self.join(timeout)

            if error_text:
                renpy.log("FNaSR | GameCycle Errors:\n{}".format(error_text))

        def join(self, timeout=None):
            if self._thread is not None and self._thread.is_alive():
                self._thread.join(timeout)

        @property
        def is_frozen(self):
            return self._freeze_event.is_set()

        def freeze(self):
            self._freeze_event.set()

        def unfreeze(self):
            self._freeze_event.clear()

        def _run(self):
            with self._state_lock:
                self._state = CycleState.STARTING

            for obj in list(self._objects):
                self._safe_call(obj, "start")

            if self._fatal_exc_info is None:
                with self._state_lock:
                    self._state = CycleState.RUNNING

                self._fps_controller.reset()

                try:
                    while not self._stop_event.is_set():
                        self._apply_pending_objects()
                        dt = self._fps_controller.tick()
                        is_frozen = self._freeze_event.is_set()

                        for obj in self._objects:
                            if self._stop_event.is_set() or is_frozen:
                                break
                            if getattr(obj, "enabled", True):
                                self._safe_call(obj, "tick_update", dt, self._refresh_time)

                        if self._fatal_exc_info is not None:
                            break
                except Exception:
                    self._fatal_exc_info = _sys.exc_info()

                with self._state_lock:
                    self._state = CycleState.STOPPING

                for obj in list(self._objects):
                    self._safe_call(obj, "reset")

            self._freeze_event.clear()

            with self._state_lock:
                if self._fatal_exc_info is not None:
                    self._state = CycleState.FAILED
                else:
                    self._state = CycleState.STOPPED

            if self._fatal_exc_info is not None:
                self._error_log.append("GameCycle перешёл в FAILED:\n" +"".join(_traceback.format_exception(*self._fatal_exc_info)))
                if self._run_in_current_thread:
                    reraise(*self._fatal_exc_info)

        # ---- Experimentally -----------------------------------------------

        def add_refresh_time(self, value=0.1):
            if not is_number(value):
                raise FNaSRValueError("value должен быть числом, пришло: {}".format(type(value)))

            if value > 0:
                self.refresh_time += float(value)

        def decrease_refresh_time(self, value=0.1):
            if not is_number(value):
                raise FNaSRValueError("value должен быть числом, пришло: {}".format(type(value)))

            if value <= 0:
                return

            new_value = self._refresh_time - float(value)

            if new_value <= 0.1:
                return

            self._refresh_time = new_value

    register_system("cycle", GameCycle(FPSController(60)))


init python in v1FNaSR:
    _dsc = DebugSection(
        DebugText(lambda context: "Cycle state: {}".format(context.cycle.state), order=0, style="v1_text_16_style_FNaSR"),
        DebugText(lambda context: "current fps: {:.2f}".format(context.cycle.fps), order=1),
        DebugText(lambda context: "target fps: {}".format(context.cycle.fps_controller.target_fps), order=2),
        DebugText(lambda context: "mode: {}".format("precise" if context.cycle.fps_controller.precise else "fast"), order=3),
        DebugText(lambda context: "dt: {}".format(context.cycle.fps_controller.dt), order=4),
        DebugText(lambda context: "errors: {}".format(len(context.cycle.errors)), order=5),
        DebugText(lambda context: "frozen: {}".format(context.cycle.is_frozen), order=6),
        DebugText(lambda context: "total obj: {}".format(len(context.cycle._objects)), order=7),
    condition=lambda context: context.cycle is not None, order=0)

    _bfc = DebugFold(
        "Cycle Control",
        DebugButton(
        lambda context: "Разморозить цикл" if context.cycle.is_frozen else "Заморозить цикл",
        lambda context: context.cycle.unfreeze() if context.cycle.is_frozen else context.cycle.freeze(),
        condition=lambda context: context.cycle is not None,
        order=1),
        DebugRow(
            DebugButton(lambda context: "+", lambda context: context.cycle.add_refresh_time()),
            DebugText(lambda context: "refresh time: {}".format(context.cycle.refresh_time), order=1),
            DebugButton(lambda context: "-", lambda context: context.cycle.decrease_refresh_time(), order=2),
        order=2),
        expanded=True
    )

    _cycle = require_system("cycle")
    _dsc.context.cycle = _cycle
    _bfc.context.cycle = _cycle

    debug.add_element(_dsc, group="System")
    debug.add_element(_bfc, group="System")

    del _cycle
    del _dsc
    del _bfc
