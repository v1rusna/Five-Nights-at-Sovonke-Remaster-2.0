# -*- coding: utf-8 -*-
# game.rpy
screen V1BaseUIScreenFNaSR:
    key "K_a" action NullAction()
    key ["K_ESCAPE", "mouseup_3"] action ShowMenu("V1GameMenuSelectorFNaSR")

screen V1InfoNightScreenFNaSR(player=None, night_system=None):
    default ns = night_system if night_system is not None else v1FNaSR.require_system("night")
    if player is None:
        $ player = v1FNaSR.require_system("player").current_player
    if not player.is_open_tablet and ns.loaded is not None:
        text ns.loaded.title style "v1_text_24_style_FNaSR" xalign 1.0

screen V1MainGameInterfaceFNaSR:
    default viewport = v1FNaSR.ViewportManager.current()
    default xsize_button = int(viewport.scale_scalar(290))
    default ysize_button = int(viewport.scale_scalar(200))

    default ns = v1FNaSR.require_system("night")

    $ player = v1FNaSR.require_system("player").current_player

    add player.get_sees_image()
    use V1InfoNightScreenFNaSR(player, ns)

    if not player.is_open_tablet and not player.is_moving and not player.under_attack:
        add v1FNaSR.DistanceButton(
            TextButton(
                "Переместиться",
                style="v1_move_location_button_FNaSR",
                text_style="v1_text_24_mod_button_FNaSR",
                clicked=(Function(player.set_moving, True), Function(v1FNaSR.show_screen, "move"))
            ),
            radius=200.0,
            opaque_radius=20.0,
            falloff=1.0
        ) align (0.5, -0.2)

    if not player.is_moving and player.has_door and not player.is_open_tablet:
        text player.get_panic_text() style "v1_text_24_style_FNaSR" align (0.9, 0.8)
        add (v1FNaSR.InitImages.ui_door_open if player.current_location.door.is_open else v1FNaSR.InitImages.ui_door_close) align (0.75, 0.9)
        if not player.is_rollback_panic:
            add player.current_location.door.button align (0.75, 1.0)

    if not player.is_moving and player.has_bulb and not player.is_open_tablet:
        button:
            align (0.25, 1.0)
            background None
            xsize xsize_button
            ysize ysize_button
            action Function(player.current_location.bulb.switch)
        imagebutton:
            align (0.25, 0.9)
            idle (v1FNaSR.InitImages.ui_bulb_on if player.current_location.bulb.is_on else v1FNaSR.InitImages.ui_bulb_off)

    if player.has_tablet and not player.is_moving:
        use V1TabletButtonScreenFNaSR(player)

screen V1TabletButtonScreenFNaSR(player):
    default viewport = v1FNaSR.ViewportManager.current()
    default xsize_tablet_button = int(viewport.scale_scalar(600))
    default ysize_tablet_button = int(viewport.scale_scalar(200))

    if player.current_location.tablet.out_battery:
        $ tablet_button_action = Function(v1FNaSR.play, v1FNaSR.resources.sounds.sfx["error"], "sound")
    else:
        $ tablet_button_action = Function(v1FNaSR.Tools.switch_tablet, player)

    key "K_SPACE" action tablet_button_action
    button:
        align(0.5, 1.0)
        background None
        xsize xsize_tablet_button
        ysize ysize_tablet_button
        action tablet_button_action
    imagebutton:
        align (0.5, 0.9)
        idle v1FNaSR.InitImages.tablet_button

screen _v1_show_camera_map_screen_FNaSR(tablet_screen, state, player):
    if state == "show":
        timer 0.18 action [Hide("_v1_show_camera_map_screen_FNaSR"), Function(player.open_tablet), Show(tablet_screen)]
        add "anim v1_tablet_open_entire_FNaSR"
    else:
        on "show" action [Hide(tablet_screen), Function(player.close_tablet)]
        timer 0.18 action [Hide("_v1_show_camera_map_screen_FNaSR")]
        add "anim v1_tablet_close_entire_FNaSR"

