
# thread.rpy
init -1 python in v1FNaSR:
    import collections as _collections
    import threading as _threading
    import traceback as _traceback
    import functools as _functools
    import types as _types


    class FNaSRMainThreadError(FNaSRException): pass
    class FNaSRThreadError(FNaSRException): pass

    def is_main_thread(thread=None):
        if thread is None:
            thread = _threading.current_thread()
        try:
            return thread is _threading.main_thread()
        except AttributeError:
            return isinstance(thread, _threading._MainThread)

    def get_thread_list():
        return _threading.enumerate()

    _thread_exc_queue = _collections.deque()
    _thread_exc_lock = _threading.Lock()

    def _push_thread_exception(name, text):
        with _thread_exc_lock:
            _thread_exc_queue.append((name, text))

    def _pop_thread_exception():
        with _thread_exc_lock:
            if not _thread_exc_queue:
                return None

            return _thread_exc_queue.popleft()

    def _handle_thread_exceptions():
        item = _pop_thread_exception()

        if item is None:
            return True

        name, text = item

        raise FNaSRThreadError("{}\n\n{}".format(name, text))

    class ThreadWithCatch(_threading.Thread):
        def run(self):
            try:
                _threading.Thread.run(self)
            except Exception:
                _push_thread_exception(self.name, _traceback.format_exc())

    def _wrap_class_methods(cls, decorator):
        for name, value in cls.__dict__.items():
            if isinstance(value, _types.FunctionType):
                setattr(cls, name, decorator(value))
                continue

            if isinstance(value, staticmethod):
                fn = value.__get__(None, cls)
                setattr(cls, name, staticmethod(decorator(fn)))
                continue

            if isinstance(value, classmethod):
                bound = value.__get__(cls, cls)
                fn = getattr(bound, "im_func", None)

                if fn is None:
                    fn = getattr(bound, "__func__", None)

                setattr(cls, name, classmethod(decorator(fn)))

        return cls

    def main_thread_only(obj):
        if isinstance(obj, type):
            return _wrap_class_methods(obj, main_thread_only)
        @_functools.wraps(obj)
        def wrapper(*args, **kwargs):
            if not is_main_thread():
                raise FNaSRMainThreadError("Function '{}' must be called from main thread".format(obj.__name__))
            return obj(*args, **kwargs)
        return wrapper

    def not_main_thread(obj):
        if isinstance(obj, type):
            return _wrap_class_methods(obj, not_main_thread)
        @_functools.wraps(obj)
        def wrapper(*args, **kwargs):
            if is_main_thread():
                raise FNaSRMainThreadError("Function '{}' must not be called from the main thread".format(obj.__name__))
            return obj(*args, **kwargs)
        return wrapper

    start_mod = main_thread_only(start_mod)
    quit_mod = main_thread_only(quit_mod)

    # Я не добавлял renpy.audio.audio.* так как у них уже есть lock = threading.RLock(), так что в теории они потокобезопасные
    def _wrapped_fn():
        _store["old"]["renpy_show"] = renpy.show
        _store["old"]["renpy_hide"] = renpy.hide
        _store["old"]["renpy_show_screen"] = renpy.show_screen
        _store["old"]["renpy_hide_screen"] = renpy.hide_screen

        renpy.show = main_thread_only(renpy.show)
        renpy.hide = main_thread_only(renpy.hide)
        renpy.show_screen = main_thread_only(renpy.show_screen)
        renpy.hide_screen = main_thread_only(renpy.hide_screen)

    def _unwrapped_fn():
        renpy.show =        _store["old"]["renpy_show"]
        renpy.hide =        _store["old"]["renpy_hide"]
        renpy.show_screen = _store["old"]["renpy_show_screen"]
        renpy.hide_screen = _store["old"]["renpy_hide_screen"]

    add_start_fn(_wrapped_fn)
    add_quit_fn(_unwrapped_fn)
    del _wrapped_fn
    del _unwrapped_fn

init python in v1FNaSR:
    def _v1_thread_info_FNaSR(context):
        thread_list = get_thread_list()
        info = []
        for t in thread_list:
            cls_name = type(t).__name__
            if isinstance(t, ThreadWithCatch):
                cls_name = "{color=#AC6700}%s{/color}" % cls_name
            elif is_main_thread(t):
                cls_name = "{color=#9a9b99}%s{/color}" % cls_name
            elif isinstance(t, _threading.Thread):
                cls_name = "{color=#8b0000}%s{/color}" % cls_name
            info.append("%s(name={color=#7aa83a}'%s'{/color}, ident={color=#407cb4}%r{/color}, daemon={color=#235873}%r{/color}, alive{color=#235873}=%r{/color})" % (cls_name, t.name, t.ident, t.daemon, t.is_alive()))
        return "\n".join(info)

    debug.add_element(DebugSection(
        DebugText(lambda context: "threads: {color=#407cb4}%s{/color}" % len(get_thread_list()), order=0, style="v1_text_16_style_FNaSR"),
        DebugText(_v1_thread_info_FNaSR, order=1),
    order=2),group="System")

    del _v1_thread_info_FNaSR

    def update_ui():
        if is_main_thread():
            renpy.restart_interaction()
        else:
            main_executor.submit(renpy.restart_interaction)
