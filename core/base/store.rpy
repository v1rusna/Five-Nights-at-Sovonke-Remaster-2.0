# state.rpy
init -6 python in v1FNaSR:
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
    _store["screens"] = _ScreensRegistry(
        "экранов",
        "Экран с ключом '{}' уже зарегистрирован",
        "Экран с ключом '{}' не найден",
        "Значение экрана должно быть итерируемым, а не '{}'"
    )
    _store["sound_channels"] = dict()
    _store["debug_mode"] = True
    _store["initialized"] = False
    _store["base_initialized"] = False

    _store_lock = _threading.RLock()

    def is_debug():
        with _store_lock:
            return _store["debug_mode"]

    def is_initialized(full=True, only_base=False): # может все таки стоит убрать only_base и добавить def is_base_initialized()
        with _store_lock:
            if full:
                return _store["initialized"] and _store["base_initialized"]
            if only_base:
                return _store["base_initialized"]
            return _store["initialized"] or _store["base_initialized"]