screen V1CameraMapScreenFNaSR:
    python:
        player = v1FNaSR.require_system("player").current_player
        tablet = player.current_location.tablet
        location_system = player.current_location.location_system
        num_cam = location_system.get_location(tablet.selected).camera.num
        if len(num_cam) == 1:
            text_cam_num =  "CAM 0{}".format(num_cam)
        else:
            text_cam_num =  "CAM {}".format(num_cam)

    default viewport = v1FNaSR.ViewportManager.current()
    default game_time = v1FNaSR.require_system("time")

    default xsize_fixed_camera_map = int(viewport.scale_scalar(1500))
    default ysize_fixed_camera_map = int(viewport.scale_scalar(844))

    add v1FNaSR.InitImages.door_hold_vignette

    add "v1_C_static_entire_FNaSR" at v1_dynamic_camera_static_t_FNaSR()

    add v1FNaSR.InitImages.camera_frame

    text "{i}"+str(tablet.charge_percentage)+"%{/i}" style "v1_text_24_style_FNaSR" align (0.024, 0.034)
    text game_time.get_time() style "v1_text_24_style_FNaSR" align (0.98, 0.034)
    text text_cam_num style "v1_text_24_style_FNaSR" align (0.024, 0.97)

    fixed:
        xsize xsize_fixed_camera_map
        ysize ysize_fixed_camera_map
        align(1.6, 1.8)

        add v1FNaSR.InitImages.camera_map.bg

        for location_id in tablet.registered_locations:
            $ location = location_system.get_location(location_id)
            if location is not None and location.camera is not None:
                add location.ui_camera_button

screen V1MoveDirectionFNaSR(config, locations, player):
    python:
        _dx = (config.xanchor - 0.5) * 2.0
        _dy = (config.yanchor - 0.5) * 2.0
        _distance = v1FNaSR.Tools.get_move_animation_distance()

    frame:
        style "v1_move_direction_frame_FNaSR"
        background None
        xpos config.xpos
        ypos config.ypos
        xanchor config.xanchor
        yanchor config.yanchor
        at v1_move_direction_t_FNaSR(
            _dx, _dy, _distance,
            v1FNaSR.MOVE_SHOW_DURATION,
            v1FNaSR.MOVE_HIDE_DURATION
        )

        vbox:
            spacing 14
            xalign 0.5

            hbox:
                text config.arrow xalign 0.5
                text " " xalign 0.5
                text config.label style "v1_move_direction_label_FNaSR" xalign 0.5

            viewport:
                style "v1_move_direction_viewport_FNaSR"
                mousewheel True
                draggable True

                if len(locations) > 3:
                    scrollbars "vertical"
                else:
                    scrollbars None

                vbox:
                    spacing 10
                    xalign 0.5

                    for location in locations:
                        textbutton location.name:
                            style "v1_move_location_button_FNaSR"
                            text_style "v1_text_24_mod_button_FNaSR"
                            if not v1FNaSR.GlobalState.get("animation", False):
                                action Function(
                                    v1FNaSR.hide_screen,
                                    "move",
                                    player=player,
                                    move_to=location,
                                    speed=1.5
                                )

screen V1MoveScreenFNaSR:
    zorder 10

    python:
        player = v1FNaSR.require_system("player").current_player
        location_system = player.current_location.location_system
        active_directions = v1FNaSR.Tools.get_active_directions(
            player,
            location_system
        )

    add v1FNaSR.DistanceButton(
        TextButton(
            "Остановится",
            style="v1_move_location_button_FNaSR",
            text_style="v1_text_24_mod_button_FNaSR",
            clicked=(
                Function(player.set_moving, False),
                Function(v1FNaSR.hide_screen, "move")
            )
        ),
        radius=200.0,
        opaque_radius=20.0,
        falloff=1.0
    ) align (0.5, 0.5)

    for config, locations in active_directions:
        use V1MoveDirectionFNaSR(config, locations, player)

screen V1MovingAnotherLocationFNaSR(player, move_to, speed=1.0):
    timer 3.6 / speed action (Hide("V1MovingAnotherLocationFNaSR"), Function(v1FNaSR.GlobalState.set, "animation", False))
    timer 3.3 / speed action (Function(v1FNaSR.show_screen, "move"), Function(v1FNaSR.stop, "walk", fadeout=1.0))
    timer 1.8 / speed action Function(player.move, move_to)
    add player.get_sees_image() at v1_go_t_FNaSR(speed)
    add move_to.parallax_image at v1_moving_location2_FNaSR(speed)
    add "black" at v1_moving_black_FNaSR(speed)
    use V1InfoNightScreenFNaSR()




