# state.rpy
init -10 python in v1FNaSR:
    import threading as _threading

    _store = dict()
    _store["old"] = dict()
    _store["start_fn"] = dict()
    _store["quit_fn"] = dict()
    _store["called_start_fn"] = list()
    _store["called_quit_fn"] = list()
    _store["systems"] = _Registry(
        "систем",
        "Система '{}' уже зарегистрирована",
        "Система '{}' не найдена"
    )
    _store["debug_mode"] = False
    _store["initialized"] = False
    _store["base_initialized"] = False
    _store["init_mod_label"] = "v1_init_FNaSR"

    _store["keymap"] = {
        'button_select': ['mouseup_1', 'K_RETURN', 'K_KP_ENTER', 'joy_dismiss'],
        'button_ignore': ['mousedown_1'],
        'button_alternate': ['mouseup_3'],
        'button_alternate_ignore': ['mousedown_3'],
        'dismiss': ['mouseup_1', 'K_RETURN', 'K_SPACE', 'K_KP_ENTER', 'joy_dismiss'],
        'bar_activate': ['mousedown_1', 'K_RETURN', 'K_KP_ENTER', 'joy_dismiss'],
        'bar_deactivate': ['mouseup_1', 'K_RETURN', 'K_KP_ENTER', 'joy_dismiss'],
        'drag_activate': ['mousedown_1'],
        'drag_deactivate': ['mouseup_1'],
        'viewport_drag_start': ['mousedown_1'],
        'viewport_drag_end': ['mouseup_1'],
        'viewport_up': ['mousedown_4'],
        'viewport_down': ['mousedown_5'],
        'viewport_wheeldown': ['mousedown_5'],
        'viewport_wheelup': ['mousedown_4'],
        'toggle_fullscreen': ['alt_K_RETURN', 'alt_K_KP_ENTER', 'K_F11'],
        'input_backspace': ['K_BACKSPACE', 'repeat_K_BACKSPACE'],
        'input_copy': ['ctrl_noshift_K_INSERT', 'ctrl_noshift_K_c'],
        'input_delete': ['K_DELETE', 'repeat_K_DELETE'],
        'input_delete_full': ['meta_K_BACKSPACE'],
        'input_delete_word': ['osctrl_K_BACKSPACE'],
        'input_down': ['K_DOWN', 'repeat_K_DOWN'],
        'input_end': ['K_END', 'meta_K_RIGHT'],
        'input_enter': ['K_RETURN', 'K_KP_ENTER'],
        'input_home': ['K_HOME', 'meta_K_LEFT'],
        'input_jump_word_left': ['osctrl_K_LEFT'],
        'input_jump_word_right': ['osctrl_K_RIGHT'],
        'input_left': ['K_LEFT', 'repeat_K_LEFT'],
        'input_paste': ['shift_K_INSERT', 'ctrl_noshift_K_v'],
        'input_right': ['K_RIGHT', 'repeat_K_RIGHT'],
        'input_up': ['K_UP', 'repeat_K_UP'],
    }

    _store_lock = _threading.RLock()

    def is_debug():
        with _store_lock:
            return _store["debug_mode"]

    def is_initialized(full=True):
        with _store_lock:
            if full:
                return _store["initialized"] and _store["base_initialized"]
            return _store["initialized"] or _store["base_initialized"]
