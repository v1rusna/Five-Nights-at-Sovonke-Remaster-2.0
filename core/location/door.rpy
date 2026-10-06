# door.rpy
init python in v1FNaSR:
    class DoorClose(FNaSRException): pass

    class Door(ResetLogic):
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

        def open(self):
            self._open = True

        def close(self):
            self._open = False

        def reset(self):
            self._door_button.force_unclick()
            self._open = True

