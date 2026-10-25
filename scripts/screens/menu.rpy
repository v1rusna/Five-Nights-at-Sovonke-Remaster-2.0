# menu.rpy
screen V1MainMenuFrameFNaSR(time="23:57", show_elements=True):
    default mm = v1FNaSR.MainMenuTools
    default tt = v1FNaSR.TextTools

    add mm.get_bg()

    if mm.is_enemy_show() and show_elements:
        add mm.get_enemy() xalign .9

    add v1FNaSR.InitImages.door_hold_vignette
    add "v1_C_static_entire_FNaSR" at v1_camera_static_t_FNaSR()
    add v1FNaSR.resources.images.other["FNaG_Cam_Frame"]

    add v1FNaSR.InitImages.lightning align (0.022, 0.038)
    text "{i}100%{/i}" style "v1_text_24_style_FNaSR" align (0.038, 0.035)
    text time style "v1_text_24_style_FNaSR" align (0.98, 0.034) at v1_text_flicker_FNaSR()
    text mm.get_cam_num() style "v1_text_24_style_FNaSR" align (0.98, 0.97)

    textbutton tt.text("Пять Ночей в Совёнке Remaster", size=24, g_power=0.0575) background None align(0.5, 0.1) action NullAction()

    textbutton tt.text("v1rus team"):
        background None
        align(0.0185, 0.971)
        hover_sound v1FNaSR.resources.sounds.ui["button_h"]
        activate_sound v1FNaSR.resources.sounds.ui["button_c"]
        action [OpenURL("https://t.me/+VewEitmB66k0MmQy"), SetField(persistent, "v1_click_v1rus_team_tg_FNaSR", True)]
    if not persistent.v1_click_v1rus_team_tg_FNaSR:
        textbutton tt.text("<- clicked") background None align(0.12, 0.971)

screen V1MainMenuFNaSR:
    tag v1menuFNaSR

    default mm = v1FNaSR.MainMenuTools
    default tt = v1FNaSR.TextTools
    default ns = v1FNaSR.require_system("night")
    default target = ns.find_available_night(v1FNaSR.MAIN_SEQUENCE)
    if target is None:
        $ target = ns.find_last_unlocked_night(v1FNaSR.MAIN_SEQUENCE)

    key "mouseup_3" action NullAction()
    key "K_ESCAPE" action NullAction()

    use V1MainMenuFrameFNaSR()

    vbox align(0.15, 0.5) spacing 15:
        add tt.textbutton("Начать({})".format(target.title), (Hide('V1MainMenuFNaSR'), Jump('v1_play_FNaSR')))
        add tt.textbutton("Выбор ночи", Function(mm.screen_switching, "V1MainMenuFNaSR", "V1MainMenuChoiceNightFNaSR"))
        add tt.textbutton("Достижения", Function(mm.screen_switching, "V1MainMenuFNaSR", "V1MainMenuAchievementsFNaSR"))
        add tt.textbutton("Настройки", Function(mm.screen_switching, "V1MainMenuFNaSR", "V1MainMenuSettingsFNaSR"))
        add tt.textbutton("Выйти", (Hide('V1MainMenuFNaSR'), Jump('v1_quit_mm_FNaSR')))

