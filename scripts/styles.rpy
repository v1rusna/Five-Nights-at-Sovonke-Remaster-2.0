
init python:

    style.v1_text_24_style_FNaSR = renpy.style.Style("text")
    style.v1_text_24_typewriter_style_FNaSR = renpy.style.Style(
        style.v1_text_24_style_FNaSR
    )
    style.v1_text_24_mod_button_FNaSR = renpy.style.Style(
        style.v1_text_24_style_FNaSR
    )
    style.v1_text_24_mod_button_static_FNaSR = renpy.style.Style(
        style.v1_text_24_style_FNaSR
    )
    style.v1_text_12_style_FNaSR = renpy.style.Style(
        style.v1_text_24_style_FNaSR
    )
    style.v1_text_16_style_FNaSR = renpy.style.Style(
        style.v1_text_24_style_FNaSR
    )
    style.v1_text_16_mod_button_FNaSR = renpy.style.Style(
        style.v1_text_16_style_FNaSR
    )

    def v1_init_style_FNaSR():
        font_24_size = v1FNaSR.scale_font_size(24)
        font_16_size = v1FNaSR.scale_font_size(16)
        font_12_size = v1FNaSR.scale_font_size(12)

        style.v1_text_24_style_FNaSR.size = font_24_size
        style.v1_text_24_style_FNaSR.font = v1FNaSR.resources.fonts["retrobanker"]
        style.v1_text_24_style_FNaSR.outlines = [
            (2, "#000000", 2, 2)
        ]

        style.v1_text_24_typewriter_style_FNaSR.font = v1FNaSR.resources.fonts["SpecialElite"]

        style.v1_text_24_mod_button_FNaSR.color = "#d4d4d4"
        style.v1_text_24_mod_button_static_FNaSR.color = "#ffffff"

        style.v1_text_12_style_FNaSR.size = font_12_size
        style.v1_text_16_style_FNaSR.size = font_16_size

    v1FNaSR.add_start_fn(v1_init_style_FNaSR)

init 1:
    style v1_move_direction_frame_FNaSR:
        padding (18, 14)
        xminimum 0
        xmaximum 340

    style v1_move_direction_viewport_FNaSR:
        ymaximum 220
        xfill True

    style v1_move_location_button_FNaSR is button:
        xalign 0.5
        xmaximum 300
        padding (10, 6)
        background None
        hover_background "#ffffff22"
        idle_background None

    style v1_move_direction_label_FNaSR is v1_text_24_style_FNaSR:
        xalign 0.5
