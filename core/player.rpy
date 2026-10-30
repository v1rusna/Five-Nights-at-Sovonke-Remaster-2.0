# player.rpy
init -1 python in v1FNaSR:
    from __future__ import division
    import threading as _threading

    audio.register_channel("heartbeat", "ambience", loop=True)
    audio.register_channel("breathing", "ambience", loop=True)

    class PlayerElement(object):
        TABLET = "tablet"
        DOOR = "door"
        BULB = "bulb"

    class Player(GameObject, BaseAI):
        def __init__(self, id, max_panic=15, magnitude_change_panic=1):
            super(Player, self).__init__()

            max_panic = int(max_panic)
            magnitude_change_panic = int(magnitude_change_panic)
            if max_panic <= 0:
                raise FNaSRValueError("'max_panic' cannot be less than or equal to zero")
            if magnitude_change_panic < 0:
                raise FNaSRValueError("'magnitude_change_panic' cannot be less than zero")

            self._id = to_text(id)

            self._setattr("_open_tablet", False)
            self._setattr("_is_moving", False)
            self._under_attack = ElementContainer()

            self._setattr("_panic", 0)
            self._setattr("_max_panic", max_panic)
            self._setattr("_magnitude_change_panic", magnitude_change_panic)
            self._setattr("_rollback", False)
            self._setattr("_rollback_threshold", round(self._max_panic * 2 / 3))
            self._setattr("_is_play_heartbeat", False)
            self._setattr("_died", False)
            self._setattr("_god_mode", False)

            self._element_enabled = {
                PlayerElement.TABLET: MultiLock(),
                PlayerElement.DOOR: MultiLock(),
                PlayerElement.BULB: MultiLock(),
            }

        @property
        def id(self):
            return self._id

        @property
        def is_open_tablet(self):
            return self._open_tablet

        @property
        def has_tablet(self):
            if self._current_location is None:
                return False
            return self._current_location.tablet is not None

        @property
        def is_moving(self):
            return self._is_moving

        @property
        def under_attack(self):
            return self._under_attack

        @property
        def panic(self):
            return self._panic

        @property
        def max_panic(self):
            return self._max_panic

        @property
        def has_door(self):
            if self._current_location is None:
                return False
            return self._current_location.door is not None

        @property
        def is_rollback_panic(self):
            return self._rollback

        @property
        def rollback_threshold(self):
            return self._rollback_threshold

        @property
        def has_bulb(self):
            if self._current_location is None:
                return False
            return self._current_location.bulb is not None

        @property
        def is_died(self):
            return self._died

        @property
        def god_mode(self):
            return self._god_mode

        @god_mode.setter
        def god_mode(self, value):
            if is_debug():
                self._god_mode = bool(value)
            else:
                self._god_mode = False

        def get_element(self, element):
            try:
                return self._element_enabled[element]
            except KeyError:
                raise FNaSRValueError("Элемент '{}' не найден.".format(element)) 

        def try_kill(self):
            if self._god_mode:
                return False
            self._died = True
            return True

        def get_panic_text(self):
            return "{}/{}".format(self._panic, self._max_panic)

        def set_moving(self, value):
            self._is_moving = bool(value)

        def get_sees_image(self):
            if self._current_location is None:
                raise FNaSRValueError("The player is not in any location")

            if not self._open_tablet:
                return self._current_location.parallax_image

            selected = self._current_location.tablet.selected

            if selected is None:
                raise FNaSRException("No location has been selected on the tablet")

            loc = self._current_location.location_system.require_location(selected)

            return loc.image

        def move(self, location, allow_migrate=False):
            if self.is_open_tablet:
                raise FNaSRException("You cannot move to other locations while the tablet is open")

            super(Player, self).move(location, allow_migrate)

            ambience_manager.sync_player(self)

        def open_tablet(self):
            if self.get_element(PlayerElement.TABLET).blocked:
                return
            if self._current_location is None:
                raise FNaSRValueError("The player is not in any location")
            if not self.has_tablet:
                raise FNaSRException("There is no tablet in the current location({})".format(self._current_location.id))
            self._open_tablet = True
            self._current_location.tablet.is_open = True
            ambience_manager.sync_player(self)

        def close_tablet(self):
            if self._current_location is None:
                raise FNaSRValueError("The player is not in any location")
            if not self.has_tablet:
                raise FNaSRException("There is no tablet in the current location({})".format(self._current_location.id))
            self._open_tablet = False
            self._current_location.tablet.is_open = False
            ambience_manager.sync_player(self)

        def switch_tablet(self):
            if self.is_open_tablet:
                self.close_tablet()
            else:
                self.open_tablet()

        @timed("player.update", budget=lambda: 1.0 / max(require_system("cycle").fps_controller.target_fps, 1.0), log_every=1)
        def update(self, dt):
            if self._died:
                return
            
            location = self._current_location

            if location is None:
                return

            self._accumulated_time += dt
            while self.interval():
                door = location.door
                panic_step = self._magnitude_change_panic
                panic_changed = False

                if door is not None and not door.is_open:
                    panic_changed = True
                    self._panic += panic_step

                    if not self._is_play_heartbeat and self._panic >= self._max_panic / 2:
                        self._is_play_heartbeat = True
                        main_executor.submit(
                            audio.play,
                            renpy.store.sfx_head_heartbeat,
                            "heartbeat",
                            fadein=2
                        )

                    if self._panic >= self._max_panic:
                        if not self._rollback:
                            self._rollback = True
                            main_executor.submit(
                                audio.play,
                                resources.sounds.sfx["panic_breathing_1"],
                                "breathing",
                                fadein=2
                            )

                    if self._rollback:
                        door.button.force_unclick()

                elif self._panic > 0:
                    panic_changed = True
                    self._panic -= panic_step

                    if self._is_play_heartbeat and self._panic < self._max_panic / 2:
                        self._is_play_heartbeat = False
                        main_executor.submit(
                            audio.stop,
                            "heartbeat",
                            fadeout=2
                        )

                    if self._rollback and self._panic <= self._rollback_threshold:
                        self._rollback = False
                        main_executor.submit(
                            audio.stop,
                            "breathing",
                            fadeout=2
                        )

                self._panic = min(max(self._panic, 0), self._max_panic)

                if self._rollback and door is not None and not door.is_open:
                    door.button.force_unclick()

                if self._open_tablet:
                    tablet = self._current_location.tablet

                    if tablet.out_battery:
                        if screen_manager.has_screen("tablet"):
                            main_executor.submit(screen_manager.hide_screen, "tablet", player=self)
                        self.close_tablet()

                if panic_changed:
                    update_ui()

        def reset(self):
            super(Player, self).reset()
            self._under_attack.clear()
            for element in iter_values(self._element_enabled):
                element.clear()

    class PlayerSystem(object):
        def __init__(self):
            self._players = dict()
            self._current_player = None

        @property
        def player_ids(self):
            return list(self._players.keys())

        @property
        def current_player(self):
            return self._current_player

        def create_player(self, id, max_panic=15, register_in_cycle=True):
            id = to_text(id)
            if id in self._players:
                raise FNaSRException("A character with ID '{}' has already been created.".format(id))
            
            player = Player(id, max_panic)

            if register_in_cycle:
                require_system("cycle").register(player)

            self._players[id] = player
            if self._current_player is None:
                self._current_player = player

            return player

        def delete_player(self, id):
            id = to_text(id)
            if id not in self._players:
                raise FNaSRException("The character with ID '{}' does not exist".format(id))

            player = self._players[id]

            if self._current_player is player:
                raise FNaSRException("Cannot remove the current player({}).".format(id))

            cycle = require_system("cycle")
            if cycle.is_registered(player):
                cycle.unregister(player)

            self._players.pop(id)

            if self._current_player is player:
                if self._players:
                    self.switch_player(next(iter(self._players)))
                else:
                    self._current_player = None
                    ambience_manager.stop_all()

        def switch_player(self, id):
            if is_initialized():
                raise FNaSRException("You cannot change the player after the mod has been initialized.")
            id = to_text(id)
            if id not in self._players:
                raise FNaSRException("The character with ID '{}' does not exist".format(id))

            self._current_player = self._players[id]
            ambience_manager.sync_player(self._current_player)

        def get_player(self, id):
            return self._players.get(to_text(id))

        def __iter__(self):
            return iter(list(self._players.values()))

    register_system("player", PlayerSystem())