screen V1MainMenuChoiceNightFNaSR(sequence=v1FNaSR.MAIN_SEQUENCE):
    tag v1menuFNaSR

    default mm = v1FNaSR.MainMenuTools
    default tt = v1FNaSR.TextTools
    default ns = v1FNaSR.require_system("night")
    default special_n = ns.get_special_nights()

    use V1MainMenuFrameFNaSR()

    key "mouseup_3" action Function(mm.screen_switching, "V1MainMenuChoiceNightFNaSR", "V1MainMenuFNaSR")
    key "K_ESCAPE" action Function(mm.screen_switching, "V1MainMenuChoiceNightFNaSR", "V1MainMenuFNaSR")

    add tt.text("Выбор ночи", size=22) align(0.5, 0.14)

    vbox align(0.15, 0.5) spacing 15:
        add tt.text("Список ночей", size=28)

        for n in ns.get_nights(sequence):
            button:
                background None
                if ns.is_unlocked(n):
                    hover_sound v1FNaSR.resources.sounds.ui["button_h"]
                    activate_sound v1FNaSR.resources.sounds.ui["button_c"]
                    action (Hide('V1MainMenuChoiceNightFNaSR'), Call('v1_play_FNaSR', n))
                
                fixed:
                    fit_first True
                    
                    text tt.text(n.title)
                    
                    if not ns.is_unlocked(n):
                        add "v1_button_static_entire_FNaSR" at v1_button_static_hover_t_FNaSR()

        if special_n:
            add tt.text("Специальные ночи")
            for n in special_n:
                button:
                    background None
                    if ns.is_unlocked(n):
                        hover_sound v1FNaSR.resources.sounds.ui["button_h"]
                        activate_sound v1FNaSR.resources.sounds.ui["button_c"]
                        action (Hide('V1MainMenuChoiceNightFNaSR'), Call('v1_play_FNaSR', n))
                    
                    fixed:
                        fit_first True
                        
                        text tt.text(n.title)
                        
                        if not ns.is_unlocked(n):
                            add "v1_button_static_entire_FNaSR" at v1_button_static_hover_t_FNaSR()
        
        add tt.textbutton("Назад", Function(mm.screen_switching, "V1MainMenuChoiceNightFNaSR", "V1MainMenuFNaSR"))

screen V1MainMenuAchievementsFNaSR:
    tag v1menuFNaSR

    default mm = v1FNaSR.MainMenuTools
    default tt = v1FNaSR.TextTools

    use V1MainMenuFrameFNaSR()

    key "mouseup_3" action Function(mm.screen_switching, "V1MainMenuAchievementsFNaSR", "V1MainMenuFNaSR")
    key "K_ESCAPE" action Function(mm.screen_switching, "V1MainMenuAchievementsFNaSR", "V1MainMenuFNaSR")

    add tt.text("Достижения", size=22) align(0.5, 0.14)

    vbox align(0.5, 0.5):
        add tt.text("В разработке") xalign 0.5
        add tt.textbutton("Назад", Function(mm.screen_switching, "V1MainMenuAchievementsFNaSR", "V1MainMenuFNaSR"), xalign=0.5)

screen V1MainMenuSettingsFNaSR:
    tag v1menuFNaSR

    default mm = v1FNaSR.MainMenuTools
    default tt = v1FNaSR.TextTools

    use V1MainMenuFrameFNaSR()

    key "mouseup_3" action Function(mm.screen_switching, "V1MainMenuSettingsFNaSR", "V1MainMenuFNaSR")
    key "K_ESCAPE" action Function(mm.screen_switching, "V1MainMenuSettingsFNaSR", "V1MainMenuFNaSR")

    add tt.text("Настройки", size=22) align(0.5, 0.14)

    vbox align(0.5, 0.5):
        add tt.text("В разработке") xalign 0.5
        add tt.textbutton("Назад", Function(mm.screen_switching, "V1MainMenuSettingsFNaSR", "V1MainMenuFNaSR"), xalign=0.5)






