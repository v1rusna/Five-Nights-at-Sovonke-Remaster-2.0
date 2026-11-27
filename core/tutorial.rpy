# -*- coding: utf-8 -*-
# core/tutorial.rpy
init python in v1FNaSR:
    def _noop_update(dt):
        pass

    class TutorialObject(GameObject):
        __slots__ = (
            "_pm", "_em", "_ts", "_ls"
            "_stage", "_current_time", "_target_time",
            "_flags",
        )

        is_tutorial = False

        _instance = None

        def __new__(cls):
            if cls._instance is None:
                cls._instance = native_object.__new__(cls)
            return cls._instance

        def __init__(self):
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
            }

        def start(self):
            loaded = require_system("night").loaded
            if loaded.id != "tutorial":
                self.update = _noop_update
                return

            self.is_tutorial = True
            self.update = self._tutorial_update
            self._pm = require_system("player")
            self._em = require_system("enemy")
            self._ts = require_system("time")
            self._ls = require_system("location")

            for enemy in self._em.iter_current_group:
                enemy.enabled = False
                enemy.is_invisible = False

            self._ts.hour_time = 1800

        def _tutorial_update(self, dt):
            self._stage_table[self._stage](dt)

        def reset(self):
            super(TutorialObject, self).reset()
            self.update = _noop_update
            self.is_tutorial = False

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
            if self._timer(dt):
                self._next_stage()
                main_executor.submit(visual.hide, "black")
                return

            player = self._pm.current_player
            player.move(self._ls.require_location(12))
            main_executor.submit(audio.play, resources.sounds.sfx["walking"], "walk", fadeout=0.5, loop=False)
            main_executor.submit(visual.show, "black", at_list=[renpy.store.v1_tutorial_hide_black])
            self._target_time = 1.0

    require_system("cycle").register(TutorialObject())


transform v1_tutorial_hide_black:
    alpha 1.0
    pause 0.5
    linear 0.5 alpha 0.0
