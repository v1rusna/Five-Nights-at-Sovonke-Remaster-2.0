init -1 python in v1FNaSR:
    MOVE_DIRECTION_DISTANCE_BASE = 480
    MOVE_SHOW_DURATION = 0.35
    MOVE_HIDE_DURATION = 0.28

init python:
    @v1FNaSR.main_thread_only
    def _v1_tablet_screen_callback(screen_names, state, **kwargs):
        if state not in ("show", "hide",):
            return

        fast_switch = kwargs.get("fast_switch", False)
        play_sound = kwargs.get("play_sound", True)

        if fast_switch:
            if state == "show":
                renpy.show_screen(screen_names[1], **kwargs)
            else:
                renpy.hide_screen(screen_names[1], **kwargs)
            return

        kwargs.pop("fast_switch", None)
        kwargs["player"] = kwargs.get("player", v1FNaSR.require_system("player").current_player)
        kwargs["tablet_screen"] = kwargs.get("tablet_screen", screen_names[1])

        if play_sound:
            if state == "show":
                if renpy.random.random() > 0.8:
                    v1FNaSR.play(v1FNaSR.resources.sounds.sfx["tablet_open_1"], "sound")
                else:
                    v1FNaSR.play(v1FNaSR.resources.sounds.sfx["tablet_open_2"], "sound")
            else:
                v1FNaSR.play(v1FNaSR.resources.sounds.sfx["tablet_close_1"], "sound")

        renpy.show_screen(screen_names[0], state=state, **kwargs)

    @v1FNaSR.main_thread_only
    def _v1_move_screen_callback(screen_names, state, **kwargs):
        player = kwargs.pop("player", None)
        move_to = kwargs.pop("move_to", None)
        speed = kwargs.pop("speed", 1.0)
        hide_force = kwargs.pop("hide_force", False)

        if state == "show":
            renpy.show_screen(screen_names[0], **kwargs)
            return

        if state == "hide":
            renpy.hide_screen(screen_names[0], **kwargs)
            if player is not None and move_to is not None:
                v1FNaSR.GlobalState.set("animation", True)
                v1FNaSR.play(v1FNaSR.resources.sounds.sfx["walking"], "walk", fadeout=0.5, loop=False)
                renpy.show_screen(screen_names[1], player=player, move_to=move_to, speed=speed, **kwargs)

    v1FNaSR.register_screen("tablet", ["_v1_show_camera_map_screen_FNaSR", "V1CameraMapScreenFNaSR"], callback=_v1_tablet_screen_callback)
    v1FNaSR.register_screen("game_interface", ["V1BaseUIScreenFNaSR", "V1MainGameInterfaceFNaSR"])
    v1FNaSR.register_screen("move", ["V1MoveScreenFNaSR", "V1MovingAnotherLocationFNaSR"], callback=_v1_move_screen_callback)

    del _v1_tablet_screen_callback
    del _v1_move_screen_callback
