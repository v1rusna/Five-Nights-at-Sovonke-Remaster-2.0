# time.rpy
init python in v1FNaSR:
    import traceback as _traceback

    class Clock(ResetLogic):
        def __init__(self, start_hour=0):
            super(Clock, self).__init__()
            self._start_hour = start_hour
            self._hour = self._start_hour % 24

        @property
        def hour(self):
            return self._hour

        def set_hour(self, hour):
            if not is_integer(hour):
                raise FNaSRTypeError("hour должен быть целым числом, получено: {}".format(type(hour)))
            if not 0 <= hour < 24:
                raise FNaSRValueError("hour должен быть в диапазоне 0...23")
            self._hour = hour

        def next_hour(self, step=1):
            self._hour += int(step)
            self._hour = self._hour % 24

        def previous_hour(self, step=1):
            self._hour = (self._hour - int(step)) % 24

        def get_time(self):
            if self._hour == 0:
                return "12 AM"  # Полночь
            elif self._hour < 12:
                return "{} AM".format(self._hour)  # Утро
            elif self._hour == 12:
                return "12 PM"  # Полдень
            else:
                return "{} PM".format(self._hour - 12)  # День/Вечер (например, 13 -> 1 PM)

        def reset(self):
            self._hour = self._start_hour % 24

    class Timer(ResetLogic):
        MAX_REPETITIONS = 10
        def __init__(self, fn, seconds, repetitions=1):
            if not callable(fn):
                raise FNaSRTypeError("fn должен быть вызываемым, передано: {}.".format(type(fn)))

            super(Timer, self).__init__()

            self._fn = fn

            self.set_seconds(seconds)
            self.set_repetitions(repetitions)

            self._setattr("_seconds", self._seconds)
            self._setattr("_repetitions", self._repetitions)
            self._setattr("_current_time", 0.0)
            self._setattr("_pause", False)

        @property
        def seconds(self):
            return self._seconds

        @property
        def repetitions(self):
            return self._repetitions

        @property
        def is_worked(self):
            return self._repetitions <= 0

        @property
        def is_paused(self):
            return self._pause

        @property
        def elapsed(self):
            return self._current_time

        @property
        def remaining(self):
            return max(0.0, self._seconds - self._current_time)

        def set_seconds(self, seconds):
            if not is_number(seconds):
                raise FNaSRTypeError("seconds должен быть числом, передано: {}.".format(type(seconds)))
            if seconds <= 0:
                raise FNaSRValueError("seconds не может быть меньше или равным нулю")
            self._seconds = seconds

        def set_repetitions(self, repetitions):
            if not is_integer(repetitions):
                raise FNaSRTypeError("repetitions должен быть целым числом, передано: {}.".format(type(repetitions)))

            if repetitions <= 0 or repetitions > self.MAX_REPETITIONS:
                raise FNaSRValueError("repetitions не может быть меньше одного или больше {}".format(self.MAX_REPETITIONS))

            self._repetitions = repetitions

        def pause(self):
            self._pause = True

        def resume(self):
            self._pause = False

        def update(self, dt):
            if self._pause:
                return
            self._current_time += dt

            while self._current_time >= self._seconds:
                self._current_time -= self._seconds
                self._fn()
                self._repetitions -= 1
                if self._repetitions <= 0:
                    return

        def __repr__(self):
            return "Timer(fn={}, seconds={}, repetitions={})".format(
                repr(self._fn),
                self._seconds,
                self._repetitions
            )

    class GameTime(GameObject):
        def __init__(self):
            super(GameTime, self).__init__()

            self._setattr("_clock", Clock())
            self._setattr("_timers", list())
            self._setattr("_error_timers", dict())
            self._setattr("_total_hours", 0)
            self._setattr("_hour_time", 89)

        @property
        def clock(self):
            return self._clock

        @property
        def error_timers(self):
            return list(self._error_timers.items())

        @property
        def progress(self):
            hour_time = self._hour_time * self.current_refresh_time
            return self._accumulated_time / float(hour_time)

        @property
        def timers(self):
            return list(self._timers)

        @property
        def total_hours(self):
            return self._total_hours

        def set_time(self, hour, minutes=0):
            if not is_integer(hour):
                raise FNaSRTypeError("hour должен быть целым числом, передано: {}.".format(type(hour)))

            if not is_number(minutes):
                raise FNaSRTypeError("minutes должен быть числом, передано: {}.".format(type(minutes)))

            extra_hours, remaining_minutes = divmod(minutes, 60)
            
            final_hour = (hour + int(extra_hours)) % 24

            self._clock.set_hour(final_hour)
            hour_time = self._hour_time * self.current_refresh_time
            self._accumulated_time = (float(remaining_minutes) / 60.0) * hour_time
        
        def get_time(self):
            minutes = self.get_minutes()
            return "{:02d}:{:02d}".format(self._clock.hour, minutes)

        def get_minutes(self, step=1):
            hour_time = self._hour_time * self.current_refresh_time
            minutes = self._accumulated_time * 60 / hour_time
            if step > 1:
                minutes = int(minutes // step * step)
            return int(minutes)


        def timer(self, fn, seconds, repetitions=1):
            timer = Timer(fn, seconds, repetitions)
            self.add_timer(timer)
            return timer

        def add_timer(self, timer):
            if not isinstance(timer, Timer):
                raise FNaSRTypeError("timer должен быть 'Timer', пришло: {}".format(type(timer)))
            self._timers.append(timer)

        def remove_timer(self, timer):
            try:
                self._timers.remove(timer)
            except ValueError:
                raise FNaSRValueError("Таймер '{}' не найден".format(repr(timer)))

        def has_timer(self, timer):
            return timer in self._timers

        def recover_timer(self, timer):
            if not timer in self._timers:
                raise FNaSRValueError("Таймер '{}' не найден".format(repr(timer)))

            return self._error_timers.pop(timer, None)


        def start(self):
            self._error_timers.clear()

        def tick_update(self, dt, refresh_time):
            self.current_refresh_time = refresh_time
            self.update(dt)

        def update(self, dt):
            new_status = False
            self._accumulated_time += dt

            hour_time = self._hour_time * self.current_refresh_time

            log("---"*10)
            log("accumulated_time: {}".format(self._accumulated_time))
            log("hour_time: {}".format(hour_time))
            log("---"*10)

            while self._accumulated_time >= hour_time:
                self._accumulated_time -= hour_time
                self._clock.next_hour()
                self._total_hours += 1
                new_status = True

            if new_status:
                update_ui()

            for timer in tuple(self._timers):
                if timer in self._error_timers or timer.is_worked:
                    continue

                try:
                    timer.update(dt)
                except Exception:
                    self._error_timers[timer] = _traceback.format_exc()

    register_system("time", GameTime())
    _cycle = get_system("cycle")
    if _cycle is not None:
        _cycle.register(require_system("time"))
    del _cycle

init python in v1FNaSR:
    _dst = DebugSection(
        DebugText(lambda context: "Время: {}".format(context.gt.get_time()), style="v1_text_16_style_FNaSR"),
        DebugText(lambda context: "Таймеров: {}".format(len(context.gt.timers)), order=1),
        DebugText(lambda context: "Сломанных таймеров: {}".format(len(context.gt.error_timers)), order=2),
        DebugText(lambda context: "Прогресс часа: {:.1f}".format(context.gt.progress), order=3),
        DebugText(lambda context: "Всего часов: {}".format(context.gt.total_hours), order=4),
    order=1)

    _dst.context.gt = require_system("time")

    debug.add_element(_dst, group="Night")

    del _dst

