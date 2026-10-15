
# modules.rpy
init -2 python in v1FNaSR:
    import math as _math

    def _hours(context):
        """Игровое время текущей сессии в часах с дробной частью (total_hours + доля часа)."""
        gt = context.game_time
        if gt.hour_time <= 0.0:   # до первого тика GameTime
            return float(gt.total_hours)
        return gt.total_hours + gt.progress

    # --- считаются ОДИН РАЗ при start() (не меняются за ночь) ---
    def factor_difficulty(module, context):
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
        left = module.steps_left
        if left <= 0 or left >= module.PROXIMITY_RANGE:
            return 1.0
        closeness = (module.PROXIMITY_RANGE - left) / float(module.PROXIMITY_RANGE - 1)
        return 1.0 + module.PROXIMITY_GAIN * closeness

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

        PROXIMITY_RANGE = 5    # с скольки шагов до игрока начинается давление (>= 2)
        PROXIMITY_GAIN = 0.3   # прибавка, когда до игрока остался 1 шаг (x1.3)

        @staticmethod
        def generate_new_path_all_enemy():
            for enemy in get_created_enemy():
                location = enemy.current_location

                if location is None:
                    continue

                for module in enemy.modules:
                    if isinstance(module, EnemyMoveModule):
                        module.generate_new_path(location.id)

        def __init__(self,
            start_location_id=None,
            end_location_id=None,
            speed=1.0,
            start_factors=ALL_ENEMY_MOVING_START_FACTORS,
            factors=ALL_ENEMY_MOVING_FACTORS
        ):
            super(EnemyMoveModule, self).__init__()

            if start_location_id is not None:
                start_location_id = _normalize_id(start_location_id)
            if end_location_id is not None:
                end_location_id = _normalize_id(end_location_id)

            if not is_number(speed) or speed < 0:
                raise FNaSRTypeError("'speed' должен быть числом получено: {}".format(type(speed)))

            start_extra = list()
            if start_factors is not None:
                for fn in start_factors:
                    if not callable(fn):
                        raise FNaSRTypeError("Фактор должен быть вызываемым, получено: {}".format(type(fn)))
                    start_extra.append(fn)

            extra = list()
            if factors is not None:
                for fn in factors:
                    if not callable(fn):
                        raise FNaSRTypeError("Фактор должен быть вызываемым, получено: {}".format(type(fn)))
                    extra.append(fn)

            self._setattr("_path", [])
            self._setattr("_cursor", 0)
            self._setattr("_speed", float(speed))
            self._setattr("_idle", 0.0)
            self._setattr("_stun_left", 0.0)
            self._setattr("_mood", 1.0)
            self._setattr("_static", 1.0)
            self._setattr("_start_location_id", start_location_id)
            self._setattr("_end_location_id", end_location_id)

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
                raise FNaSRTypeError("'speed' должен быть числом >= 0, получено: {}".format(type(value)))
            self._speed = float(value)

        @property
        def stun_left(self):
            return self._stun_left

        @property
        def is_first(self):
            return bool(self._path) and self._cursor == 0

        @property
        def is_last(self):
            return bool(self._path) and self._cursor >= len(self._path) - 1

        @property
        def steps_left(self):
            return max(0, len(self._path) - 1 - self._cursor)

        def generate_new_path(self, start_location_id=None, end_location_id=None):
            if start_location_id is None:
                start_location_id = self._start_location_id

            if end_location_id is None:
                end_location_id = self._end_location_id

            path = PathGenerator.generate_path(
                start_location_id,
                end_location_id
            )

            self._path = path if path is not None else []
            self._cursor = 0

            if path is None:
                return None

            return tuple(path)

        def add_stun(self, value):
            if not is_strict_integer(value):
                raise FNaSRTypeError("'value' должен быть целым числом, получено: {}".format(type(value)))
            if value < 1:
                raise FNaSRValueError("'value' должен быть больше нуля, получено: {}".format(repr(value)))

            self._stun_left += value

        def add_factor(self, fn):
            if not callable(fn):
                raise FNaSRTypeError("Фактор должен быть вызываемым, получено: {}".format(type(fn)))
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
            path = self.generate_new_path()
            if path is None:
                raise FNaSRException("Не удалось построить путь для '{}'({})".format(context.enemy.name, context.enemy.tag))

            for location_id in path:
                context.location_system.require_location(location_id)

            static = 1.0
            for fn in self._start_factors:
                static *= fn(self, context)
            self._static = static
            self._idle = 0.0
            self._mood = renpy.random.uniform(0.85, 1.2)

            if path:
                self._move(context)

        def update(self, context):
            path = tuple(self._path)

            if not path:
                return

            if self._cursor >= len(path) - 1:
                return

            dt = 1.0 # context.enemy.current_refresh_time

            if self._stun_left > 0.0:
                self._stun_left = max(0.0, self._stun_left - dt)
                return

            if context.stop_moving:
                return

            if self.move_change(context):
                self._idle = 0.0

                self.step_forward()

                if not self._move(context):
                    self.generate_new_path()
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
            dt = (
                context.enemy.current_refresh_time
                if consider_refresh_time
                else 1.0
            )

            if dt <= 0.0:
                return False

            self._idle += dt

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

        def step_forward(self, cyclic_path=False):
            path = tuple(self._path)
            if not len(path):
                return
            self._cursor += 1
            if self._cursor > len(path) - 1:
                if cyclic_path:
                    self._cursor = 0
                else:
                    self._cursor -= 1
            return self.current_location_id

        def step_back(self, cyclic_path=False):
            path = tuple(self._path)
            if not len(path):
                return
            self._cursor -= 1
            if self._cursor < 0:
                if cyclic_path:
                    self._cursor = len(path) - 1
                else:
                    self._cursor += 1
            return self.current_location_id

        def get_debug_list_texts(self, enemy_context):
            return [
                "path: {}".format(self._path),
                "steps left: {}".format(self.steps_left),
                "rate: {}".format(self.get_rate(enemy_context)),
                "stun: {}".format(self.stun_left),
                "speed: {}".format(self.speed),
                "current location id: {}".format(self.current_location_id)
            ]

    class EnemyAttackModule(EnemyModule):
        def __init__(self, enemy_screamer, safety_time=0.5):
            if not isinstance(enemy_screamer, EnemyScreamer):
                raise FNaSRTypeError("'enemy_screamer' должен быть 'EnemyScreamer', получено: {}".format(type(enemy_screamer)))

            if not is_number(safety_time) or safety_time < 0:
                raise FNaSRTypeError("'safety_time' должен быть положительным числом, получено: {}".format(type(safety_time)))

            super(EnemyAttackModule, self).__init__()

            self._enemy_screamer = enemy_screamer

            self._setattr("_safety_time", float(safety_time))
            self._setattr("_current_safety_time", 0.0)

        def get_safety_time(self):
            "Получить safety_time с учётом времени анимации"
            return self._safety_time + 1.8 / GlobalState.get("moving_animation_speed", 1.0)

        def on_include(self, enemy):
            context = enemy.context
            
            if context.get("player_manager") is None:
                context.player_manager = require_system("player")

            if context.get("is_all_players_dead") is None:
                context.is_all_players_dead = False

        def tick_update(self, context, dt):
            if context.is_all_players_dead:
                return
            player = context.player_manager.current_player
            if player.current_location.id == context.enemy.current_location.id:
                self._current_safety_time += dt
                if self._current_safety_time >= self.get_safety_time():
                    self._current_safety_time = 0.0
                    self._kill_player(context, player)
            else:
                self._current_safety_time = 0.0

        def _kill_player(self, context, player):
            player.to_kill()
            self._add_history_murders(context.enemy.tag)
            for player in context.player_manager:
                if not player.is_died:
                    context.player_manager.switch_player(player.id)
                    break
            else:
                context.is_all_players_dead = True
                main_executor.submit_and_wait(renpy.jump, "v1_screamer_label_FNaSR")

        def _add_history_murders(self, enemy_tag):
            history_murders = GlobalState.get("HistoryMurders")
            if history_murders is None:
                GlobalState.set("HistoryMurders", list())

            GlobalState.get("HistoryMurders").append((enemy_tag, self._enemy_screamer,))

        def get_debug_list_texts(self, enemy_context):
            return [
                "net safety time: {}".format(self._safety_time),
                "safety time: {}/{}".format(self._current_safety_time, self.get_safety_time()),
            ]




