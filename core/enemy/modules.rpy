
# modules.rpy
init -2 python in v1FNaSR:
    import math as _math

    audio.register_channel("enemy_channel", "sound", loop=False)

    def _hours(context):
        """Игровое время текущей сессии в часах с дробной частью (total_hours + доля часа)."""
        gt = context.game_time
        if gt.hour_time <= 0.0:
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
        if position is None:
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
        if progress > 1.0:
            progress = 1.0

        t = (progress - start) / (1.0 - start)
        return 1.0 + module.ENDGAME_GAIN * t ** module.ENDGAME_POWER

    def factor_mood(module, context):
        return module._mood

    def factor_crowd(module, context):
        player = context.player_manager.current_player
        return 1.5 if player.under_attack else 1.0

    def factor_time(module, context):
        return 1.0 + module.TIME_GAIN * (1.0 - _math.exp(-_hours(context) / module.TIME_TAU))

    def factor_not_watch(module, context):
        player = context.player_manager.current_player
        if player.current_location is None:
            return 1.0
        if player.is_open_tablet and player.current_location.tablet.selected == module.current_location_id:
            return 0.0
        return 1.0

    ALL_ENEMY_MOVING_START_FACTORS = (
        factor_difficulty,
        factor_night
    )

    BASE_ENEMY_MOVING_FACTORS = (
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
        __slots__ = (
            "_path", "_cursor", "_speed", "_idle",
            "_stun_left", "_mood", "_static",
            "_start_location_id", "_end_location_id",
            "_ignore_player", "_start_factors", "_factors",
        )

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
            for enemy in require_system("enemy").iter_current_group:
                location = enemy.current_location

                if location is None:
                    continue

                for module in enemy.modules:
                    if isinstance(module, EnemyMoveModule) and not module.ignore_player:
                        module.generate_new_path(location.id)

        def __init__(self,
            start_location_id=None,
            end_location_id=None,
            ignore_player=False,
            speed=1.0,
            start_factors=ALL_ENEMY_MOVING_START_FACTORS,
            factors=BASE_ENEMY_MOVING_FACTORS
        ):
            super(EnemyMoveModule, self).__init__()

            if start_location_id is not None:
                start_location_id = _normalize_id(start_location_id)
            if end_location_id is not None:
                end_location_id = _normalize_id(end_location_id)

            if not is_number(speed):
                raise FNaSRTypeError("'speed' должен быть числом получено: {}".format(type(speed)))
            if speed < 0:
                raise FNaSRValueError("'speed' не может быть меньше нуля, получено: {}".format(speed))

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

            self._setattr("_path", list())
            self._setattr("_cursor", 0)
            self._setattr("_speed", float(speed))
            self._setattr("_idle", 0.0)
            self._setattr("_stun_left", 0.0)
            self._setattr("_mood", 1.0)
            self._setattr("_static", 1.0)
            self._setattr("_start_location_id", start_location_id)
            self._setattr("_end_location_id", end_location_id)
            self._setattr("_ignore_player", bool(ignore_player))

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

        @property
        def start_location_id(self):
            return self._start_location_id

        @property
        def end_location_id(self):
            return self._end_location_id

        @property
        def ignore_player(self):
            return self._ignore_player

        def generate_new_path(self, start_location_id=MISSING, end_location_id=MISSING):
            if start_location_id is MISSING:
                start_location_id = self._start_location_id

            if end_location_id is MISSING:
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
                context.stop_moving = MultiLock()

            if context.get("move_wait_door_open") is None:
                context.move_wait_door_open = False

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

        def update(self, context, dt):
            if not self._path:
                return

            if self._cursor >= len(self._path) - 1:
                return

            if self._stun_left > 0.0:
                self._stun_left = max(0.0, self._stun_left - dt)
                return

            if context.stop_moving.blocked:
                return

            if self.move_change(context, dt):
                self._idle = 0.0

                self.step_forward()

                if not self._move(context):
                    if not context.move_wait_door_open:
                        self.generate_new_path()
                        self._move(context)

                context.enemy.set_align()
                update_ui()
        
        def reset(self, context):
            context.stop_moving.clear()
            context.move_wait_door_open = False
            super(EnemyMoveModule, self).reset(context)

        def _move(self, context, location=None):
            if location is None:
                if self.current_location_id is None:
                    return False
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

        def move_change(self, context, dt):
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

            return renpy.random.random() < 1.0 - _math.exp(-rate * dt)

        def get_next_location_id(self, offset=1):
            len_path = len(self._path)

            if not len_path:
                return

            offset = int(offset)
            virtual_cursor = self._cursor + offset

            if virtual_cursor > len_path - 1:
                return

            return self._path[virtual_cursor]

        def get_previous_location_id(self, offset=1):
            len_path = len(self._path)

            if not len_path:
                return

            offset = int(offset)
            virtual_cursor = self._cursor - offset

            if virtual_cursor < 0:
                return

            return self._path[virtual_cursor]

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
                "current location id: {}".format(self.current_location_id),
                "stop moving: {}".format(enemy_context.stop_moving.blocked)
            ]


    class EnemyAggressiveModule(EnemyModule):
        __slots__ = ("_enemy_screamer", "_safety_time", "_current_safety_time",)

        conflicting_modules = tuple()

        def __init__(self, enemy_screamer, safety_time=1.0):
            super(EnemyAggressiveModule, self).__init__()

            if not isinstance(enemy_screamer, EnemyScreamer):
                raise FNaSRTypeError("'enemy_screamer' должен быть 'EnemyScreamer', получено: {}".format(type(enemy_screamer)))

            if not is_number(safety_time):
                raise FNaSRTypeError("'safety_time' должен быть числом, получено: {}".format(type(safety_time)))
            if safety_time < 0:
                raise FNaSRValueError("'safety_time' должен быть положительным, получено: {}".format(safety_time))
            safety_time = float(safety_time)

            self._enemy_screamer = enemy_screamer
            self._setattr("_safety_time", safety_time)
            self._setattr("_record_safety_time", safety_time)
            self._setattr("_current_safety_time", 0.0)

        @property
        def safety_time(self):
            return self._safety_time

        @safety_time.setter
        def safety_time(self, value):
            if not is_number(value):
                raise FNaSRTypeError("'value' должен быть числом, получено: {}".format(type(value)))
            if value < 0:
                raise FNaSRValueError("'value' должен быть положительным, получено: {}".format(value))
            self._safety_time = float(value)

        def record_safety_time(self):
            self._record_safety_time = self._safety_time

        def reset_safety_time(self):
            self._safety_time = self._record_safety_time

        def get_current_safety_time(self):
            """Получить safety_time с учётом времени анимации"""
            speed = GlobalState.get("moving_animation_speed", 1.0)
            if speed > 0:
                return self._safety_time + 1.8 / GlobalState.get("moving_animation_speed", 1.0)
            return self._safety_time

        def on_include(self, enemy):
            context = enemy.context
            
            if context.get("player_manager") is None:
                context.player_manager = require_system("player")

            if context.get("cycle") is None:
                context.cycle = require_system("cycle")

            if context.get("is_player_dead") is None:
                context.is_player_dead = False

        def start(self, context):
            self.record_safety_time()

        def update(self, context, dt):
            if context.is_player_dead:
                return
            player = context.player_manager.current_player
            if player is None:
                return
            if player.current_location is None:
                return
            if context.enemy.current_location is None:
                return
            if player.current_location.id == context.enemy.current_location.id:
                self._current_safety_time += dt
                if self._current_safety_time >= self.get_current_safety_time():
                    self._current_safety_time = 0.0
                    self._kill_player(context, player)
            else:
                self._current_safety_time = 0.0

        def _kill_player(self, context, player):
            if player.try_kill():
                self._set_killed_player(context)
                context.is_player_dead = True
                context.cycle.request_transition("v1_night_screamer_label_FNaSR")

        def _set_killed_player(self, context):
            GlobalState.set_if_absent("OpponentKilledPlayer", (context.enemy.tag, self._enemy_screamer, require_system("time").get_time(),))

        def get_debug_list_texts(self, enemy_context):
            return [
                "net safety time: {}".format(self._safety_time),
                "safety time: {}/{}".format(self._current_safety_time, self.get_current_safety_time()),
            ]

    class EnemyAttackModule(EnemyAggressiveModule):
        __slots__ = (
            "_move_module", "_attack_target_id",
            "_murder_countdown", "_r_t_m", "_sound_channel",
        )

        dependent_modules = (EnemyMoveModule,)
        conflicting_modules = tuple()

        def __init__(self, enemy_screamer, random_time_murder=(4,6,), sound_channel="enemy_channel", **kwargs):
            super(EnemyAttackModule, self).__init__(enemy_screamer=enemy_screamer, **kwargs)

            if not isinstance(random_time_murder, (list, tuple,)):
                raise FNaSRTypeError("'random_time_murder' должен быть списком или кортежем, получено: {}".format(type(random_time_murder)))

            if len(random_time_murder) != 2:
                raise FNaSRValueError("'random_time_murder' должен держать строго 2 элемента, получено: {}".format(len(random_time_murder)))

            if not is_strict_integer(random_time_murder[0]) or not is_strict_integer(random_time_murder[1]):
                raise FNaSRValueError("'random_time_murder' должен держать только целые числа, получено: 1-{}, 2-{}".format(type(random_time_murder[0]), type(random_time_murder[1])))

            if random_time_murder[0] < 1:
                raise FNaSRValueError("'random_time_murder' нижняя граница должна быть не меньше 1, получено: {}".format(random_time_murder[0]))

            if random_time_murder[1] < random_time_murder[0]:
                raise FNaSRValueError("'random_time_murder' верхняя граница должна быть не меньше нижней, получено: {} < {}".format(random_time_murder[1], random_time_murder[0]))

            if not is_string(sound_channel):
                raise FNaSRTypeError("'sound_channel' должен быть строкой, получено: {}".format(type(sound_channel)))

            self._setattr("_move_module", None)
            self._setattr("_attack_target_id", None)
            self._setattr("_murder_countdown", None)
            self._setattr("_r_t_m", tuple(random_time_murder))
            self._setattr("_sound_channel", sound_channel)
            self._setattr("_old_safe_time", 1.5)

        def get_current_safety_time(self):
            "Получить safety_time с учётом времени анимации"
            return self._safety_time + 1.8 / GlobalState.get("moving_animation_speed", 1.0)

        def on_include(self, enemy):
            context = enemy.context
            
            if context.get("player_manager") is None:
                context.player_manager = require_system("player")

            if context.get("location_system") is None:
                context.location_system = require_system("location")

            if context.get("cycle") is None:
                context.cycle = require_system("cycle")

            if context.get("is_player_dead") is None:
                context.is_player_dead = False

        def start(self, context):
            self._move_module = self.get_module(context.enemy, EnemyMoveModule)

        def update(self, context, dt):
            if context.is_player_dead:
                return

            super(EnemyAttackModule, self).update(context, dt)

            self._accumulated_time += dt
            while self.interval():
                if self._move_module is None:
                    return

                self._handle_attack(context)

        def reset(self, context):
            context.is_player_dead = False
            super(EnemyAttackModule, self).reset(context)

        def _handle_attack(self, context):
            if self._handle_attack_target_id(context):
                return

            location = self.get_relative_location(context, 1)
            if location is None:
                return
            if location.door is None:
                return

            if not self.player_present(context, location):
                return

            self._start_attack(context, location)

        def _handle_attack_target_id(self, context):
            if self._attack_target_id is None:
                return False

            player = context.player_manager.current_player

            if player is not None:
                player_location = player.current_location

                if player_location is not None and player_location.id == self._attack_target_id:
                    if context.enemy.tag not in player.under_attack:
                        player.under_attack + context.enemy.tag
                elif context.enemy.tag in player.under_attack:
                    player.under_attack - context.enemy.tag

            self._attack(context)
            return True

        def _start_attack(self, context, attack_target):
            main_executor.submit(audio.play, resources.sounds.sfx["enemy_deep_steps"], self._sound_channel)
            context.stop_moving.block(self)
            self._attack_target_id = attack_target.id
            self._safety_time = 0.5
            self._attack(context)

        def _attack(self, context):
            target_id = self._attack_target_id

            if target_id is None:
                return

            location = context.location_system.get_location(target_id)

            if location is None or location.door is None:
                self._finish_attack(context)
                return

            if not self._is_murder_time():
                return

            if not location.door.is_open:
                self._loss_attack(context)
                return

            self._move_module.step_forward()

            if not self._move_module._move(context):
                self._loss_attack(context)
                return

            self._finish_attack(context)

        def _loss_attack(self, context):
            main_executor.submit(audio.play, renpy.store.sfx_campus_door_rattle, self._sound_channel)
            player = context.player_manager.current_player

            if player.current_location is None:
                self._move_module.generate_new_path()
            elif self._move_module.start_location_id is not None and player.current_location.id != self._move_module.start_location_id:
                self._move_module.generate_new_path()
            else:
                self._move_module.generate_new_path(None)

            self._move_module._move(context)
            self._finish_attack(context)

            if context.enemy.tag == "us":
                if renpy.random.random() < 0.01:
                    random_s = (
                        renpy.store.sfx_hell_crickets_1,
                        renpy.store.sfx_hell_crickets_2,
                        renpy.store.sfx_hell_crickets_3,
                    )

                    main_executor.submit(audio.play, renpy.random.choice(random_s), self._sound_channel, loop=False, fadeout=1, fadein=2)

        def _finish_attack(self, context):
            self.reset_safety_time()
            player = context.player_manager.current_player
            self._attack_target_id = None
            self._murder_countdown = None
            context.stop_moving.unblock(self)
            if context.enemy.tag in player.under_attack:
                player.under_attack - context.enemy.tag

        def _get_time_murder(self):
            return renpy.random.randint(self._r_t_m[0], self._r_t_m[1])

        def _is_murder_time(self):
            if self._murder_countdown is None:
                self._murder_countdown = self._get_time_murder()

            self._murder_countdown -= 1

            if self._murder_countdown > 0:
                return False

            self._murder_countdown = None
            return True

        def get_relative_location(self, context, distance):
            if self._move_module is None:
                return

            distance = int(distance)

            if distance >= 0:
                location_id = self._move_module.get_next_location_id(distance)
            else:
                location_id = self._move_module.get_previous_location_id(distance)
            if location_id is None:
                return

            location = context.location_system.get_location(location_id)
            if location is None:
                return

            return location

        def player_present(self, context, location):
            player = context.player_manager.current_player
            if player is None:
                return False
            if player.current_location is None:
                return False
            if player.current_location.id != location.id:
                return False
            return True

        def get_debug_list_texts(self, enemy_context):
            return super(EnemyAttackModule, self).get_debug_list_texts(enemy_context) + [
                "murder countdown: {}".format(self._murder_countdown),
                "attack target id: {}".format(self._attack_target_id),
            ]

    class EnemySilentAttackModule(EnemyAttackModule):
        __slots__ = ("_silent_locations", "_replaced",)

        conflicting_modules = tuple()

        def __init__(self, enemy_screamer, silent_locations=None, **kwargs):
            super(EnemySilentAttackModule, self).__init__(enemy_screamer, **kwargs)

            if silent_locations is None:
                silent_locations = {}

            if not isinstance(silent_locations, dict):
                raise FNaSRTypeError("'silent_locations' должен быть словарём, получено: {}".format(type(silent_locations)))

            normalized = {}

            for location_id, variants in iter_items(silent_locations):
                if not is_strict_integer(location_id):
                    raise FNaSRTypeError("ID локации должен быть int, получено: {!r}".format(location_id))

                if isinstance(variants, SilentImageVariant):
                    variants = [variants]

                if not isinstance(variants, (list, tuple,)):
                    raise FNaSRTypeError("'variants' должен быть списком или кортежем, получено: {}".format(type(variants)))

                if not variants:
                    continue

                total_chance = 0
                for i, variant in enumerate(variants):
                    if not isinstance(variant, SilentImageVariant):
                        raise FNaSRTypeError("silent_locations[{}][{}] должен быть 'SilentImageVariant', получено: {}.".format(location_id, i, type(variant)))
                    total_chance += variant.chance
                if total_chance != 100:
                    raise FNaSRValueError("Сумма шансов изображений для локации {} должна равняться 100, получено: {}.".format(location_id, total_chance))

                normalized[_normalize_id(location_id)] = tuple(variants)

            self._silent_locations = normalized
            self._setattr("_replaced", False)

        def update(self, context, dt):
            self._replace_image(context)
            super(EnemySilentAttackModule, self).update(context, dt)

        def _start_attack(self, context, attack_target):
            data = self._silent_locations.get(attack_target.id, None)

            if not attack_target.is_replaced_image and data is not None and data:
                self._replace_image(context)
            else:
                main_executor.submit(audio.play,resources.sounds.sfx["enemy_deep_steps"], self._sound_channel)

            context.stop_moving.block(self)
            self._attack_target_id = attack_target.id
            self._safety_time = 0.5
            self._attack(context)
            

        def _choose_silent_variant(self, variants):
            if not variants:
                return None

            roll = renpy.random.random() * 100.0
            cumulative_chance = 0

            for variant in variants:
                cumulative_chance += variant.chance

                if roll < cumulative_chance:
                    return variant

            for variant in reversed(variants):
                if variant.chance > 0:
                    return variant

            return None

        def _loss_attack(self, context):
            super(EnemySilentAttackModule, self)._loss_attack(context)
            if renpy.random.random() < 0.01:
                main_executor.submit(audio.play, renpy.store.sfx_knock_glass, self._sound_channel)

        def _finish_attack(self, context):
            if self._attack_target_id is not None:
                location = context.location_system.get_location(self._attack_target_id)
                if location is not None and self._replaced:
                    location.clear_substituted_image(all=True)
            super(EnemySilentAttackModule, self)._finish_attack(context)
            self._replaced = False

        def _replace_image(self, context):
            target_id = self._attack_target_id

            if target_id is None or target_id not in self._silent_locations:
                return

            location = context.location_system.get_location(target_id)

            if location is None:
                return

            player = context.player_manager.current_player
            player_location = player.current_location if player is not None else None

            if player_location is None or player_location.id != target_id:
                if self._replaced:
                    location.clear_substituted_image(all=True)
                    self._replaced = False

                return

            if self._replaced or location.is_replaced_image:
                return

            variants = self._silent_locations[target_id]
            variant = self._choose_silent_variant(variants)

            if variant is None:
                return

            if variant.light_image is not None:
                location.replace_image(variant.light_image)

            if variant.dark_image is not None:
                location.replace_image(variant.dark_image, dark=True)

            self._replaced = variant.light_image is not None or variant.dark_image is not None

        def get_debug_list_texts(self, enemy_context):
            lines = []
            for loc_id, variants in iter_items(self._silent_locations):
                lines.append(" {}: {}\n".format(loc_id, len(variants)))
            return super(EnemySilentAttackModule, self).get_debug_list_texts(enemy_context) + [
                "silent locations:\n{}".format("".join(lines)),
                "replaced: {}".format(self._replaced)
            ]

    class EnemySignalButtonModule(EnemyModule):
        KEY = "v1_enemy_signal_button_module_%s"

        dependent_modules = (EnemyMoveModule,)

        def __init__(self, button_press_duration=3, button_image=None, signal_sound=None, signal_channel="signal", button_align=(0.25, 0.89), xysize=(290 / 2, 60 / 2)):
            if button_image is None:
                button_image = resources.images.other["Signal_button"]
            if signal_sound is None:
                signal_sound = resources.sounds.sfx["tablet_scaring_sound"]

            if not is_number(button_press_duration):
                raise FNaSRTypeError("'button_press_duration' должен быть числом, получено: {}".format(type(button_press_duration)))
            if not is_string(button_image):
                raise FNaSRTypeError("'button_image' должен быть строкой, получено: {}".format(type(button_image)))
            if not is_string(signal_sound):
                raise FNaSRTypeError("'signal_sound' должен быть строкой, получено: {}".format(type(signal_sound)))
            if not is_string(signal_channel):
                raise FNaSRTypeError("'signal_channel' должен быть строкой, получено: {}".format(type(signal_channel)))
            if not isinstance(button_align, (list, tuple)):
                raise FNaSRTypeError("'button_align' должен быть списком или кортежем, получено: {}".format(type(button_align)))
            if len(button_align) != 2:
                raise FNaSRValueError("'button_align' должен состоять из 2 элементов, получено: {}".format(len(button_align)))
            for i in range(2):
                if not is_number(button_align[i]):
                    raise FNaSRValueError("button_align[{}] должен быть числом, получено: {}".format(i, button_align[i]))
            if not isinstance(xysize, (list, tuple)):
                raise FNaSRTypeError("'xysize' должен быть списком или кортежем, получено: {}".format(type(xysize)))
            if len(xysize) != 2:
                raise FNaSRValueError("'xysize' должен состоять из 2 элементов, получено: {}".format(len(xysize)))
            for i in range(2):
                if not is_number(xysize[i]):
                    raise FNaSRValueError("xysize[{}] должен быть числом, получено: {}".format(i, xysize[i]))
            
            button_align = tuple(button_align)
            xysize = tuple(xysize)
            vp = ViewportManager.current()
            xsize = round(vp.scale_scalar(xysize[0]))
            ysize = round(vp.scale_scalar(xysize[1]))

            self._button_press_duration = float(button_press_duration)
            self._button_image = button_image
            self._signal_sound = signal_sound
            self._signal_channel = signal_channel
            self._button_align = button_align
            self._key = None

            self._button = HoldingMouseImageButton(
                idle=renpy.store.Transform(self._button_image, xysize=(xsize, ysize)),
                click_action=renpy.store.Function(self._handle_button, True),
                unclick_action=renpy.store.Function(self._handle_button, False),
                allow_alternate=False,
                align=button_align
            )

            self._setattr("_signal", False)
            self._setattr("_show_button", False)
            self._setattr("_player", None)
            self._setattr("_move_module", None)

        def on_include(self, enemy):
            context = enemy.context
            self._key = self.KEY % context.enemy.tag
            
            if context.get("player_manager") is None:
                context.player_manager = require_system("player")

        def start(self, context):
            self._player = context.player_manager.current_player
            if self._player is None:
                raise FNaSRRuntimeError("'current_player' не указан.")
            self._move_module = self.get_module(context.enemy, EnemyMoveModule)

        def update(self, context, dt):
            self._accumulated_time += dt
            self._handle_render_button(context)
            while self.interval(self._button_press_duration):
                self._scare_away(context)

        def _scare_away(self, context):
            if self._move_module is None:
                return

            player = context.player_manager.current_player

            if player.current_location is None:
                self._move_module.generate_new_path()
            elif self._move_module.start_location_id is not None and player.current_location.id != self._move_module.start_location_id:
                self._move_module.generate_new_path()
            else:
                self._move_module.generate_new_path(None)

        def _handle_render_button(self, context):
            if not self._player.is_open_tablet:
                self._hide()
                return

            if context.enemy.current_location is None:
                self._hide()
                return

            visible_ids = Tablet.get_visible_ids(self._player)
            if context.enemy.current_location.id not in visible_ids:
                self._hide()
                return

            self._show()

        def _show(self):
            if self._show_button:
                return
            self._show_button = True
            main_executor.submit(renpy.show, self._key, what=self._button)

        def _hide(self):
            if not self._show_button:
                return
            self._show_button = False
            main_executor.submit(renpy.hide, self._key)

        def _handle_button(self, s):
            self._signal = bool(s)
            if self._signal:
                main_executor.submit(audio.play, self._signal_sound, self._signal_channel, loop=True)
            else:
                main_executor.submit(audio.stop, self._signal_channel)

        def reset(self, context):
            main_executor.submit(renpy.hide, self._key)
            super(EnemySignalButtonModule, self).reset(context)
            self._button.force_unclick()




















    EnemyAggressiveModule.conflicting_modules = (
        EnemyAttackModule,
        EnemySilentAttackModule,
    )

    EnemyAttackModule.conflicting_modules = (
        EnemyAggressiveModule,
        EnemySilentAttackModule,
    )

    EnemySilentAttackModule.conflicting_modules = (
        EnemyAggressiveModule,
        EnemyAttackModule,
    )
