# -*- coding: utf-8 -*-
# core/say/core.rpy
init -1 python in v1FNaSR:
    import random as _random
    import threading as _threading
    import uuid as _uuid

    class _Ticker(object):
        SCREEN = "v1_text_ticker_screen_FNaSR"
        _lock = _threading.RLock()
        _shown = False

        @classmethod
        def _call(cls, fn, *args):
            if is_main_thread():
                fn(*args)
            else:
                main_executor.submit(fn, *args)

        @classmethod
        def sync(cls):
            with cls._lock:
                need = bool(BlockText._blocks) or bool(TextSegment._active)
                if need == cls._shown:
                    return
                cls._shown = need
                if need:
                    cls._call(renpy.show_screen, cls.SCREEN)
                else:
                    cls._call(renpy.hide_screen, cls.SCREEN)

    class TextTimer(native_object):
        _lock = _threading.RLock()
        _timers = set()

        @classmethod
        def start_timer(cls, callback, delay, *args, **kwargs):
            timer = cls(callback, delay, *args, **kwargs)
            timer.start()
            return timer

        @classmethod
        def cancel_all(cls):
            with cls._lock:
                timers = list(cls._timers)
            for timer in timers:
                timer.cancel()

        def __init__(self, callback, delay, *args, **kwargs):
            self._callback = callback
            self._delay = max(0.0, float(delay))
            self._args = args
            self._kwargs = kwargs
            self._event = _threading.Event()
            self._state = "new"  # new -> running -> done / cancelled
            self._thread = None

        def start(self):
            with self._lock:
                if self._state != "new":
                    return self
                self._state = "running"
                self._timers.add(self)
                self._thread = ThreadWithCatch(
                    target=self._run,
                    name="FNaSR-TextTimer-{}".format(hex(id(self)))
                )
                self._thread.daemon = True
                self._thread.start()
            return self

        def cancel(self):
            with self._lock:
                if self._state not in ("new", "running"):
                    return False
                self._state = "cancelled"
                self._timers.discard(self)
                self._event.set()
            self._release()
            return True

        @property
        def is_active(self):
            return self._state == "running"

        @not_main_thread
        def _run(self):
            self._event.wait(self._delay)
            with self._lock:
                if self._state != "running":
                    return
                self._state = "done"
                self._timers.discard(self)
            try:
                self._callback(*self._args, **self._kwargs)
            finally:
                self._release()

        def _release(self):
            self._callback = None
            self._args = ()
            self._kwargs = {}

    class TextSegment(native_object):
        _lock = _threading.RLock()
        _active = set()  # сегменты, которые сейчас на экране (в т.ч. затухающие)

        @classmethod
        def hide_all(cls, fast_hide=True):
            with cls._lock:
                segments = list(cls._active)
            for segment in segments:
                segment.hide(fast_hide=fast_hide)

        def __init__(
            self,
            text,
            pause=0,
            decay_time=0,
            appearance_time=0,
            lifetime=6,
            align=None,
            rotate=0
        ):
            if align is None:
                align = (_random.uniform(0.2, 0.8), _random.uniform(0.2, 0.8))

            self.text = str(text)
            self.align = align
            self.rotate = rotate

            self.pause = float(pause)
            self.decay_time = float(decay_time)
            self.appearance_time = float(appearance_time)
            self.lifetime = float(lifetime)

            self._key = "v1_text_{}_FNaSR".format(_uuid.uuid4().hex)

            self._state = "idle"  # idle / shown / hiding
            self._lifetime_timer = None
            self._decay_timer = None

        def show(self):
            with self._lock:
                self._cancel_timers()

                if self._state != "idle":
                    self._hide_screen(self._key)

                # Новый тег на каждый показ: старое скрытие не заденет новый экран
                self._key = "v1_text_{}_FNaSR".format(_uuid.uuid4().hex)

                self._state = "shown"
                self._active.add(self)

                self._show_screen(self.decay_time, "show")

                if self.lifetime > 0:
                    self._lifetime_timer = TextTimer.start_timer(self.hide, self.lifetime)

                _Ticker.sync()

        def hide(self, fast_hide=False):
            with self._lock:
                if self._state == "idle":
                    return
                if self._state == "hiding" and not fast_hide:
                    return

                self._cancel_timers()

                if fast_hide or self.decay_time <= 0:
                    self._finish_hide()
                    return

                self._state = "hiding"
                self._show_screen(self.decay_time, "hide")
                self._decay_timer = TextTimer.start_timer(
                    self._finish_hide, self.decay_time, True
                )

        def _finish_hide(self, only_if_hiding=False):
            with self._lock:
                if only_if_hiding and self._state != "hiding":
                    return
                self._state = "idle"
                self._active.discard(self)
                self._decay_timer = None
                self._hide_screen(self._key)
                _Ticker.sync()

        def _cancel_timers(self):
            if self._lifetime_timer is not None:
                self._lifetime_timer.cancel()
                self._lifetime_timer = None
            if self._decay_timer is not None:
                self._decay_timer.cancel()
                self._decay_timer = None

        def _show_screen(self, decay_time, state):
            main_executor.submit(
                renpy.show_screen,
                "v1_text_screen_FNaSR",
                text=self.text,
                align=self.align,
                rotate=self.rotate,
                appearance_time=self.appearance_time,
                decay_time=decay_time,
                state=state,
                _tag=self._key
            )

        def _hide_screen(self, *args, **kwargs):
            main_executor.submit(renpy.hide_screen, *args, **kwargs)

    class BlockText(native_object):
        _lock = _threading.RLock()
        _blocks = set()

        @classmethod
        def stop_all(cls):
            with cls._lock:
                blocks = list(cls._blocks)
            for block in blocks:
                block.stop()

        def __init__(self, *text_list):
            for text in text_list:
                if not isinstance(text, TextSegment):
                    raise FNaSRTypeError("All items must be TextSegment")

            self._text_list = list(text_list)
            self._index = 0
            self._running = False
            self._generation = 0
            self._timer = None

        def start(self):
            with self._lock:
                self._cancel_timer()
                self._generation += 1
                self._running = True
                self._index = 0
                self._blocks.add(self)

                for text in self._text_list:
                    text.hide(fast_hide=True)

                _Ticker.sync()
                self._show_next(self._generation)

        def resume(self):
            with self._lock:
                if self._running:
                    return
                self._generation += 1
                self._running = True
                self._blocks.add(self)
                _Ticker.sync()
                self._show_next(self._generation)

        def stop(self, hide=True):
            with self._lock:
                self._running = False
                self._generation += 1
                self._cancel_timer()
                self._blocks.discard(self)
                if hide:
                    for text in self._text_list:
                        text.hide(fast_hide=True)

                _Ticker.sync()

        def _show_next(self, generation):
            with self._lock:
                if not self._running or generation != self._generation:
                    return

                self._timer = None

                if self._index >= len(self._text_list):
                    self._running = False
                    self._blocks.discard(self)
                    _Ticker.sync()
                    return

                text = self._text_list[self._index]
                self._index += 1
                text.show()

                self._timer = TextTimer.start_timer(self._show_next, text.pause, generation)

        def _cancel_timer(self):
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def hide_all_text():
        BlockText.stop_all()
        TextSegment.hide_all(fast_hide=True)
        TextTimer.cancel_all()
        _Ticker.sync()

    add_quit_fn(TextTimer.cancel_all)

    class TextManagerObject(GameObject):
        def reset(self):
            hide_all_text()

    require_system("cycle").register(TextManagerObject())


transform v1_show_st_FNaSR(time=1.0, angle=0):
    alpha 0.0
    rotate angle
    easein time alpha 1.0
transform v1_hide_st_FNaSR(time=1.0, angle=0):
    alpha 1.0
    rotate angle
    easeout time alpha 0.0

screen v1_text_screen_FNaSR(
        text,
        align=(0.5, 0.5),
        rotate=0,
        appearance_time=0.0,
        decay_time=0.0,
        state="show"
    ):
    text text:
        style "v1_text_24_style_FNaSR"
        align align
        at (v1_show_st_FNaSR(appearance_time, rotate) if state == "show" else v1_hide_st_FNaSR(decay_time, rotate))

screen v1_text_ticker_screen_FNaSR():
    timer 0.05 repeat True action (Function(renpy.restart_interaction))




