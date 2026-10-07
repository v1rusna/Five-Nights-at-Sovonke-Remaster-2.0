init:
    python:
        import math as v1_math_FNaSR
        def v1_ease_FNaSR(t):
            return 0.5 - v1_math_FNaSR.cos(v1_math_FNaSR.pi * t) / 2.0

        def v1_door_hold_vignette_appear_t_func_FNaSR(t_obj, st, at):
            DOOR_HOLDING_VIGNETTE_APPEAR = 0.8
            door_hold_vignette_current_alpha = 0.0

            normalized_t = st / DOOR_HOLDING_VIGNETTE_APPEAR
            warped_t = v1_ease_FNaSR(normalized_t)

            door_hold_vignette_current_alpha += warped_t

            if door_hold_vignette_current_alpha < 1.0:
                t_obj.alpha = door_hold_vignette_current_alpha
                return 0.0

            t_obj.alpha = 1.0
            return None

        def v1_door_hold_vignette_disappear_t_func_FNaSR(t_obj, st, at):
            DOOR_HOLDING_VIGNETTE_DISAPPEAR = 0.8
            
            if st >= DOOR_HOLDING_VIGNETTE_DISAPPEAR:
                t_obj.alpha = 0.0
                return None  # Завершаем трансформацию
            
            normalized_t = st / DOOR_HOLDING_VIGNETTE_DISAPPEAR
            warped_t = v1_ease_FNaSR(normalized_t)
            t_obj.alpha = 1.0 - warped_t  # Уменьшаем от 1.0 до 0.0
            
            return 0.0  # Продолжаем обновление

transform v1_set_align_center_FNaSR(x, y):
    xalign x yalign y

transform v1_dynamic_camera_static_t_FNaSR():
    alpha 0.05
    choice:
        linear 0.04 alpha 0.2
        linear 0.02 alpha 0.05
    choice:
        linear 0.01 alpha 0.25
        linear 0.04 alpha 0.05
    choice:
        alpha 0.15
        pause 0.01
        alpha 0.05
    choice:
        alpha 0.35
        pause 0.04
        alpha 0.05
    pause 1.5
    repeat

transform v1_camera_static_t_FNaSR():
    alpha 1.0
    ease 0.5 alpha 0.05
    v1_dynamic_camera_static_t_FNaSR()

transform v1_cam_rotate_t_FNaSR(angle=0):
    rotate angle

transform v1_go_t_FNaSR(speed=1.0):
    xalign 0.5 yalign 0.5
    #zoom 1.1
    subpixel True
    transform_anchor True
    truecenter

    ease 0.2 / speed zoom 1.03
    parallel:
        ease 0.5 / speed xoffset 15 yoffset -30 rotate 0.3 zoom 1.11
        ease 0.5 / speed xoffset 0 yoffset 0 rotate 0 zoom 1.10

    parallel:
        ease 1.5 / speed zoom 1.2

transform v1_stop_t_FNaSR(speed=1.0):
    xalign 0.5 yalign 0.5
    zoom 1.1
    subpixel True
    transform_anchor True
    truecenter
    parallel:
        ease 0.5 / speed xoffset 15 yoffset -30 rotate 0.3 zoom 1.11
        ease 0.5 / speed xoffset 0 yoffset 0 rotate 0 zoom 1.10
        ease 0.5 / speed zoom 1.0
    parallel:
        ease 1.0 / speed zoom 1.2
        ease 0.5 / speed zoom 1.00


transform v1_moving_location2_FNaSR(speed=1.0):
    alpha 0.0
    pause 2.2 / speed
    alpha 1.0
    v1_stop_t_FNaSR(speed)


transform v1_moving_black_FNaSR(speed=1.0):
    alpha 0.0
    pause 0.8 / speed
    linear 0.5 / speed alpha 1.0
    pause 1.0 / speed
    linear 0.5 / speed alpha 0.0

transform v1_move_direction_t_FNaSR(dx, dy, distance, show_duration, hide_duration):
    on show:
        xoffset (dx * distance)
        yoffset (dy * distance)
        alpha 0.0
        easeout show_duration xoffset 0 yoffset 0 alpha 1.0
    on hide:
        easein hide_duration xoffset (dx * distance) yoffset (dy * distance) alpha 0.0

transform v1_door_hold_vignette_appear_FNaSR():
    function v1_door_hold_vignette_appear_t_func_FNaSR

transform v1_door_hold_vignette_disappear_FNaSR():
    function v1_door_hold_vignette_disappear_t_func_FNaSR

transform v1_text_flicker_FNaSR(fdelay=0.7):
    alpha 1.0
    pause fdelay
    alpha 0.0
    pause fdelay
    repeat
