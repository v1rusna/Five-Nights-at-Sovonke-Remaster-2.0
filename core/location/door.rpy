# door.rpy
init python in v1FNaSR:
    audio.register_channel("door_sound", "sound", loop=False)

    class DoorClose(FNaSRException):
        def __init__(self, location_id):
            super(DoorClose, self).__init__(location_id)
            self.location_id = location_id

    class Door(object):
        __slots__ = ("_open", "_door_button",)

        def __init__(self):
            vp = ViewportManager.current()
            self._open = True
            self._door_button = HoldingMouseImageButton(
                idle=renpy.store.Solid("#00000000", xsize=int(vp.scale_scalar(290)), ysize=int(vp.scale_scalar(200))),
                clicked=renpy.store.Solid("#00000000", xsize=int(vp.scale_scalar(290)), ysize=int(vp.scale_scalar(200))),
                click_action=renpy.store.Function(self.close),
                unclick_action=renpy.store.Function(self.open),
                allow_alternate=False
            )

        @property
        def is_open(self):
            return self._open

        @property
        def button(self):
            return self._door_button

        def open(self, play_sound=True, show_vignette=True):
            if self._open:
                return
            self._open = True
            if play_sound:
                main_executor.submit(
                    audio.play,
                    renpy.store.sfx_door_squeak_light,
                    "door_sound"
                )
            if show_vignette:
                main_executor.submit(self._show_vignette, [renpy.store.v1_door_hold_vignette_disappear_FNaSR])

        def close(self, play_sound=True, show_vignette=True):
            if not self._open:
                return
            self._open = False
            if play_sound:
                main_executor.submit(
                    audio.play,
                    resources.sounds.sfx["door_unhold"],
                    "door_sound"
                )
            if show_vignette:
                main_executor.submit(self._show_vignette, [renpy.store.v1_door_hold_vignette_appear_FNaSR])

        @main_thread_only
        def _show_vignette(self, at_list):
            try:
                renpy.show(name="v1_door_hold_vignette_FNaSR", at_list=tuple(at_list), what=InitImages.door_hold_vignette, layer="screens")
            except:
                pass

        def reset(self):
            self._door_button.force_unclick()
            self._open = True

        def __repr__(self):
            return "<store.v1FNaSR.{} is_open={} hex={}>".format(type(self).__name__, self._open, hex(id(self)))