screen V1GameMenuSelectorFNaSR:
    zorder 999
    modal True

    default cycle = v1FNaSR.require_system("cycle")

    default tt = v1FNaSR.TextTools
    default settings = False
    default is_running = v1FNaSR.require_system("night").is_running
    default loaded = v1FNaSR.require_system("night").loaded
    default confirmation_action = None

    default bar_null = Frame(v1FNaSR.resources.images.other["bar_null"],36,36)
    default bar_full = Frame(v1FNaSR.resources.images.other["bar_full"],36,36)
    default hide_gms = Hide("V1GameMenuSelectorFNaSR", transition=dspr)

    key ["K_ESCAPE", "mouseup_3"] action hide_gms

    on "show" action Function(cycle.freeze)
    on "hide" action Function(cycle.unfreeze)

    add "black" alpha 0.5

    if is_running:
        text loaded.title style "v1_text_24_style_FNaSR" xalign 1.0 at v1_text_flicker_FNaSR()

    add tt.text("Пять Ночей в Совёнке Remaster", size=24, g_power=0.0575) align(0.5, 0.1)

    vbox align(0.5, 0.5) spacing 15:
        if confirmation_action is None:
            if not settings:
                textbutton tt.text("Продолжить") background None xalign 0.5 hover_sound v1FNaSR.resources.sounds.ui["button_h"] activate_sound v1FNaSR.resources.sounds.ui["button_c"] action hide_gms

                if is_running:
                    textbutton tt.text("Начать ночь заново"):
                        background None xalign 0.5
                        hover_sound v1FNaSR.resources.sounds.ui["button_h"]
                        activate_sound v1FNaSR.resources.sounds.ui["button_c"]
                        action SetScreenVariable("confirmation_action", [hide_gms, Function(v1FNaSR.Tools.restart_night, loaded)])

                    textbutton tt.text("В меню"):
                        background None xalign 0.5
                        hover_sound v1FNaSR.resources.sounds.ui["button_h"]
                        activate_sound v1FNaSR.resources.sounds.ui["button_c"]
                        action SetScreenVariable("confirmation_action", [hide_gms, Function(cycle.request_transition, "v1_night_stop_label_FNaSR")])
                    
                textbutton tt.text("Настройки"):
                    background None xalign 0.5
                    hover_sound v1FNaSR.resources.sounds.ui["button_h"]
                    activate_sound v1FNaSR.resources.sounds.ui["button_c"]
                    action SetScreenVariable("settings", True)

                textbutton tt.text("Выйти"):
                    background None xalign 0.5
                    hover_sound v1FNaSR.resources.sounds.ui["button_h"]
                    activate_sound v1FNaSR.resources.sounds.ui["button_c"]
                    action SetScreenVariable("confirmation_action", [hide_gms, Function(renpy.jump, "v1_quit_FNaSR")])
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
    def _v1_main_menu_screen_handler_FNaSR(screen_list, state, **kwargs):
        menu_index = kwargs.pop("menu_index", 0)
        if state == "show":
            renpy.show_screen(screen_list[menu_index], **kwargs)
        elif state == "hide":
            for screen_name in screen_list:
                renpy.hide_screen(screen_name, **kwargs)

    v1FNaSR.screen_manager.register_screen(
        "main menu",
        [
            "V1MainMenuFNaSR",
            "V1MainMenuChoiceNightFNaSR",
            "V1MainMenuAchievementsFNaSR",
            "V1MainMenuSettingsFNaSR"
        ],
        callback=_v1_main_menu_screen_handler_FNaSR
    )

    del _v1_main_menu_screen_handler_FNaSR


label v1_play_FNaSR(night=None, sequence=v1FNaSR.MAIN_SEQUENCE):
    $ v1FNaSR.audio.play(v1FNaSR.resources.sounds.sfx["tablet_close_1"], "sound")
    $ v1FNaSR.MainMenuTools.close()
    scene black
    show anim v1_tablet_close_entire_FNaSR
    $ renpy.pause(0.18, hard=True)
    hide anim v1_tablet_close_entire_FNaSR
    $ renpy.pause(.1, hard=True)
    call v1_load_night_label_FNaSR(night=night, sequence=sequence)

label v1_quit_mm_FNaSR:
    $ v1FNaSR.audio.play(v1FNaSR.resources.sounds.sfx["tablet_close_1"], "sound")
    scene black
    show anim v1_tablet_close_entire_FNaSR
    $ renpy.pause(0.18, hard=True)
    hide anim v1_tablet_close_entire_FNaSR
    $ renpy.pause(.1, hard=True)
    jump v1_quit_FNaSR