init python in v1FNaSR:
    def _switch_player_god_mode(context):
        player = context.ps.current_player
        player.god_mode = not player.god_mode

    _dsp1 = DebugSection(
        DebugText(lambda context: "Player: {}".format(context.ps.current_player.id), style="v1_text_16_style_FNaSR"),
        DebugText(lambda context: "is moving: {}".format(context.ps.current_player.is_moving)),
        DebugText(lambda context: "under attack: {}".format(context.ps.current_player.under_attack)),
        DebugButton(
            lambda context: "god mode: {}".format(context.ps.current_player.god_mode),
            _switch_player_god_mode
        ),
        order=0
    )

    _dsp2 = DebugSection(
        DebugText(lambda context: "Паника: {}".format(context.ps.current_player.get_panic_text()), style="v1_text_16_style_FNaSR"),
        DebugText(lambda context: "rollback panic: {}".format(context.ps.current_player.is_rollback_panic)),
        DebugText(lambda context: "rollback threshold: {}".format(context.ps.current_player.rollback_threshold)),
        DebugText(lambda context: "magnitude change panic: {}".format(context.ps.current_player._magnitude_change_panic)),
        DebugText(lambda context: "Дверь: {}".format("{color=#0ac80a}открыта{/color}" if context.ps.current_player.current_location.door.is_open else "{color=#c80a0a}закрыта{/color}"), condition=lambda context: context.ps.current_player.has_door),
    order=1)

    _ps = require_system("player")
    _dsp1.context.ps = _ps
    _dsp2.context.ps = _ps

    debug.add_element(_dsp1, group="Player")
    debug.add_element(_dsp2, group="Player")

    del _ps
    del _dsp1
    del _dsp2
    del _switch_player_god_mode


