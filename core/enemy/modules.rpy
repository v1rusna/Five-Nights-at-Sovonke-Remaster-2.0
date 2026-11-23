# -*- coding: utf-8 -*-
# core/enemy/modules.rpy
init -2 python in v1FNaSR:
    import math as _math
    import random as _random
    import weakref as _weakref

    audio.register_channel("enemy_channel", "sound", loop=False)
    audio.register_channel("enemy_footsteps_channel", "sound", loop=False)
    audio.register_channel("enemy_agitation_channel", "sound", loop=False)
    audio.register_channel("enemy_call_phone_channel", "sound", loop=False)

    class FactorsMoveModule:
        @staticmethod
        def _hours(context):
            """Игровое время текущей сессии в часах с дробной частью (total_hours + доля часа)."""
            gt = context.game_time
            if gt.hour_time <= 0.0:
                return float(gt.total_hours)
            return gt.total_hours + gt.progress

        # --- считаются ОДИН РАЗ при start() (не меняются за ночь) ---
        @staticmethod
        def factor_difficulty(module, context):
            d = settings.game_difficulty # 1-4
            return 0.7 + 0.3 * (d - 1)

        @staticmethod
        def factor_night(module, context):
            night = context.night_system.loaded
            if night is None:
                return 1.0
            position = context.night_system.get_position(night)
            if position is None:
                return 1.0
            return min(1.0 + 0.1 * (position - 1), 1.5)   # ночь 1 -> x1.0, ночь 5 -> x1.4

        # --- считаются каждый update() ---
        @staticmethod
        def factor_watched(module, context):
            player = context.player_manager.current_player
            if not player.has_tablet or not player.is_open_tablet:
                return 1.0
            if player.current_location.tablet.selected == module.current_location_id:
                return 0.5
            return 1.0

        @staticmethod
        def factor_door(module, context):
            player = context.player_manager.current_player
            if not player.has_door:
                return 1.0
            return 0.6 if not player.current_location.door.is_open else 1.0
        
        @staticmethod
        def factor_external(module, context):
            value = context.get("moving_module_tempo_mult")
            if value is None:
                return 1.0
            if value < 0:
                return 0.0
            return value
        
        @staticmethod
        def factor_proximity(module, context):
            left = module.steps_left
            if left <= 0 or left >= module.PROXIMITY_RANGE:
                return 1.0
            closeness = (module.PROXIMITY_RANGE - left) / float(module.PROXIMITY_RANGE - 1)
            return 1.0 + module.PROXIMITY_GAIN * closeness
        
        @staticmethod
        def factor_endgame(module, context):
            night = context.night_system.loaded
            if night is None or night.end_of_shift <= 0:
                return 1.0

            progress = FactorsMoveModule._hours(context) / float(night.end_of_shift)
            start = module.ENDGAME_START
            if progress <= start:
                return 1.0
            if progress > 1.0:
                progress = 1.0

            t = (progress - start) / (1.0 - start)
            return 1.0 + module.ENDGAME_GAIN * t ** module.ENDGAME_POWER

        @staticmethod
        def factor_mood(module, context):
            return module._mood

        @staticmethod
        def factor_crowd(module, context):
            player = context.player_manager.current_player
            return 0.5 if player.under_attack else 1.0

        @staticmethod
        def factor_time(module, context):
            return 1.0 + module.TIME_GAIN * (1.0 - _math.exp(-FactorsMoveModule._hours(context) / module.TIME_TAU))

        @staticmethod
        def factor_not_watch(module, context):
            player = context.player_manager.current_player
            if player.current_location is None:
                return 1.0
            if not player.is_open_tablet:
                return 1.0
            if module.current_location_id in Tablet.get_visible_ids(player):
                return 0.0
            return 1.0

    BASE_ENEMY_MOVING_START_FACTORS = (
        FactorsMoveModule.factor_difficulty,
        FactorsMoveModule.factor_night
    )

    BASE_ENEMY_MOVING_FACTORS = (
        FactorsMoveModule.factor_watched,
        FactorsMoveModule.factor_door,
        FactorsMoveModule.factor_external,
        FactorsMoveModule.factor_proximity,
        FactorsMoveModule.factor_endgame,
        FactorsMoveModule.factor_mood,
        FactorsMoveModule.factor_crowd,
        FactorsMoveModule.factor_time,
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
                        enemy._safe_call(module, "generate_new_path", location.id)
                        break


        def __init__(self,
            start_location_id=None,
            end_location_id=None,
            ignore_player=False,
            wait_door_open=False,
            speed=1.0,
            start_factors=BASE_ENEMY_MOVING_START_FACTORS,
            factors=BASE_ENEMY_MOVING_FACTORS,
        ):
            super(EnemyMoveModule, self).__init__()

            if start_location_id is not None:
                start_location_id = LocationTools.normalize_id(start_location_id)
            if end_location_id is not None:
                end_location_id = LocationTools.normalize_id(end_location_id)

            check.expect_type(speed, is_number, "speed", "числом")
            check.expect_value(speed, lambda value: value >= 0, "speed", "больше или равным нулю")

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
            self._wait_door_open = bool(wait_door_open)

        @property
        def path(self):
            return tuple(self._path)

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
            if not is_number(value):
                raise FNaSRTypeError("'speed' должен быть числом, получено: {}".format(type(value)))
            if value < 0:
                raise FNaSRValueError("'speed' не может быть меньше нуля, получено: {}".format(value))
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

        def generate_new_path(
            self,
            start_location_id=MISSING,
            end_location_id=MISSING,
            replaced_path=True,
            player_location_id=None,
            attempts=10
        ):
            if not is_strict_integer(attempts):
                raise FNaSRTypeError("'attempts' должен быть числом, получено: {}".format(type(attempts)))
            if attempts < 1:
                raise FNaSRValueError("'attempts' должен быть положительный, получено: {}".format(attempts))

            if start_location_id is MISSING:
                start_location_id = self._start_location_id

            if end_location_id is MISSING:
                end_location_id = self._end_location_id

            for _ in range(attempts):
                path = PathGenerator.generate_path(start_location_id, end_location_id)

                if path is None:
                    raise PathGenerateError(start_location_id, end_location_id)

                if player_location_id != path[0]:
                    break
            else:
                raise PathGenerateError(start_location_id, end_location_id)

            if replaced_path:
                self._replace_path(path)

            return tuple(path)

        def _replace_path(self, path):
            self._path = list(path) if path is not None else []
            self._cursor = 0
            self.on_path_replaced()

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
                context.remember("location_system", require_system("location"))

            if context.get("game_time") is None:
                context.remember("game_time", require_system("time"))

            if context.get("night_system") is None:
                context.remember("night_system", require_system("night"))

            if context.get("player_manager") is None:
                context.remember("player_manager", require_system("player"))

            if context.get("stop_moving") is None:
                context.remember("stop_moving", MultiLock())

        def start(self, context):
            player = context.player_manager.current_player
            player_location = player.current_location if self._start_location_id is None else None
            player_location_id = player_location.id if player_location is not None else None
            
            try:
                path = self.generate_new_path(player_location_id=player_location_id)
            except PathGenerateError as e:
                raise FNaSRException("Не удалось построить путь, отличный от локации игрока, для '{}': {}".format(context.enemy.tag, e))

            if context.get("move_wait_door_open") is None:
                context.move_wait_door_open = self._wait_door_open

            for location_id in path:
                context.location_system.require_location(location_id)

            static = 1.0
            for fn in self._start_factors:
                static *= fn(self, context)
            self._static = static
            self._idle = 0.0
            self._mood = _random.uniform(0.85, 1.2)

            if path:
                self.move(context)

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

                if not self.move(context):
                    self.step_back()

                    if not context.move_wait_door_open:
                        path = self.generate_new_path(replaced_path=False) # TODO: сделать механику при которой противник идет обратно к точке спайна (или в рандомную отдаленную локацию), при этом если игрок поменял локацию противник уже шел обратно к игроку, ну либо шел до конца в спавну, либо комбинированный вариант, как второй но если игрок на соседней локации то противник начинал преследовать игрока
                        if self.move(context, context.location_system.require_location(path[0])):
                            self._replace_path(path)
                        else:
                            path = self.generate_new_path(None, replaced_path=False)
                            if self.move(context, context.location_system.require_location(path[0])):
                                self._replace_path(path)

                context.enemy.set_align()
                update_ui()

        def on_path_replaced(self):
            pass
        
        def reset(self, context):
            context.stop_moving.clear()
            super(EnemyMoveModule, self).reset(context)

        def move(self, context, location=None):
            if location is None:
                current_location_id = self.current_location_id
                if current_location_id is None:
                    return False
                location = context.location_system.require_location(current_location_id)
            try:
                context.enemy.move(location, ignore_door=context.get("move_module_ignore_door", False))
                update_ui()
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

            return _random.random() < 1.0 - _math.exp(-rate * dt)

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

        def get_relative_location(self, context, distance):
            distance = int(distance)

            if distance >= 0:
                location_id = self.get_next_location_id(distance)
            else:
                location_id = self.get_previous_location_id(-distance)
            if location_id is None:
                return

            location = context.location_system.get_location(location_id)
            if location is None:
                return

            return location

    class EnemyMoveElementTriggerModule(EnemyMoveModule):
        __slots__ = ("_triggers", "_target_trigger", "_check_time",)

        def __init__(self, *args, **kwargs):
            kwargs["ignore_player"] = True
            check_time = kwargs.pop("check_time", 1.0)
            elements_triggers = kwargs.pop("elements_triggers", None)
            if elements_triggers is None:
                elements_triggers = ()
            super(EnemyMoveElementTriggerModule, self).__init__(*args, **kwargs)

            check.expect_type(check_time, is_number, "check_time", "числом")
            check.expect_value(check_time, lambda value: value >= 0.1, "speed", "больше или равным 0.1")

            triggers = []
            names = set()

            for i, trigger in enumerate(elements_triggers):
                check.expect_type(trigger, lambda value: isinstance(value, EnemyElementTrigger), "trigger", "'EnemyElementTrigger'")

                if trigger.name in names:
                    raise FNaSRValueError("Триггер для элемента '{}' уже добавлен.".format(trigger.name))

                names.add(trigger.name)
                triggers.append(trigger)

            self._triggers = tuple(triggers)
            self._setattr("_target_trigger", None)
            self._setattr("_check_time", check_time)

        def start(self, context):
            super(EnemyMoveElementTriggerModule, self).start(context)
            context.move_wait_door_open = True

        def update(self, context, dt):
            self._accumulated_time += dt
            self._target_handle(context)
            super(EnemyMoveElementTriggerModule, self).update(context, dt)
            self._handle_target(context)

        def on_path_replaced(self):
            self._target_trigger = None

        def _target_handle(self, context):
            if not self._accumulated_time >= self._check_time:
                return
            
            self._accumulated_time -= self._check_time

            if self._target_trigger is not None:
                location = context.location_system.get_location(self._path[-1])
                if not self._target_trigger.condition(self, context, location):
                    self.generate_new_path(context.enemy.current_location.id)
                return

            enemy = context.enemy
            current_location = enemy.current_location

            if current_location is None:
                return

            targets, all_ids = self._collect_targets(context)

            if not all_ids:
                if self.is_last:
                    self.generate_new_path(current_location.id)
                return

            path = PathGenerator.generate_nearest_element_path(current_location.id, all_ids)

            if path is None:
                if self.is_last:
                    self.generate_new_path(current_location.id)
                return

            target_id = path[-1]

            for trigger, ids in targets:
                if target_id in ids:
                    self._replace_path(path)
                    self._target_trigger = trigger
                    return

        def _handle_target(self, context):
            if self._target_trigger is None or not self.is_last:
                return

            trigger = self._target_trigger
            self._target_trigger = None

            location = context.location_system.get_location(self.current_location_id)

            trigger.handle(self, context, location)

        def _collect_targets(self, context):
            location_system = context.location_system

            targets = []
            all_ids = set()

            for trigger in self._triggers:
                ids = set()

                for location_id in location_system.get_locations_with(trigger.name):
                    location = location_system.get_location(location_id)

                    if location is not None and trigger.condition(self, context, location):
                        ids.add(location_id)

                if ids:
                    targets.append((trigger, ids))
                    all_ids.update(ids)

            return targets, all_ids

        def get_debug_list_texts(self, enemy_context):
            return super(EnemyMoveElementTriggerModule, self).get_debug_list_texts(enemy_context) + [
                "triggers: {}".format(self._triggers),
                "target: {}".format(self._target_trigger),
                "check time: {}/{}".format(self._accumulated_time, self._check_time)
            ]


    class EnemyAggressiveModule(EnemyModule): # TODO: Наверное стоит отделить способность убивать от этого модуля
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
            speed = max(GlobalState.get("moving_animation_speed", 1.0), 0.5)
            if speed > 0:
                return self._safety_time + 1.8 / speed
            return self._safety_time

        def on_include(self, enemy):
            context = enemy.context
            
            if context.get("player_manager") is None:
                context.remember("player_manager", require_system("player"))

            if context.get("cycle") is None:
                context.remember("cycle", require_system("cycle"))

        def start(self, context):
            self.record_safety_time()
            if context.get("is_player_dead") is None:
                context.is_player_dead = False

        def update(self, context, dt):
            if context.is_player_dead:
                return

            player = context.player_manager.current_player
            if player.current_location is None:
                return

            if context.enemy.current_location is None:
                return

            if player.current_location.id != context.enemy.current_location.id:
                self._current_safety_time = 0.0
                return

            self._current_safety_time += dt
            if self._current_safety_time >= self.get_current_safety_time():
                self._current_safety_time = 0.0
                self._kill_player(context, player)

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

    class EnemyBulbAggressiveModule(EnemyAggressiveModule):
        __slots__ = "_inverted", "_symmetric_drain", "_interaction_time", "_current_interaction_time", "_move_module"

        dependent_modules = EnemyMoveModule,
        conflicting_modules = EnemyAggressiveModule,

        def __init__(self, *args, **kwargs):
            inverted = bool(kwargs.pop("inverted", False))
            symmetric_drain = bool(kwargs.pop("symmetric_drain", False))
            bulb_interaction_time = kwargs.pop("bulb_interaction_time", 3.0)

            super(EnemyBulbAggressiveModule, self).__init__(*args, **kwargs)

            check.expect_type(bulb_interaction_time, is_number, "bulb_interaction_time", "числом")
            check.expect_value(bulb_interaction_time, lambda value: value >= 0.1, "bulb_interaction_time", "больше или равным 0.1")

            self._setattr("_inverted", inverted)
            self._setattr("_symmetric_drain", symmetric_drain)
            self._setattr("_interaction_time", float(bulb_interaction_time))
            self._setattr("_current_interaction_time", 0.0)
            self._setattr("_move_module", None)

        @property
        def inverted(self):
            return self._inverted

        @property
        def symmetric_drain(self):
            return self._symmetric_drain

        @property
        def interaction_time(self):
            return self._interaction_time

        def on_include(self, enemy):
            super(EnemyBulbAggressiveModule, self).on_include(enemy)
            context = enemy.context

            if context.get("location_system") is None:
                context.remember("location_system", require_system("location"))

        def start(self, context):
            super(EnemyBulbAggressiveModule, self).start(context)
            self._move_module = self.get_module(context.enemy, EnemyMoveModule)
            context.move_wait_door_open = True

        def update(self, context, dt):
            if context.is_player_dead:
                return

            player = context.player_manager.current_player
            if player.current_location is None or context.enemy.current_location is None:
                return

            if player.current_location.id != context.enemy.current_location.id:
                self._current_safety_time = 0.0
                self._current_interaction_time = 0.0
                return

            is_lamp_active = not player.has_bulb or player.current_location.bulb.is_on
            should_gain_time = not is_lamp_active if self._inverted else is_lamp_active

            if should_gain_time:
                self._current_safety_time += dt
            else:
                drain = dt * 0.5 if self._symmetric_drain else dt
                self._current_safety_time -= drain
                #self._current_safety_time = max(0.0, self._current_safety_time - drain)

            if self._current_safety_time <= 0:
                self._current_interaction_time += dt
                if self._current_interaction_time >= self._interaction_time:
                    self._loss_attack(context)
                    return
            else:
                self._current_interaction_time = 0.0

            if self._current_safety_time >= self.get_current_safety_time():
                self._current_safety_time = 0.0
                self._current_interaction_time = 0.0
                self._kill_player(context, player)

        def _loss_attack(self, context):
            self._current_interaction_time = 0.0
            self._current_safety_time = 0.0

            player_location_id = context.player_manager.current_player.current_location.id
            move_module = self._move_module

            if move_module.start_location_id is not None and player_location_id != move_module.start_location_id:
                path = move_module.generate_new_path(
                    replaced_path=False,
                    player_location_id=player_location_id
                )
            else:
                path = move_module.generate_new_path(
                    start_location_id=None,
                    replaced_path=False,
                    player_location_id=player_location_id
                )

            if move_module.move(context, context.location_system.require_location(path[0])):
                move_module._replace_path(path)

        def get_debug_list_texts(self, enemy_context):
            return super(EnemyBulbAggressiveModule, self).get_debug_list_texts(enemy_context) + [
                "inverted: {}".format(self._inverted),
                "symmetric: {}".format(self._symmetric_drain),
                "interaction time: {}/{}".format(self._current_interaction_time, self._interaction_time)
            ]


    class EnemyAttackModule(EnemyModule):
        __slots__ = (
            "_move_module", "_attack_target_id",
            "_murder_countdown", "_r_t_m", "_sound_channel",
        )

        dependent_modules = (EnemyMoveModule,)
        conflicting_modules = tuple()

        def __init__(self, random_time_murder=(4,6,), sound_channel="enemy_channel", **kwargs):
            super(EnemyAttackModule, self).__init__(**kwargs)

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

        @property
        def attack_target_id(self):
            return self._attack_target_id

        @property
        def sound_channel(self):
            return self._sound_channel

        def on_include(self, enemy):
            context = enemy.context
            
            if context.get("player_manager") is None:
                context.remember("player_manager", require_system("player"))

            if context.get("location_system") is None:
                context.remember("location_system", require_system("location"))

        def start(self, context):
            self._move_module = self.get_module(context.enemy, EnemyMoveModule)
            if context.get("is_player_dead") is None:
                context.is_player_dead = False

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

            location = self._move_module.get_relative_location(context, 1)
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
            player_location = player.current_location

            if player_location is not None and player_location.id == self._attack_target_id:
                if context.enemy.tag not in player.under_attack:
                    player.under_attack.append(context.enemy.tag)
            elif context.enemy.tag in player.under_attack:
                player.under_attack.remove(context.enemy.tag)

            self._attack(context)
            return True

        def _start_attack(self, context, attack_target):
            context.stop_moving.block(self)
            self._attack_target_id = attack_target.id
            # self._safety_time = 0.5
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

            if not self._move_module.move(context):
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

            self._move_module.move(context)
            self._finish_attack(context)

            if context.enemy.tag == "us":
                if _random.random() < 0.01:
                    random_s = (
                        renpy.store.sfx_hell_crickets_1,
                        renpy.store.sfx_hell_crickets_2,
                        renpy.store.sfx_hell_crickets_3,
                    )

                    main_executor.submit(audio.play, _random.choice(random_s), self._sound_channel, loop=False, fadeout=1, fadein=2)

        def _finish_attack(self, context):
            # self.reset_safety_time()
            player = context.player_manager.current_player
            self._attack_target_id = None
            self._murder_countdown = None
            context.stop_moving.unblock(self)
            if context.enemy.tag in player.under_attack:
                player.under_attack.remove(context.enemy.tag)

        def _get_time_murder(self):
            return _random.randint(self._r_t_m[0], self._r_t_m[1])

        def _is_murder_time(self):
            if self._murder_countdown is None:
                self._murder_countdown = self._get_time_murder()

            self._murder_countdown -= 1

            if self._murder_countdown > 0:
                return False

            self._murder_countdown = None
            return True

        def player_present(self, context, location):
            player = context.player_manager.current_player
            if player.current_location is None:
                return False
            if player.current_location.id != location.id:
                return False
            return True

        def get_debug_list_texts(self, enemy_context):
            return [
                "murder countdown: {}".format(self._murder_countdown),
                "attack target id: {}".format(self._attack_target_id),
            ]

    class EnemySilentAttackModule(EnemyAttackModule):
        __slots__ = ("_silent_locations", "_replaced",)

        conflicting_modules = tuple()

        def __init__(self, silent_locations=None, **kwargs):
            super(EnemySilentAttackModule, self).__init__(**kwargs)

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

                normalized[LocationTools.normalize_id(location_id)] = tuple(variants)

            self._silent_locations = normalized
            self._setattr("_replaced", False)

        @property
        def silent_locations(self):
            return tuple(iter_keys(self._silent_locations))

        @property
        def replaced(self):
            return self._replaced

        def update(self, context, dt):
            self._replace_image(context)
            super(EnemySilentAttackModule, self).update(context, dt)

        def _start_attack(self, context, attack_target):
            self._attack_target_id = attack_target.id

            data = self._silent_locations.get(attack_target.id)

            if not attack_target.is_replaced_image and data:
                self._replace_image(context)
            else:
                main_executor.submit(audio.play, resources.sounds.sfx["enemy_deep_steps"],self._sound_channel)

            context.stop_moving.block(self)
            self._attack(context)
            
        def _choose_silent_variant(self, variants):
            if not variants:
                return None

            roll = _random.random() * 100.0
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
            if _random.random() < 0.1:
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
        __slots__ = (
            "_button", "_button_press_duration", "_signal_sound", "_signal_channel",
            "_key", "_signal", "_show_button", "_player", "_move_module",
        )

        KEY = "v1_enemy_signal_button_module_%s"

        dependent_modules = (EnemyMoveModule,)

        def __init__(
            self,
            button_press_duration=3,
            button_image=None,
            signal_sound=None,
            signal_channel="signal",
            button_align=(0.25, 0.89),
            xysize=(290 / 2, 60 / 2),
            **kwargs
        ):
            super(EnemySignalButtonModule, self).__init__(**kwargs)

            if button_image is None:
                button_image = resources.images.other["Signal_button"]
            if signal_sound is None:
                signal_sound = resources.sounds.sfx["tablet_scaring_sound"]

            if not is_number(button_press_duration):
                raise FNaSRTypeError("'button_press_duration' должен быть числом, получено: {}".format(type(button_press_duration)))
            if button_press_duration < 1:
                raise FNaSRValueError("'button_press_duration' должен быть положительным, получено: {}".format(button_press_duration))
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
            xsize = int(round(vp.scale_scalar(xysize[0])))
            ysize = int(round(vp.scale_scalar(xysize[1])))

            self._button_press_duration = float(button_press_duration)
            self._signal_sound = signal_sound
            self._signal_channel = signal_channel
            self._key = None

            self._button = HoldingMouseImageButton(
                idle=build_transform(button_image, width=int(xysize[0]), height=int(xysize[1])),
                click_action=renpy.store.Function(self._handle_button, True),
                unclick_action=renpy.store.Function(self._handle_button, False),
                allow_alternate=True,
                align=button_align,
            )

            self._setattr("_signal", False)
            self._setattr("_show_button", False)
            self._setattr("_player", None)
            self._setattr("_move_module", None)

        def on_include(self, enemy):
            context = enemy.context
            self._key = self.KEY % context.enemy.tag
            
            if context.get("player_manager") is None:
                context.remember("player_manager", require_system("player"))

        def start(self, context):
            self._player = context.player_manager.current_player
            if self._player is None:
                raise FNaSRRuntimeError("'current_player' не указан.")
            self._move_module = self.get_module(context.enemy, EnemyMoveModule)

        def update(self, context, dt):
            self._handle_render_button(context)

            if not self._signal:
                self._accumulated_time = 0.0
                return

            self._accumulated_time += dt
            while self.interval(self._button_press_duration):
                self._scare_away(context)

        def _scare_away(self, context):
            if self._move_module is None:
                return

            self._accumulated_time = 0.0
            player = self._player

            if player.current_location is None:
                self._move_module.generate_new_path()
            elif self._move_module.start_location_id is not None and player.current_location.id != self._move_module.start_location_id:
                self._move_module.generate_new_path()
            else:
                self._move_module.generate_new_path(None)

            self._move_module.move(context)

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
            main_executor.submit(visual.show, self._key, what=self._button, layer="screens")
            update_ui()

        def _hide(self):
            if not self._show_button:
                return
            self._show_button = False
            self._signal = False
            main_executor.submit(audio.stop, self._signal_channel)
            main_executor.submit(visual.hide, self._key, layer="screens")
            update_ui()

        def _handle_button(self, s):
            self._signal = bool(s)
            if self._signal:
                main_executor.submit(audio.play, self._signal_sound, self._signal_channel, loop=True)
            else:
                main_executor.submit(audio.stop, self._signal_channel)

        def reset(self, context):
            main_executor.submit(audio.stop, self._signal_channel)
            main_executor.submit(visual.hide, self._key, layer="screens")
            super(EnemySignalButtonModule, self).reset(context)
            self._button.force_unclick()

        def get_debug_list_texts(self, enemy_context):
            return [
                "button press: {}/{}".format(self._accumulated_time, self._button_press_duration),
                "signal: {}".format(self._signal),
                "show button: {}".format(self._show_button)
            ]


    class EnemyInteractiveModule(EnemyModule):
        __slots__ = (
            "_needs_clicks", "_downtime", "_sprite_button",
            "_clicks", "_move_module", "_context",
        )

        dependent_modules = (EnemyMoveModule,)

        def __init__(
            self,
            needs_clicks=10,
            downtime=1.0,
            **kwargs
        ):
            super(EnemyInteractiveModule, self).__init__(**kwargs)

            if not is_strict_integer(needs_clicks):
                raise FNaSRTypeError("'needs_clicks' должен быть целым числом, получено: {}".format(type(needs_clicks)))
            if needs_clicks <= 0:
                raise FNaSRValueError("'needs_clicks' должен быть больше нуля.")

            if not is_number(downtime):
                raise FNaSRTypeError("'downtime' должен быть числом, получено: {}".format(type(downtime)))
            if downtime < 1:
                raise FNaSRValueError("'downtime' должен быть положительным, получено: {}".format(downtime))

            self._needs_clicks = needs_clicks
            self._downtime = float(downtime)
            self._sprite_button = None

            self._setattr("_clicks", 0)
            self._setattr("_move_module", None)
            self._setattr("_context", None)

        @property
        def needs_clicks(self):
            return self._needs_clicks

        @property
        def downtime(self):
            return self._downtime

        def on_include(self, enemy):
            context = enemy.context
            
            if context.get("player_manager") is None:
                context.remember("player_manager", require_system("player"))

            sprite = enemy.original_sprite

            parallax_sprite = Parallax(
                displayable=sprite,
                zoom=1.15,
                anchor=None,
                power=0.10,
                sharpness_factor=0.1,
                fill_viewport=True
            )

            self._sprite_button = ParallaxWrapper(
                renpy.display.behavior.ImageButton,
                idle_image=parallax_sprite,
                clicked=renpy.store.Function(self._click)
            )

        def start(self, context):
            self._move_module = self.get_module(context.enemy, EnemyMoveModule)
            if not context.enemy.replaced_parallax_sprite:
                context.enemy.replace_sprite(self._sprite_button, parallax=True)
            self._context = context

        def update(self, context, dt):
            if not self.sees_player(context):
                self._clicks = 0
                self._accumulated_time = 0.0
                return
            if self._clicks <= 0:
                self._accumulated_time = 0.0
                return
            self._accumulated_time += dt
            while self.interval(self._downtime):
                self._clicks = 0

        def sees_player(self, context):
            enemy_location = context.enemy.current_location
            if enemy_location is None:
                return False

            player = context.player_manager.current_player

            if player.current_location is None:
                return False

            return enemy_location.id == player.current_location.id

        def _click(self):
            self._accumulated_time = 0.0
            self._clicks += 1
            if self._clicks >= self._needs_clicks:
                self._scare_away(self._context)

        def _scare_away(self, context):
            if self._move_module is None:
                return

            self._clicks = 0
            player = context.player_manager.current_player

            if player.current_location is None:
                self._move_module.generate_new_path()
            elif self._move_module.start_location_id is not None and player.current_location.id != self._move_module.start_location_id:
                self._move_module.generate_new_path()
            else:
                self._move_module.generate_new_path(None)

            self._move_module.move(context)

        def get_debug_list_texts(self, enemy_context):
            return [
                "clicks: {}/{}".format(self._clicks, self._needs_clicks),
                "downtime: {}/{}".format(self._accumulated_time, self._downtime)
            ]


    class EnemyLockdownModule(EnemyModule):
        __slots__ = ("_block_list", "_player", "_is_block",)

        def __init__(self, block_list=None, **kwargs):
            super(EnemyLockdownModule, self).__init__(**kwargs)

            if block_list is None:
                block_list = set()

            if not isinstance(block_list, (list, tuple, set,)):
                raise FNaSRTypeError("'block_list' должен быть list, tuple или set, получено: {}".format(type(block_list)))

            for i in block_list:
                if not is_string(i):
                    raise FNaSRValueError("Все элементы 'block_list' должны быть строками, получено: {}".format(type(i)))

            self._setattr("_block_list", set(block_list))
            self._setattr("_player", None)
            self._setattr("_is_block", False)

        @property
        def block_list(self):
            return frozenset(self._block_list)

        @property
        def is_block(self):
            return self._is_block

        def on_include(self, enemy):
            context = enemy.context

            if context.get("player_manager") is None:
                context.remember("player_manager", require_system("player"))

        def start(self, context):
            self._player = context.player_manager.current_player
            if self._player is None:
                raise FNaSRRuntimeError("'current_player' не указан.")

        def update(self, context, dt):
            self._handle_block(context)

        def _handle_block(self, context):
            enemy = context.enemy
            if enemy.current_location is None:
                self.unblock()
                return

            if self._player.current_location is None:
                self.unblock()
                return

            if enemy.current_location.id != self._player.current_location.id:
                self.unblock()
                return

            self.block()

        def block(self):
            if self._is_block:
                return
            self._is_block = True
            for el in self._block_list:
                if el == PlayerElement.TABLET:
                    if self._player.is_open_tablet:
                        try:
                            main_executor.submit(screen_manager.hide_screen, "tablet", player=self._player, fast_switch=False)
                        except:
                            self._player.close_tablet()
                self._player.get_element(el).block(self)

        def unblock(self):
            if not self._is_block:
                return
            self._is_block = False
            for el in self._block_list:
                self._player.get_element(el).unblock(self)

        def get_debug_list_texts(self, enemy_context):
            return [
                "block list: {}".format(self._block_list),
                "is block: {}".format(self._is_block)
            ]


    class EnemySabotageGeneratorModule(EnemyModule):
        __slots__ = "_target_location_id", "_safety_time", "_blocked"

        @staticmethod
        def _validate_safety_time(safety_time):
            if not is_number(safety_time):
                raise FNaSRTypeError("'safety_time' должен быть числом, получено: {}".format(type(safety_time)))
            if safety_time <= 0:
                raise FNaSRValueError("'safety_time' должен быть положительным, получено: {}".format(safety_time))

        def __init__(self, target_location_id, safety_time=3.0, **kwargs):
            super(EnemySabotageGeneratorModule, self).__init__(**kwargs)

            target_location_id = LocationTools.normalize_id(target_location_id)
            self._validate_safety_time(safety_time)

            self._setattr("_target_location_id", target_location_id)
            self._setattr("_safety_time", float(safety_time))
            self._setattr("_blocked", False)

        @property
        def target_location_id(self):
            return self._target_location_id

        @target_location_id.setter
        def target_location_id(self, value):
            self._target_location_id = LocationTools.normalize_id(value)

        @property
        def is_blocked(self):
            return self._blocked

        @property
        def safety_time(self):
            return self._safety_time

        @safety_time.setter
        def safety_time(self, value):
            self._validate_safety_time(value)
            self._safety_time = float(value)

        def on_include(self, enemy):
            Generator.create_if_absent()
            cycle = require_system("cycle")
            generator = Generator()
            if not cycle.is_registered(generator):
                cycle.register(generator)

        def update(self, context, dt):
            if not self.is_located_target_location(context):
                if self._blocked:
                    self._blocked = False
                    Generator.enable(self)
                self._accumulated_time = 0.0
                return

            if self._blocked:
                return

            self._accumulated_time = min(self._accumulated_time + dt, self._safety_time)

            if self._accumulated_time < self._safety_time:
                return

            self._accumulated_time = 0.0
            self._blocked = True
            Generator.disable(self)

        def is_located_target_location(self, context):
            current_location = context.enemy.current_location
            if current_location is None:
                return False
            return current_location.id == self._target_location_id

        def get_debug_list_texts(self, enemy_context):
            return [
                "target location: {}".format(self._target_location_id),
                "safety time: {}/{}".format(self._accumulated_time, self._safety_time),
                "blocked: {}".format(self._blocked)
            ]


    class EnemyAgitationModule(EnemyModule):
        __slots__ = "_coefficient", "_agitation", "_sound", "_sound_channel", "_player"

        UPDATE_TIME = 0.1

        @staticmethod
        def _validate_ac(aggressiveness_coefficient):
            if not is_number(aggressiveness_coefficient):
                raise FNaSRTypeError("'aggressiveness_coefficient' должен быть числом, получено: {}".format(type(aggressiveness_coefficient)))
            if aggressiveness_coefficient <= 0:
                raise FNaSRValueError("'aggressiveness_coefficient' должен быть положительным, получено: {}".format(aggressiveness_coefficient))

        def __init__(
            self,
            aggressiveness_coefficient=2.0,
            sound=None,
            sound_channel="enemy_agitation_channel",
            **kwargs
        ):
            if sound is None:
                sound = renpy.store.music_list["miku_song_voice"]
            super(EnemyAgitationModule, self).__init__(**kwargs)

            self._validate_ac(aggressiveness_coefficient)
            if not is_string(sound):
                raise FNaSRTypeError("'sound' должен быть строкой, получено: {}".format(type(sound)))
            if not is_string(sound_channel):
                raise FNaSRTypeError("'sound_channel' должен быть строкой, получено: {}".format(type(sound_channel)))

            self._setattr("_coefficient", float(aggressiveness_coefficient))
            self._setattr("_agitation", False)
            self._setattr("_sound", sound)
            self._setattr("_sound_channel", sound_channel)
            self._setattr("_player", None)

        @property
        def aggressiveness_coefficient(self):
            return self._coefficient

        @aggressiveness_coefficient.setter
        def aggressiveness_coefficient(self, value):
            self._validate_ac(value)
            self._coefficient = float(value)

        @property
        def is_agitation(self):
            return self._agitation

        @property
        def sound_channel(self):
            return self._sound_channel

        def on_include(self, enemy):
            context = enemy.context
            
            if context.get("player_manager") is None:
                context.remember("player_manager", require_system("player"))

            if context.get("enemy_manager") is None:
                context.remember("enemy_manager", require_system("enemy"))

        def start(self, context):
            self._player = context.player_manager.current_player

        def update(self, context, dt):
            self._accumulated_time += dt
            while self.interval(self.UPDATE_TIME):
                if self.is_sees_player(context):
                    self.start_agitation(context)
                else:
                    self.stop_agitation(context)

        def is_sees_player(self, context):
            current_location = context.enemy.current_location
            player_location = self._player.current_location
            if current_location is None:
                return False
            if player_location is None:
                return False
            return current_location.id == player_location.id

        def start_agitation(self, context):
            if self._agitation:
                return

            for enemy in context.enemy_manager.iter_current_group:
                enemy_context = enemy.context
                value = enemy_context.get("moving_module_tempo_mult")

                if value is None:
                    value = 1.0

                enemy_context.moving_module_tempo_mult = value + self._coefficient

            self._agitation = True
            main_executor.submit(audio.play, self._sound, self._sound_channel, fadein=0.5)

        def stop_agitation(self, context):
            if not self._agitation:
                return

            for enemy in context.enemy_manager.iter_current_group:
                enemy_context = enemy.context
                value = enemy_context.get("moving_module_tempo_mult")

                if value is None:
                    value = 1.0

                enemy_context.moving_module_tempo_mult = value - self._coefficient

            self._agitation = False
            main_executor.submit(audio.stop, self._sound_channel, fadeout=0.5)

        def get_debug_list_texts(self, enemy_context):
            return [
                "coefficient: {}".format(self._coefficient),
                "agitation: {}".format(self._agitation)
            ]


    class EnemyPanicModule(EnemyModule):
        __slots__ = "_panic_add", "_scalable"

        HANDLE_INTERVAL = 1.0

        def __init__(self, panic_add=1, increment_scalable=False, **kwargs):
            super(EnemyPanicModule, self).__init__(**kwargs)

            check.expect_type(panic_add, is_strict_integer, "panic_add", "числом")

            self._setattr("_panic_add", panic_add)
            self._setattr("_scalable", bool(increment_scalable))

        @property
        def panic_add(self):
            return self._panic_add

        @property
        def is_scalable(self):
            return self._scalable

        def on_include(self, enemy):
            context = enemy.context

            if "player_manager" not in context:
                context.remember("player_manager", require_system("player"))

        def update(self, context, dt):
            self._accumulated_time += dt
            while self.interval(self.HANDLE_INTERVAL):
                self._handle(context)

        def _handle(self, context):
            player = context.player_manager.current_player
            player_location = player.current_location
            current_location = context.enemy.current_location

            if player_location is None or current_location is None:
                return

            if player_location.id != current_location.id:
                return

            panic_add = player.magnitude_change_panic + self.calculate_panic_add(context)
            player.panic += panic_add

        def calculate_panic_add(self, context):
            player = context.player_manager.current_player

            if not self._scalable:
                return self._panic_add

            return int(round(self._panic_add * player.max_panic / float(Player.DEFAULT_MAX_PANIC)))

        def get_debug_list_texts(self, enemy_context):
            return [
                "panic add: {}".format(self._panic_add),
                "is scalable: {}".format(self._scalable),
                "calculate panic: {}".format(self.calculate_panic_add(enemy_context)),
                "handle interval: {}".format(self.HANDLE_INTERVAL)
            ]


    class EnemyIgnoreModule(EnemyModule):
        __slots__ = "_ignore_seconds", "_move_module", "_player"

        dependent_modules = EnemyMoveModule,

        def __init__(self, ignore_seconds=3, **kwargs):
            super(EnemyIgnoreModule, self).__init__(**kwargs)

            check.expect_type(ignore_seconds, is_strict_integer, "ignore_seconds", "целым числом")
            check.expect_value(ignore_seconds, lambda value: value > 0, "ignore_seconds", "положительным числом")

            self._setattr("_ignore_seconds", ignore_seconds)
            self._setattr("_move_module", None)
            self._setattr("_player", None)

        @property
        def ignore_seconds(self):
            return self._ignore_seconds

        def on_include(self, enemy):
            context = enemy.context

            if "player_manager" not in context:
                context.remember("player_manager", require_system("player"))

            if "location_system" not in context:
                context.remember("location_system", require_system("location"))

        def start(self, context):
            self._move_module = self.get_module(context.enemy, EnemyMoveModule)
            self._player = context.player_manager.current_player

        def update(self, context, dt):
            player = self._player
            player_location = player.current_location
            current_location = context.enemy.current_location
            if current_location is None or player_location is None:
                return

            if current_location.id != player_location.id or not player.is_open_tablet:
                self._accumulated_time = 0.0
                return
            
            self._accumulated_time += dt
            if not self.interval(self._ignore_seconds):
                return

            self._accumulated_time = 0.0
            player_location_id = player_location.id
            move_module = self._move_module

            if move_module.start_location_id is not None and player_location_id != move_module.start_location_id:
                path = move_module.generate_new_path(
                    replaced_path=False,
                    player_location_id=player_location_id
                )
            else:
                path = move_module.generate_new_path(
                    start_location_id=None,
                    replaced_path=False,
                    player_location_id=player_location_id
                )

            if move_module.move(context, context.location_system.require_location(path[0])):
                move_module._replace_path(path)

        def get_debug_list_texts(self, enemy_context):
            return [
                "ignore: {}/{}".format(self._accumulated_time, self._ignore_seconds)
            ]
    

    class EnemyBulbScareModule(EnemyModule):
        __slots__ = "_inverted", "_time_scared", "_move_module", "_player"

        dependent_modules = EnemyMoveModule,

        def __init__(self, time_scared=3, inverted=False, **kwargs):
            super(EnemyBulbScareModule, self).__init__(**kwargs)

            check.expect_type(time_scared, is_strict_integer, "time_scared", "целым числом")
            check.expect_value(time_scared, lambda value: value > 0, "time_scared", "положительным числом")

            self._setattr("_inverted", bool(inverted))
            self._setattr("_time_scared", int(time_scared))
            self._setattr("_move_module", None)
            self._setattr("_player", None)

        @property
        def inverted(self):
            return self._inverted

        @property
        def time_scared(self):
            return self._time_scared

        def on_include(self, enemy):
            context = enemy.context

            if "player_manager" not in context:
                context.remember("player_manager", require_system("player"))

        def start(self, context):
            self._move_module = self.get_module(context.enemy, EnemyMoveModule)
            self._player = context.player_manager.current_player

        def update(self, context, dt):
            player = self._player
            player_location = player.current_location
            current_location = context.enemy.current_location

            if player_location is None or current_location is None:
                self._accumulated_time = 0.0
                return
            if player_location.id != current_location.id or not player.has_bulb:
                self._accumulated_time = 0.0
                return

            increasing = player_location.bulb.is_on != self._inverted
            self._accumulated_time += dt if increasing else -dt
            self._accumulated_time = min(max(self._accumulated_time, 0.0), self._time_scared)

            if self._accumulated_time >= self._time_scared:
                self._accumulated_time = 0.0
                player_location_id = player_location.id
                move_module = self._move_module

                if move_module.start_location_id is not None and player_location_id != move_module.start_location_id:
                    path = move_module.generate_new_path(
                        replaced_path=False,
                        player_location_id=player_location_id
                    )
                else:
                    path = move_module.generate_new_path(
                        start_location_id=None,
                        replaced_path=False,
                        player_location_id=player_location_id
                    )

                if move_module.move(context, context.location_system.require_location(path[0])):
                    move_module._replace_path(path)


    class EnemySoundFootstepsModule(EnemyModule):
        __slots__ = "_check_interval", "_steps_left", "_footsteps_audio", "_channel", "_move_module", "_is_play"

        dependent_modules = EnemyMoveModule,

        def __init__(self, check_interval=0.1, steps_left=1, footsteps_audio=None, channel="enemy_footsteps_channel", **kwargs):
            super(EnemySoundFootstepsModule, self).__init__(**kwargs)

            if footsteps_audio is None:
                footsteps_audio = resources.sounds.sfx["enemy_deep_steps"]

            check.expect_type(check_interval, is_number, "check_interval", "числом")
            check.expect_value(check_interval, lambda value: value >= 0.1, "check_interval", "больше или равным 0.1")
            check.expect_type(steps_left, is_strict_integer, "steps_left", "целым числом")
            check.expect_value(steps_left, lambda value: value >= 0, "steps_left", "не отрицательным")
            check.expect_type(footsteps_audio, is_string, "footsteps_audio", "строкой")
            check.expect_type(channel, is_string, "channel", "строкой")

            self._setattr("_check_interval", check_interval)
            self._setattr("_steps_left", steps_left)
            self._setattr("_footsteps_audio", footsteps_audio)
            self._setattr("_channel", channel)
            self._setattr("_move_module", None)
            self._setattr("_is_play", None)

        @property
        def check_interval(self):
            return self._check_interval

        @property
        def steps_left(self):
            return self._steps_left

        @property
        def footsteps_audio(self):
            return self._footsteps_audio

        @property
        def channel(self):
            return self._channel

        def start(self, context):
            self._move_module = self.get_module(context.enemy, EnemyMoveModule)

        def update(self, context, dt):
            self._accumulated_time += dt
            while self.interval(self._check_interval):
                if self._move_module.steps_left == self._steps_left:
                    if not self._is_play:
                        self._is_play = True
                        main_executor.submit(audio.play, self._footsteps_audio, self._channel)
                else:
                    self._is_play = False

        def get_debug_list_texts(self, enemy_context):
            return [
                "steps left: {}=={}".format(self._move_module.steps_left, self._steps_left),
                "is play: {}".format(self._is_play)
            ]
                

    class EnemyCallAggressiveModule(EnemyModule):
        __slots__ = (
            "_enemy_screamer", "_button_image", "_button", "_key",
            "_interval", "_change", "_call_time", "_current_call_time",
            "_is_call", "_delayed_call", "_target_location_id", "_player",
            "_call_phone_sound", "_answer_phone_sound", "_call_phone_channel",
            "_is_show_button", "_cooldown", "_current_cooldown", "_button_transform",
            "_context"
        )

        KEY = "v1_enemy_call_aggressive_module_%s"
        MIN_CHANGE = 0.001

        def __init__(
            self,
            enemy_screamer,
            interval=5.0,
            change=0.1,
            call_time=12.0,
            cooldown=10,
            image_button=None,
            alpha_button=0.2,
            size_button=(290//3, 60//3),
            call_phone_sound=None,
            answer_phone_sound=None,
            call_phone_channel="enemy_call_phone_channel",
            **kwargs
        ):
            super(EnemyCallAggressiveModule, self).__init__(**kwargs)

            if image_button is None:
                image_button = resources.images.other["call_button"]
            if call_phone_sound is None:
                call_phone_sound = resources.sounds.sfx["call"]
            if answer_phone_sound is None:
                answer_phone_sound = resources.sounds.sfx["answer_phone"]


            check.expect_type(enemy_screamer, lambda value: isinstance(value, EnemyScreamer), "enemy_screamer", "'EnemyScreamer'")
            check.expect_type(interval, is_number, "interval", "числом")
            check.expect_value(interval, lambda value: value >= 0.1, "interval", "больше или равным 0.1")
            check.expect_type(change, is_number, "change", "числом")
            check.expect_value(change, lambda value: value >= self.MIN_CHANGE and value <= 1.0, "change", "в диапазоне от {} до 1.0".format(self.MIN_CHANGE))
            check.expect_type(call_time, is_number, "call_time", "числом")
            check.expect_value(call_time, lambda value: value >= 0.1, "call_time", "больше или равным 0.1")
            check.expect_type(cooldown, is_strict_integer, "cooldown", "целым числом")
            check.expect_value(cooldown, lambda value: value >= 0, "cooldown", "больше или равным нулю")
            check.expect_type(alpha_button, is_number, "alpha_button", "числом")
            check.expect_value(alpha_button, lambda value: value >= 0.0 and value <= 1.0, "alpha_button", "в диапазоне от 0.0 до 1.0")
            check.expect_type(size_button, lambda value: isinstance(value, (list, tuple,)), "size_button", "списком или кортежем")
            check.expect_value(size_button, lambda value: len(value) == 2, "size_button", "ровно из двух элементов")
            for i in range(2):
                v = size_button[i]
                check.expect_type(v, is_strict_integer, "size_button[{}]".format(i), "целым числом")
                check.expect_value(v, lambda value: value >= 1, "size_button[{}]".format(i), "положительным")

            check.expect_type(call_phone_sound, is_string, "call_phone_sound", "строкой")
            check.expect_type(answer_phone_sound, is_string, "answer_phone_sound", "строкой")
            check.expect_type(call_phone_channel, is_string, "call_phone_channel", "строкой")

            self._key = self.KEY
            self._button_image = build_transform(image_button, alpha=alpha_button, width=int(size_button[0]), height=int(size_button[1]))
            self._button = renpy.display.behavior.ImageButton(
                idle_image=self._button_image,
                clicked=renpy.store.Function(self.answer_phone)
            )
            self._button_transform = renpy.display.transform.Transform(
                child=self._button,
                xpos=_random.randint(0, renpy.config.screen_width),
                ypos=_random.randint(0, renpy.config.screen_height)
            )

            self._enemy_screamer = enemy_screamer

            self._setattr("_interval", float(interval))
            self._setattr("_change", float(change))
            self._setattr("_call_time", float(call_time))
            self._setattr("_current_call_time", 0.0)
            self._setattr("_is_call", False)
            self._setattr("_delayed_call", False)
            self._setattr("_target_location_id", None)
            self._setattr("_player", None)
            self._setattr("_call_phone_sound", call_phone_sound)
            self._setattr("_answer_phone_sound", answer_phone_sound)
            self._setattr("_call_phone_channel", call_phone_channel)
            self._setattr("_is_show_button", False)
            self._setattr("_cooldown", cooldown)
            self._setattr("_current_cooldown", float(cooldown))
            self._setattr("_context", None)

            game.add_paused_fn(self._paused)
            game.add_unpaused_fn(self._unpaused)

        @property
        def call_time(self):
            return self._call_time

        @property
        def is_call(self):
            return self._is_call

        @property
        def delayed_call(self):
            return self._delayed_call

        @property
        def target_location_id(self):
            return self._target_location_id

        @property
        def call_phone_channel(self):
            return self._call_phone_channel

        def on_include(self, enemy):
            self._key = self._key % enemy.tag
            context = enemy.context

            if "player_manager" not in context:
                context.remember("player_manager", require_system("player"))

            if "cycle" not in context:
                context.remember("cycle", require_system("cycle"))

        def start(self, context):
            self._context = _weakref.ref(context)
            self._player = context.player_manager.current_player
            if "is_player_dead" not in context:
                context.is_player_dead = False

        def update(self, context, dt):
            if context.is_player_dead:
                return

            if self._is_call:
                self.sync_state(context)
                self._handle(context, dt)
                return

            player = self._player
            
            if player.current_location is None:
                return

            if not player.has_tablet and not player.has_bulb:
                return

            if self._current_cooldown >= 0:
                self._current_cooldown = max(0.0, self._current_cooldown - dt)
                return

            if self._delayed_call:
                if player.is_moving:
                    return
                self.call_phone()
                self.sync_state(context)
                return

            self._accumulated_time += dt
            while self.interval(self._interval):
                if self.change():
                    if player.is_moving:
                        self._delayed_call = True
                        return
                    self.call_phone()
                    self.sync_state(context)
                    return

        def change(self):
            return _random.random() <= self._change

        def call_phone(self):
            if self._is_call:
                return

            self._is_call = True
            self._accumulated_time = 0.0
            self._delayed_call = False
            self._target_location_id = self._player.current_location.id

            main_executor.submit(audio.play, self._call_phone_sound, self._call_phone_channel, loop=True)
            main_executor.submit(self._set_button_pos)

        def answer_phone(self):
            if not self._is_call:
                return

            self._is_call = False
            self._target_location_id = None
            self._current_call_time = 0.0
            self._current_cooldown = self._cooldown

            main_executor.submit(audio.play, self._answer_phone_sound, self._call_phone_channel, loop=False)
            self._hide_button()

        def sync_state(self, context):
            if not self._is_call:
                self._hide_button()
                return

            player = self._player
            
            if player.current_location is None:
                self._hide_button()
                return

            if player.current_location.id != self._target_location_id:
                self._hide_button()
                return

            self._show_button()

        def _show_button(self):
            if self._is_show_button:
                return
            self._is_show_button = True
            main_executor.submit(visual.show, self._key, what=self._button_transform, layer="screens")

        def _hide_button(self):
            if not self._is_show_button:
                return
            self._is_show_button = False
            main_executor.submit(visual.hide, self._key, layer="screens")

        def _handle(self, context, dt):
            if not self._is_call:
                return

            self._current_call_time += dt
            if self._current_call_time >= self._call_time:
                self._kill_player(context, self._player)

        def _kill_player(self, context, player): # TODO: Может быть заменить на вызов указанной функции, вместо убийства игрока
            if player.try_kill():
                main_executor.submit(audio.stop, self._call_phone_channel)
                self._hide_button()
                GlobalState.set_if_absent("OpponentKilledPlayer", (context.enemy.tag, self._enemy_screamer, require_system("time").get_time(),))
                context.is_player_dead = True
                context.cycle.request_transition("v1_night_screamer_label_FNaSR")
            else:
                self.answer_phone()

        def _set_button_pos(self, xpos=None, ypos=None):
            sw = renpy.config.screen_width
            sh = renpy.config.screen_height

            if xpos is None:
                xpos = _random.randint(int(sw * 0.1), int(sw * 0.9))
            if ypos is None:
                ypos = _random.randint(int(sh * 0.1), int(sh * 0.9))

            self._button_transform.xpos = xpos
            self._button_transform.ypos = ypos
            self._button_transform.update()

        def get_debug_list_texts(self, enemy_context):
            info = [
                "interval: {}/{}".format(self._accumulated_time, self._interval),
                "change: {}".format(self._change),
                "cooldown: {}/{}".format(self._current_cooldown, self._cooldown),
                "is call: {}".format(self._is_call),
                "delayed call: {}".format(self._delayed_call),
                "show button: {}".format(self._is_show_button),
            ]
            if self._is_call:
                info.append("call time: {}/{}".format(self._current_call_time, self._call_time))
                info.append("target id: {}".format(self._target_location_id))

            return info

        def _paused(self):
            if not self._is_call:
                return

            main_executor.submit(audio.stop, self._call_phone_channel)
            main_executor.submit(visual.hide, self._key, layer="screens")

        def _unpause(self):
            if not self._is_call:
                return

            main_executor.submit(audio.play, self._call_phone_sound, self._call_phone_channel, loop=True)
            if self._context is not None:
                context = self._context()
                if context is not None:
                    self.sync_state(context)

















    EnemyMoveModule.conflicting_modules = (
        EnemyMoveElementTriggerModule,
    )

    EnemyMoveElementTriggerModule.conflicting_modules = (
        EnemyMoveModule,
    )


    EnemyAttackModule.conflicting_modules = (
        EnemySilentAttackModule,
    )

    EnemySilentAttackModule.conflicting_modules = (
        EnemyAttackModule, EnemySoundFootstepsModule,
    )

