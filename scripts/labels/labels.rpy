# labels.rpy
init python in v1FNaSR:
    @main_thread_only
    def stop_game_helper(is_win):
        audio.stop_all(0.5)
        visual.hide_all()
        screen_manager.hide_all_screen(True)
        require_system("night").finish(bool(is_win))
        settings.save()

    def get_latest_killer():
        opponent_data = GlobalState.get("OpponentKilledPlayer")
        if opponent_data is None:
            return None, None, None

        for enemy in require_system("enemy").iter_current_group:
            if enemy.tag == opponent_data[0]:
                return enemy, opponent_data[1], opponent_data[2]

        return None, None, None

label v1_night_stop_label_FNaSR:
    $ v1FNaSR.stop_game_helper(False)
    scene black
    jump v1_main_menu_label_FNaSR

label v1_night_win_label_FNaSR:
    $ v1FNaSR.stop_game_helper(True)

    scene black
    $ v1FNaSR.show_text("{}\nВремя: {}:00\nСмена окончена...".format(v1FNaSR.require_system("night").loaded.title, v1FNaSR.require_system("night").loaded.end_of_shift))

    $ v1FNaSR.GlobalState.clear()
    jump v1_main_menu_label_FNaSR

label v1_night_screamer_label_FNaSR:
    $ v1FNaSR.stop_game_helper(False)
    scene black
    
    python hide:
        latest_killer, screamer, death_time = v1FNaSR.get_latest_killer()
        if latest_killer is not None:
            screamer()

        renpy.pause(0.5, hard=True)
        v1FNaSR.show_text("{}\nВремя: {}\nСмена окончена...".format(v1FNaSR.require_system("night").loaded.title, death_time))

        v1FNaSR.GlobalState.clear()
    jump v1_main_menu_label_FNaSR
