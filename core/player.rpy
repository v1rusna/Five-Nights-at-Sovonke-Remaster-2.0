init -1 python in v1FNaSR:
    register_channel("heartbeat", "ambience", loop=True)
    register_channel("breathing", "ambience", loop=True)

    class Player(GameObject, BaseAI):
        def __init__(self, id, max_panic=15, magnitude_change_panic=1):
            super(Player, self).__init__()

            max_panic = int(max_panic)
            magnitude_change_panic = int(magnitude_change_panic)
            if max_panic <= 0:
                raise FNaSRValueError("'max_panic' cannot be less than or equal to zero")

            self._id = to_text(id)

            self._setattr("_current_location", None)
            self._setattr("_open_tablet", None)
            self._setattr("_is_moving", False)
            self._setattr("_under_attack", False)

            self._setattr("_panic", 0)
            self._setattr("_max_panic", max_panic)
            self._setattr("_magnitude_change_panic", magnitude_change_panic)
            self._setattr("_rollback", False)
            self._setattr("_rollback_threshold", round(self._max_panic * 2 / 3))
            self._setattr("_is_play_heartbeat", False)

        @property
        def id(self):
            return self._id

        @property
        def is_open_tablet(self):
            return self._open_tablet is not None

        @property
        def has_tablet(self):
            if self._current_location is None:
                raise FNaSRAttributeError("The player is not in any location")
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
            return self._current_location.door is not None

        @property
        def is_rollback_panic(self):
            return self._rollback

        @property
        def rollback_threshold(self):
            return self._rollback_threshold

        @property
        def has_bulb(self):
            return self._current_location.bulb is not None

        def get_panic_text(self):
            return "panic: {}/{}".format(self._panic, self._max_panic)

        def set_moving(self, value):
            self._is_moving = bool(value)

        def set_under_attack(self, value):
            self._under_attack = bool(value)

        def get_sees_image(self):
            if self._current_location is None:
                raise FNaSRAttributeError("The player is not in any location")

            if self._open_tablet is None:
                return self._current_location.parallax_image

            selected = self._open_tablet.selected

            if selected is None:
                raise FNaSRException("No location has been selected on the tablet")

            loc = self._current_location.location_system.require_location(selected)

            return loc.image

        def move(self, location, allow_migrate=False):
            if self.is_open_tablet:
                raise FNaSRException("You cannot move to other locations while the tablet is open")

            super(Player, self).move(location, allow_migrate)

        def open_tablet(self):
            if self._current_location is None:
                raise FNaSRAttributeError("The player is not in any location")
            if not self.has_tablet:
                raise FNaSRException("There is no tablet in the current location({})".format(self._current_location.id))
            self._open_tablet = self._current_location.tablet
            self._open_tablet.safe_discharge(2)

        def close_tablet(self):
            self._open_tablet = None

        def switch_tablet(self):
            if self.is_open_tablet:
                self.close_tablet()
            else:
                self.open_tablet()

        def update(self):
            location = self._current_location

            if location is None:
                return

            door = location.door
            panic_step = self._magnitude_change_panic
            panic_changed = False

            if door is not None and not door.is_open:
                panic_changed = True
                self._panic += panic_step

                if not self._is_play_heartbeat and self._panic >= self._max_panic / 2:
                    self._is_play_heartbeat = True
                    play(renpy.store.sfx_head_heartbeat, "heartbeat", fadein=2)

                if self._panic >= self._max_panic:
                    door.button.force_unclick()
                    self._rollback = True
                    play(resources.sounds.sfx["panic_breathing_1"], "breathing", fadein=2)

            elif self._panic > 0:
                panic_changed = True
                self._panic -= panic_step

                if self._is_play_heartbeat and self._panic < self._max_panic / 2:
                    self._is_play_heartbeat = False
                    stop("heartbeat", fadeout=2)

                if self._rollback and self._panic <= self._rollback_threshold:
                    self._rollback = False
                    stop("breathing", fadeout=2)

            self._panic = min(max(self._panic, 0), self._max_panic)

            if self._rollback and door is not None and not door.is_open:
                door.button.force_unclick()

            tablet = self._open_tablet

            if tablet is not None and tablet.out_battery:
                if has_screen("tablet"):
                    main_executor.submit(hide_screen, "tablet", player=self)
                else:
                    self.close_tablet()

            if panic_changed:
                update_ui()

        def reset(self):
            super(Player, self).reset()
            if self._reset_to_default["_current_location"] is not None:
                location_system = get_system("location")
                if location_system is not None:
                    location = location_system.get_location(self._reset_to_default["_current_location"])
                    if location is not None:
                        self.move(location)

    class PlayerSystem(object):
        def __init__(self):
            self._players = dict()
            self._current_player = None
            self._player_id_error = None

        @property
        def player_ids(self):
            return list(self._players.keys())

        @property
        def current_player(self):
            return self._current_player

        def create_player(self, id, max_panic=15, start_location=None, register_in_cycle=True):
            id = to_text(id)
            if id in self._players:
                raise FNaSRException("A character with ID '{}' has already been created.".format(id))
            
            player = Player(id, max_panic)
            if start_location is not None:
                player._setattr("_current_location", start_location.id)
                player.move(start_location)

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

            player = self._players.pop(id)

            if self._current_player is player:
                if self._players:
                    self._current_player = next(iter(self._players.values()))
                else:
                    self._current_player = None

        def switch_player(self, id):
            id = to_text(id)
            if id not in self._players:
                raise FNaSRException("The character with ID '{}' does not exist".format(id))

            self._current_player = self._players[id]

        def get_player(self, id):
            return self._players.get(to_text(id))

    register_system("player", PlayerSystem())

init python in v1FNaSR:
    _dsp1 = DebugSection(
        DebugText(lambda context: "Player: {}".format(context.ps.current_player.id), order=0, style="v1_text_16_style_FNaSR"),
        DebugText(lambda context: "is moving: {}".format(context.ps.current_player.is_moving), order=1),
        DebugText(lambda context: "under attack: {}".format(context.ps.current_player.under_attack), order=2),
    order=0)

    _dsp2 = DebugSection(
        DebugText(lambda context: "Паника: {}/{}".format(context.ps.current_player.panic, context.ps.current_player.max_panic), order=0, style="v1_text_16_style_FNaSR"),
        DebugText(lambda context: "rollback panic: {}".format(context.ps.current_player.is_rollback_panic), order=1),
        DebugText(lambda context: "rollback threshold: {}".format(context.ps.current_player.rollback_threshold), order=2),
        DebugText(lambda context: "magnitude change panic: {}".format(context.ps.current_player._magnitude_change_panic), order=3),
        DebugText(lambda context: "дверь: {}".format("{color=#0ac80a}открыта{/color}" if context.ps.current_player.current_location.door.is_open else "{color=#c80a0a}закрыта{/color}"), order=4, condition=lambda context: context.ps.current_player.has_door),
    order=1)

    _ps = require_system("player")
    _dsp1.context.ps = _ps
    _dsp2.context.ps = _ps

    debug.add_element(_dsp1, group="Player")
    debug.add_element(_dsp2, group="Player")

    del _ps
    del _dsp1
    del _dsp2


