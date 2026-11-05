# -*- coding: utf-8 -*-
# core/location/bulb.rpy
init -1 python in v1FNaSR:
    class Bulb(native_object):
        __slots__ = "_is_on", "_dark_image"

        def __init__(self, dark_image):
            self._is_on = True
            self._dark_image = renpy.displayable(dark_image)

        @property
        def is_on(self):
            return self._is_on

        @is_on.setter
        def is_on(self, value):
            play_sound = True
            if isinstance(value, (list, tuple)):
                if not 1 <= len(value) <= 2:
                    raise FNaSRValueError("'is_on' должен содержать 1 или 2 элемента, получено: {}".format(len(value)))
                status = bool(value[0])
                if len(value) == 2:
                    play_sound = bool(value[1])
            else:
                status = bool(value)
            if status:
                self.switch_on(play_sound)
            else:
                self.switch_off(play_sound)

        @property
        def dark_image(self):
            return self._dark_image

        def switch_on(self, play_sound=True):
            if self._is_on:
                return
            self._is_on = True
            if play_sound:
                main_executor.submit(audio.play, resources.sounds.sfx["switch_on"], "sound")

        def switch_off(self, play_sound=True):
            if not self._is_on:
                return
            self._is_on = False
            if play_sound:
                main_executor.submit(audio.play, resources.sounds.sfx["switch_off"], "sound")

        def switch(self, play_sound=True):
            if self._is_on:
                self.switch_off(play_sound)
            else:
                self.switch_on(play_sound)

        def reset(self):
            self._is_on = True

 

