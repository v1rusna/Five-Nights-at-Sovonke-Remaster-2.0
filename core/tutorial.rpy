# -*- coding: utf-8 -*-
# core/tutorial.rpy
init python in v1FNaSR:
    def _noop_update(dt):
        pass

    class TutorialObject(GameObject):
        __slots__ = (
            "_pm", "_em", "_ts", "_ls",
            "_stage", "_current_time", "_target_time",
            "_flags",
            "_initialized",
        )

        is_tutorial = False

        _instance = None
        _initialized = False

        def __new__(cls):
            if cls._instance is None:
                cls._instance = native_object.__new__(cls)
                cls._initialized = False
            return cls._instance

        def __init__(self):
            if TutorialObject._initialized:
                return

            super(TutorialObject, self).__init__()
            self._setattr("_stage", 1)
            self._setattr("_current_time", 0.0)
            self._setattr("_target_time", None)
            self._setattr("_pm", None)
            self._setattr("_em", None)
            self._setattr("_ts", None)
            self._setattr("_flags", dict())

            self._stage_table = {
                1: self._stage_1,
                2: lambda dt: None
            }

            TutorialObject._initialized = True

        def start(self):
            loaded = require_system("night").loaded
            if loaded.id != "tutorial":
                self.update = _noop_update
                return

            TutorialObject.is_tutorial = True
            self.update = self._tutorial_update
            self._pm = require_system("player")
            self._em = require_system("enemy")
            self._ts = require_system("time")
            self._ls = require_system("location")

            for enemy in self._em.iter_current_group:
                enemy.enabled = False
                enemy.is_invisible = True

            self._ts.hour_time = 1800
            self.update(0.0)

        def _tutorial_update(self, dt):
            self._stage_table[self._stage](dt)

        def reset(self):
            super(TutorialObject, self).reset()
            self.update = _noop_update
            TutorialObject.is_tutorial = False

        def _timer(self, dt):
            if self._target_time is None:
                return False

            self._current_time += dt
            result = self._current_time >= self._target_time
            if result:
                self._target_time = None
                self._current_time = 0.0
            return result

        def _next_stage(self):
            self._target_time = None
            self._current_time = 0.0
            self._flags.clear()
            self._stage += 1

        def _stage_1(self, dt):
            if self._ts.clock.hour >= 2:
                self._ts.is_game_time_enabled = False

            stage = self._flags.get("stage",0)

            if stage == 0:
                player = self._pm.current_player
                player.move(self._ls.require_location(12))
                player.get_element(PlayerElement.MOVING).block(self)
                main_executor.submit(audio.play, resources.sounds.sfx["walking"], "walk", fadeout=0.5, loop=False)
                self._target_time = 2.5
                self._flags["stage"] = 1
                update_ui()
            elif stage == 1:
                self._current_time += dt
                if self._current_time >= self._target_time:
                    tutorial_text_blocks[1].start()
                    self._current_time = 0.0
                    self._target_time = 18.0
                    self._flags["stage"] = 2
            elif stage == 2:
                self._current_time += dt
                if self._current_time >= self._target_time:
                    self._pm.current_player.get_element(PlayerElement.MOVING).unblock(self)
                    self._next_stage()

    require_system("cycle").register(TutorialObject())


transform v1_tutorial_hide_black:
    alpha 1.0
    pause 0.5
    linear 0.5 alpha 0.0
