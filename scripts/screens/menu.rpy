

screen V1MainMenuScreenFNaSR:
    pass

screen V1GameMenuSelectorFNaSR:
    zorder 999
    modal True

    default tt = v1FNaSR.TextTools
    default settings = False

    default bar_null = Frame(v1FNaSR.resources.images.other["bar_null"],36,36)
    default bar_full = Frame(v1FNaSR.resources.images.other["bar_full"],36,36)

    key ["K_ESCAPE", "mouseup_3"] action Return()

    add "black" alpha 0.5

    add tt.text("Пять Ночей в Совёнке Remaster", size=24, g_power=0.0575) align(0.5, 0.1)

    vbox align(0.5, 0.5) spacing 15:
        if not settings:
            textbutton tt.text("Продолжить") background None xalign 0.5 hover_sound v1FNaSR.resources.sounds.ui["button_h"] activate_sound v1FNaSR.resources.sounds.ui["button_c"] action Return()
                
            textbutton tt.text("Настройки"):
                background None xalign 0.5
                hover_sound v1FNaSR.resources.sounds.ui["button_h"]
                activate_sound v1FNaSR.resources.sounds.ui["button_c"]
                action SetScreenVariable("settings", True)

            textbutton tt.text("Выйти"):
                background None xalign 0.5
                hover_sound v1FNaSR.resources.sounds.ui["button_h"]
                activate_sound v1FNaSR.resources.sounds.ui["button_c"]
                action [Return(), Function(renpy.jump, "v1_quit_FNaSR")]
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

init python:
    v1FNaSR.register_screen("main menu", "V1MainMenuScreenFNaSR")
