# state.rpy
init python early:
    import sys

    DEBUG_FLAG = "--v1FNaSR:Debug"

    renpy.store.V1_DEBUG_FNaSR = DEBUG_FLAG in sys.argv

    if renpy.store.V1_DEBUG_FNaSR:
        sys.argv.remove(DEBUG_FLAG)

init -6 python in v1FNaSR:
    import threading as _threading
    import sys as _sys

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
    _store["debug_mode"] = bool(getattr(renpy.store, "V1_DEBUG_FNaSR", False))
    _store["initialized"] = False
    _store["base_initialized"] = False

    _store_lock = _threading.RLock()

    def is_debug():
        with _store_lock:
            return _store["debug_mode"]

    def is_initialized(full=True, only_base=False):
        with _store_lock:
            if full:
                return _store["initialized"] and _store["base_initialized"]
            if only_base:
                return _store["base_initialized"]
            return _store["initialized"] or _store["base_initialized"]
