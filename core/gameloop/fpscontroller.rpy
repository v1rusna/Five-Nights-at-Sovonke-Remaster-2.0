# fpscontroller.rpy
init -6 python in v1FNaSR:
    from __future__ import division
    
    import sys as _sys
    import time as _time

    _FPS_MIN = 1
    _FPS_MAX = 10000
    _MAX_FRAME_TIME = 10.0
    _BUSY_WAIT_LIMIT = 500000          # аварийный fallback по итерациям
    _BUSY_WAIT_TIME_LIMIT_S = 0.05     # основной лимит: не крутиться дольше 50мс

    if hasattr(_time, "perf_counter"):
        _perf_counter = _time.perf_counter
    else:
        _perf_counter = getattr(_time, "clock", _time.time)

    _sleep = _time.sleep

    def _validate_fps(value, name="target_fps"):
        if not is_integer(value):
            raise TypeError("{name} must be an integer, got {tp}".format(name=name, tp=type(value).__name__))
        if not (_FPS_MIN <= value <= _FPS_MAX):
            raise ValueError("{name} must be between {lo} and {hi}, got {val}".format(name=name, lo=_FPS_MIN, hi=_FPS_MAX, val=value))

    def get_target_dt(target_fps):
        if target_fps <= 0:
            return 0.0 
        return 1.0 / target_fps

    # Я писал FPSController для другого проекта, но попал сюда в немного измененном виде
    class FPSController(object):
        MIN_BUSY_WAIT_S = 0.0002
        SLEEP_MARGIN_S = 0.001
        SMALL_SLEEP_STEP_S = 0.0005
        FPS_WINDOW_S = 1.0
        DEADLINE_RESET_THRESHOLD_S = 0.5

        __slots__ = (
            "_target_frame_time",
            "_frame_start",
            "_fps_window_start",
            "_fps_frame_count",
            "_precise",
            "dt",
            "current_fps",
        )

        def __init__(self, target_fps=30, precise=True):
            _validate_fps(target_fps)
            now = _perf_counter()
            self._target_frame_time = 1.0 / target_fps
            self._frame_start = now
            self._fps_window_start = now
            self._fps_frame_count = 0
            self._precise = bool(precise)
            self.dt = 0.0
            self.current_fps = 0.0

        def set_fps(self, target_fps):
            _validate_fps(target_fps)
            self._target_frame_time = 1.0 / target_fps

        def _get_target_fps(self):
            return 1.0 / self._target_frame_time

        def _set_target_fps(self, value):
            self.set_fps(value)

        target_fps = property(_get_target_fps, _set_target_fps)

        def _get_precise(self):
            return self._precise

        def _set_precise(self, value):
            self._precise = bool(value)

        precise = property(_get_precise, _set_precise)

        def tick(self):
            perf_counter = _perf_counter
            target_ft = self._target_frame_time
            deadline = self._frame_start + target_ft

            now = perf_counter()
            overdue = now - deadline
            if overdue > self.DEADLINE_RESET_THRESHOLD_S:
                self._frame_start = now
                deadline = now + target_ft

            if self._precise:
                self._wait_precise(perf_counter, deadline)
            else:
                self._wait_simple(deadline)

            now = perf_counter()
            raw_dt = now - self._frame_start
            self.dt = max(0.0, min(raw_dt, _MAX_FRAME_TIME))
            self._frame_start = now

            self._fps_frame_count += 1
            window = now - self._fps_window_start
            if window >= self.FPS_WINDOW_S:
                if window > 0.0:
                    self.current_fps = self._fps_frame_count / window
                self._fps_frame_count = 0
                self._fps_window_start = now

            return self.dt

        def _wait_precise(self, perf_counter, deadline):
            min_busy = self.MIN_BUSY_WAIT_S
            margin = self.SLEEP_MARGIN_S
            step = self.SMALL_SLEEP_STEP_S

            remaining = deadline - perf_counter()
            bulk = remaining - margin - min_busy
            if bulk > 0.0:
                _sleep(bulk)

            remaining = deadline - perf_counter()
            while remaining > min_busy:
                chunk = remaining - min_busy
                _sleep(step if chunk > step else chunk)
                remaining = deadline - perf_counter()

            busy_deadline = perf_counter() + _BUSY_WAIT_TIME_LIMIT_S
            iterations = 0
            while perf_counter() < deadline:
                iterations += 1
                if iterations >= _BUSY_WAIT_LIMIT:
                    break
                if perf_counter() >= busy_deadline:
                    break

        def _wait_simple(self, deadline):
            remaining = deadline - _perf_counter()
            if remaining > 0.0:
                _sleep(remaining)

        def reset(self):
            now = _perf_counter()
            self._frame_start = now
            self._fps_window_start = now
            self._fps_frame_count = 0
            self.dt = 0.0
            self.current_fps = 0.0

        def __repr__(self):
            mode = "precise" if self._precise else "fast"
            return (
                "FPSController(target={target:.0f}fps, current={current:.1f}fps, "
                "dt={dt:.2f}ms, mode={mode})".format(
                    target=self._get_target_fps(),
                    current=self.current_fps,
                    dt=self.dt * 1000.0,
                    mode=mode,
                )
            )
