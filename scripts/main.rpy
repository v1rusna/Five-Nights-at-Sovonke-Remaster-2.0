init:
    $ _v1_size_style_text_mod = 16 if renpy.android or renpy.ios else 24
    style _v1_text_mod_style_FNaSR:
        color "#ffffff"
        size _v1_size_style_text_mod
        font "FNaSR/fonts/retrobanker.ttf"
        outlines [(2, "#000000", 2, 2)]
    image v1_mod_button_text_FNaSR = At(Text("Пять Ночей в Совёнке Remaster", style="_v1_text_mod_style_FNaSR"), v1_vhs_crt_shader_t_FNaSR(0.0575))
    $ mods["AAA_v1_start_FNaSR"] = " {image=v1_mod_button_text_FNaSR} "

label AAA_v1_start_FNaSR:

    stop music fadeout 2
    window hide dissolve

    python:
        renpy.music.play("FNaSR/sounds/sfx/startday.wav", channel="sound", loop=False)
        renpy.scene()
        renpy.show("bg black")
        renpy.with_statement(dissolve2)
        renpy.pause(2.0, hard=True)
        renpy.show_screen("V1BaseUIScreenFNaSR")

        renpy.block_rollback()

label v1_init_FNaSR:
    $ v1FNaSR.start_mod()
    if not v1FNaSR.is_initialized():
        return

    if not persistent.v1_recommendation_seen_FNaSR:
        show expression v1FNaSR.InitImages.recommendation at v1_set_align_center_FNaSR(0.5, 0.5)
        with dissolve
        $ renpy.pause(1.0, hard=True)
        pause 5
        hide expression v1FNaSR.InitImages.recommendation with dissolve
        $ renpy.pause(1.0, hard=True)
        $ persistent.v1_recommendation_seen_FNaSR = True
        #jump v1_prolog_label_FNaSR

    jump v1_load_night_label_FNaSR

label v1_main_menu_label_FNaSR:
    $ v1FNaSR.show_screen("main menu")
    jump v1_loop_FNaSR


label v1_load_night_label_FNaSR(night=None, ignore_lock=False, sequence=v1FNaSR.MAIN_SEQUENCE):
    python hide:
        ns = v1FNaSR.require_system("night")

        if night is not None:
            ns.load(night, ignore_lock)
        else:
            if sequence is None:
                raise v1FNaSR.FNaSRException("Не указана ни ночь, ни последовательность.")

            # Продолжение; если непройденных нет — повтор последней открытой ночи.
            target = ns.find_available_night(sequence)

            if target is None:
                target = ns.find_last_unlocked_night(sequence)

            if target is None:
                raise v1FNaSR.FNaSRException("В последовательности '{}' нет открытых ночей.".format(sequence))

            ns.load(target, ignore_lock)

        ns.start()

    jump v1_game_FNaSR



label v1_game_FNaSR:
    python hide:
        ns = v1FNaSR.require_system("night")
        ls = v1FNaSR.require_system("location")
        if ns.loaded.start_location_id:
            location = ls.require_location(ns.loaded.start_location_id)
        else:
            location = ls.get_location(-1)
        if location is not None:
            v1FNaSR.require_system("player").current_player.move(location)
        v1FNaSR.show_screen("game_interface")
        v1FNaSR.show_screen("debug")
        v1FNaSR.require_system("cycle").start()

label v1_loop_FNaSR:
    $ renpy.pause(hard=True)
    jump v1_loop_FNaSR



label v1_quit_mm_FNaSR:
    $ v1FNaSR.play(v1FNaSR.resources.sounds.sfx["tablet_close_1"], "sound")
    scene black
    show anim v1_tablet_close_entire_VNaSR
    $ renpy.pause(0.18, hard=True)
    hide anim v1_tablet_close_entire_VNaSR
    $ renpy.pause(.1, hard=True)

label v1_quit_FNaSR:
    $ v1FNaSR.require_system("cycle").stop(True)
    $ v1FNaSR.quit_mod()
    scene black with dissolve
    $ renpy.pause(.5, hard=True)
    $ MainMenu(confirm=False)()
