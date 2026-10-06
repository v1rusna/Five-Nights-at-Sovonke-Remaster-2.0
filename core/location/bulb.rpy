# bulb.rpy
init -1 python in v1FNaSR:
    class Bulb(ResetLogic):
        def __init__(self, dark_image):
            self._is_on = True
            self._dark_image = renpy.displayable(dark_image)

        @property
        def is_on(self):
            return self._is_on

        @property
        def dark_image(self):
            return self._dark_image

        def switch_on(self, play_sound=True):
            if self._is_on:
                return
            self._is_on = True
            if play_sound:
                play(resources.sounds.sfx["switch_on"], "sound")

        def switch_off(self, play_sound=True):
            if not self._is_on:
                return
            self._is_on = False
            if play_sound:
                play(resources.sounds.sfx["switch_off"], "sound")

        def switch(self, play_sound=True):
            if self._is_on:
                self.switch_off(play_sound)
            else:
                self.switch_on(play_sound)

        def reset(self):
            self._is_on = True

 

