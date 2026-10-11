# modules.rpy
init -2 python in v1FNaSR:
    def _hours(context):
        """Игровое время текущей сессии в часах с дробной частью (total_hours + доля часа)."""
        gt = context.game_time
        if gt.hour_time <= 0.0:   # до первого тика GameTime
            return float(gt.total_hours)
        return gt.total_hours + gt.progress

    # --- считаются ОДИН РАЗ при start() (не меняются за ночь) ---
    def factor_difficulty(module, context):
        return 1.0 # TODO: когда будут настройки убрать return
        d = settings.game_difficulty # 1-4
        return 0.7 + 0.3 * (d - 1)

    def factor_night(module, context):
        night = context.night_system.loaded
        if night is None:
            return 1.0
        position = context.night_system.get_position(night)
        if position is None:      # особая ночь вне последовательности
            return 1.0
        return min(1.0 + 0.1 * (position - 1), 1.5)   # ночь 1 -> x1.0, ночь 5 -> x1.4

    # --- считаются каждый update() ---
    def factor_watched(module, context):
        player = context.player_manager.current_player
        if not player.has_tablet or not player.is_open_tablet:
            return 1.0
        if player.current_location.tablet.selected == module.current_location_id:
            return 0.5
        return 1.0

    def factor_door(module, context):
        player = context.player_manager.current_player
        if not player.has_door:
            return 1.0
        return 0.6 if not player.current_location.door.is_open else 1.0

    def factor_external(module, context):
        value = context.get("moving_module_tempo_mult")
        return 1.0 if value is None else value

    def factor_proximity(module, context):
        n = len(module._path)
        if n < 2:
            return 1.0
        progress = module._cursor / float(n - 1)
        return 1.0 + 0.3 * progress

    def factor_endgame(module, context):
        night = context.night_system.loaded
        if night is None or night.end_of_shift <= 0:
            return 1.0

        progress = _hours(context) / float(night.end_of_shift)
        start = module.ENDGAME_START
        if progress <= start:
            return 1.0
        if progress > 1.0:        # смена закончилась, но ночь ещё не завершена
            progress = 1.0

        t = (progress - start) / (1.0 - start)
        return 1.0 + module.ENDGAME_GAIN * t ** module.ENDGAME_POWER

    def factor_mood(module, context):
        return module._mood

    def factor_crowd(module, context):
        player = context.player_manager.current_player
        return 0.5 if player.under_attack else 1.0

    def factor_time(module, context):
        return 1.0 + module.TIME_GAIN * (1.0 - _math.exp(-_hours(context) / module.TIME_TAU))

    ALL_ENEMY_MOVING_START_FACTORS = (
        factor_difficulty,
        factor_night
    )

    ALL_ENEMY_MOVING_FACTORS = (
        factor_watched,
        factor_door,
        factor_external,
        factor_proximity,
        factor_endgame,
        factor_mood,
        factor_crowd,
        factor_time,
    )

    class EnemyMoveModule(EnemyModule):
        BASE_INTERVAL = 30.0   # средний интервал между ходами (сек) при speed=1 в начале ночи
        MIN_INTERVAL = 6.0     # быстрее этого не двигается никогда
        SPEED_MAX = 3.0        # потолок влияния speed
        MIN_DWELL = 3.0        # сек неподвижности после хода
        TIME_GAIN = 1.5        # прирост темпа от времени (потолок x2.5)
        TIME_TAU = 4.0         # за сколько игровых часов темп выходит на плато
        STUCK_GRACE = 1.5      # сколько "ожидаемых интервалов" можно простоять без бонуса
        STUCK_MAX = 3.0        # максимальный множитель от простоя

        ENDGAME_START = 0.66   # с какой доли ночи начинается давление (строго < 1.0)
        ENDGAME_GAIN = 0.5     # прибавка в конце смены (x1.5 при 0.5)
        ENDGAME_POWER = 2.0    # форма нарастания: 1 = линейно, 2 = медленно, потом резко

        def __init__(
            self, path,
            speed=1.0,
            start_factors=None,
            factors=None
        ):
            super(EnemyMoveModule, self).__init__()

            if path is None:
                path = ()
            elif is_string(path):
                path = (path,)
            elif not isinstance(path, Iterable):
                raise FNaSRTypeError("'path' должен быть итерируемым, пришло: {}".format(type(path)))

            if not is_number(speed) or speed < 0:
                raise FNaSRTypeError("'speed' должен быть числом пришло: {}".format(type(speed)))

            start_extra = list()
            if start_factors is not None:
                for fn in start_factors:
                    if not callable(fn):
                        raise FNaSRTypeError("Фактор должен быть вызываемым, пришло: {}".format(type(fn)))
                    start_extra.append(fn)

            extra = list()
            if factors is not None:
                for fn in factors:
                    if not callable(fn):
                        raise FNaSRTypeError("Фактор должен быть вызываемым, пришло: {}".format(type(fn)))
                    extra.append(fn)

            self._setattr("_path", list(path))
            self._setattr("_cursor", 0)
            self._setattr("_speed", float(speed))
            self._setattr("_idle", 0.0)
            self._setattr("_stun_left", 0.0)
            self._setattr("_mood", 1.0)
            self._setattr("_static", 1.0)

            self._start_factors = start_extra
            self._factors = extra

        @property
        def current_location_id(self):
            if not len(self._path):
                return None
            return self._path[self._cursor]

        @property
        def len_path(self):
            return len(self._path)

        @property
        def speed(self):
            return self._speed

        @speed.setter
        def speed(self, value):
            if not is_number(value) or value < 0:
                raise FNaSRTypeError("'speed' должен быть числом >= 0, пришло: {}".format(type(value)))
            self._speed = float(value)

        @property
        def stun_left(self):
            return self._stun_left

        def add_stun(self, value):
            if not is_strict_integer(value):
                raise FNaSRTypeError("'value' должен быть целым числом, пришло: {}".format(type(value)))
            if value < 1:
                raise FNaSRValueError("'value' должен быть больше нуля, пришло: {}".format(repr(value)))

            self._stun_left += value

        def add_factor(self, fn):
            if not callable(fn):
                raise FNaSRTypeError("Фактор должен быть вызываемым, пришло: {}".format(type(fn)))
            self._factors.append(fn)

        def on_include(self, enemy):
            context = enemy.context
            
            if context.get("location_system") is None:
                context.location_system = require_system("location")

            if context.get("game_time") is None:
                context.game_time = require_system("time")

            if context.get("night_system") is None:
                context.night_system = require_system("night")

            if context.get("player_manager") is None:
                context.player_manager = require_system("player")

            if context.get("stop_moving") is None:
                context.stop_moving = False


        def start(self, context):
            for location_id in self._path:
                context.location_system.require_location(location_id)

            static = 1.0
            for fn in self._start_factors:
                static *= fn(self, context)
            self._static = static
            self._idle = 0.0
            self._mood = renpy.random.uniform(0.85, 1.2)

            if self._path:
                self._move(context)

        def update(self, context):
            if not self._path:
                return

            dt = context.enemy.current_refresh_time

            if self._stun_left > 0.0:
                self._stun_left = max(0.0, self._stun_left - dt)
                return

            if context.stop_moving:
                return

            if self.move_change(context):
                self._idle_time = 0.0
                self.step_forward()

                if not self._move(context):
                    self._cursor = 0
                    self._move(context)

                context.enemy.set_align()
                update_ui()

        def _move(self, context, location=None):
            if location is None:
                location = context.location_system.require_location(self.current_location_id)
            try:
                context.enemy.move(location)
                return True
            except DoorClose:
                return False

        def get_rate(self, context):
            rate = min(self._speed, self.SPEED_MAX) / self.BASE_INTERVAL * self._static

            for fn in self._factors:
                rate *= fn(self, context)

            return rate

        def move_change(self, context, consider_refresh_time=False):
            self._idle += 1.0

            if self._idle < self.MIN_DWELL:
                return False

            rate = self.get_rate(context)
            if rate <= 0.0:
                return False

            expected = self._idle * rate
            if expected > self.STUCK_GRACE:
                rate *= min(1.0 + (expected - self.STUCK_GRACE) / self.STUCK_GRACE, self.STUCK_MAX)

            rate = min(rate, 1.0 / self.MIN_INTERVAL)

            if consider_refresh_time:
                return renpy.random.random() < 1.0 - _math.exp(-rate * context.enemy.current_refresh_time)
            else:
                return renpy.random.random() < 1.0 - _math.exp(-rate)

        def step_forward(self):
            if not len(self._path):
                return
            self._cursor += 1
            if self._cursor > len(self._path) - 1:
                self._cursor = 0
            return self.current_location_id

        def step_back(self):
            if not len(self._path):
                return
            self._cursor -= 1
            if self._cursor < 0:
                self._cursor = len(self._path) - 1
            return self.current_location_id

        def get_debug_list_texts(self, enemy_context):
            return [
                "path: {}/{}".format(self._cursor+1, self.len_path),
                "rate: {}".format(self.get_rate(enemy_context)),
                "stun: {}".format(self.stun_left),
                "speed: {}".format(self.speed),
                "current location id: {}".format(self.current_location_id)
            ]





