# labels.rpy
init python in v1FNaSR:
    @main_thread_only
    def stop_game_helper(is_win):
        require_system("cycle").stop(True)
        audio.stop_all(0.5)
        screen_manager.hide_all_screen(True)
        require_system("night").finish(bool(is_win))

    def get_latest_killer():
        history_murders = GlobalState.get("HistoryMurders")
        if history_murders is None:
            return None, None

        lasted = history_murders[-1]
        for enemy in get_created_enemy():
            if enemy.tag == lasted[0]:
                return enemy, lasted[1]

        return None, None

label v1_win_label_FNaSR:
    $ v1FNaSR.stop_game_helper(True)

    scene black
    $ v1FNaSR.show_text("{}\nВремя: {}:00\nСмена окончена...".format(v1FNaSR.require_system("night").loaded.title, v1FNaSR.require_system("night").loaded.end_of_shift))

    $ v1FNaSR.GlobalState.clear()
    jump v1_main_menu_label_FNaSR

label v1_screamer_label_FNaSR:
    $ v1FNaSR.stop_game_helper(False)
    scene black
    
    python hide:
        latest_killer, screamer = v1FNaSR.get_latest_killer()
        if latest_killer is not None:
            screamer()

    $ renpy.pause(0.5, hard=True)
    $ v1FNaSR.show_text("{}\nВремя: {}\nСмена окончена...".format(v1FNaSR.require_system("night").loaded.title, v1FNaSR.GlobalState.get("death_time", "00:00")))

    $ v1FNaSR.GlobalState.clear()
    jump v1_main_menu_label_FNaSR
