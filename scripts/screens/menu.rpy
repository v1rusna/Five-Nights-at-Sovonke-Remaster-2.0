

screen V1GameMenuSelectorFNaSR:
    zorder 999
    modal True

    default tt = v1FNaSR.TextTools
    default settings = False
    default is_running = v1FNaSR.require_system("night").is_running
    default loaded = v1FNaSR.require_system("night").loaded
    default confirmation_action = None

    default bar_null = Frame(v1FNaSR.resources.images.other["bar_null"],36,36)
    default bar_full = Frame(v1FNaSR.resources.images.other["bar_full"],36,36)

    key ["K_ESCAPE", "mouseup_3"] action Return()

    on "show" action Function(lambda: v1FNaSR.require_system("cycle").freeze())
    on "hide" action Function(lambda: v1FNaSR.require_system("cycle").unfreeze())

    add "black" alpha 0.5

    if is_running:
        text loaded.title style "v1_text_24_style_FNaSR" xalign 1.0 at v1_text_flicker_FNaSR()

    add tt.text("Пять Ночей в Совёнке Remaster", size=24, g_power=0.0575) align(0.5, 0.1)

    vbox align(0.5, 0.5) spacing 15:
        if confirmation_action is None:
            if not settings:
                textbutton tt.text("Продолжить") background None xalign 0.5 hover_sound v1FNaSR.resources.sounds.ui["button_h"] activate_sound v1FNaSR.resources.sounds.ui["button_c"] action Return()

                if is_running:
                    textbutton tt.text("Начать ночь заново"):
                        background None xalign 0.5
                        hover_sound v1FNaSR.resources.sounds.ui["button_h"]
                        activate_sound v1FNaSR.resources.sounds.ui["button_c"]
                        action SetScreenVariable("confirmation_action", [Return(), Function(v1FNaSR.Tools.restart_night, loaded)])

                    textbutton tt.text("В меню"):
                        background None xalign 0.5
                        hover_sound v1FNaSR.resources.sounds.ui["button_h"]
                        activate_sound v1FNaSR.resources.sounds.ui["button_c"]
                        action SetScreenVariable("confirmation_action", [Return(), Function(renpy.jump, "v1_quit_FNaSR")]) # TODO: реализовать
                    
                textbutton tt.text("Настройки"):
                    background None xalign 0.5
                    hover_sound v1FNaSR.resources.sounds.ui["button_h"]
                    activate_sound v1FNaSR.resources.sounds.ui["button_c"]
                    action SetScreenVariable("settings", True)

                textbutton tt.text("Выйти"):
                    background None xalign 0.5
                    hover_sound v1FNaSR.resources.sounds.ui["button_h"]
                    activate_sound v1FNaSR.resources.sounds.ui["button_c"]
                    action SetScreenVariable("confirmation_action", [Return(), Function(renpy.jump, "v1_quit_FNaSR")])
            else:
                for volume_type, label in (("music volume", "Музыка"), ("sound volume", "Звуки"), ("voice volume", "Эмбиент")):
                    add tt.text(label) xalign 0.5
                    bar:
                        value Preference(volume_type)
                        left_bar bar_full
                        right_bar bar_null
                        thumb None
                        hover_thumb None
                        xmaximum 0.25
                        ymaximum 36
                        xalign 0.5

                textbutton tt.text("Назад"):
                    background None xalign 0.5
                    hover_sound v1FNaSR.resources.sounds.ui["button_h"]
                    activate_sound v1FNaSR.resources.sounds.ui["button_c"]
                    action SetScreenVariable("settings", False)
        else:
            text tt.text("Вы уверены?") xalign 0.5

            hbox:
                xalign 0.5
                spacing 30

                textbutton tt.text("     <-[[ Да ]->     "):
                    background None xalign 0.5
                    hover_sound v1FNaSR.resources.sounds.ui["button_h"]
                    activate_sound v1FNaSR.resources.sounds.ui["button_c"]
                    action confirmation_action
                textbutton tt.text("     <-[[ Нет ]->     "):
                    background None xalign 0.5
                    hover_sound v1FNaSR.resources.sounds.ui["button_h"]
                    activate_sound v1FNaSR.resources.sounds.ui["button_c"]
                    action SetScreenVariable("confirmation_action", None)

screen V1SayScreenFNaSR:
    text what id "what" xalign 0.5 ypos 964 xmaximum 1541 size 28 line_spacing 2
    if who:
        text who id "who" xalign 0.5 ypos 931 size 28 line_spacing 2

init python:
    v1FNaSR.register_screen("main menu", "V1MainMenuScreenFNaSR")
