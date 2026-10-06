# lifecycle.rpy
init -5 python in v1FNaSR:
    class BaseHook(object):
        """
        Базовый класс для хуков жизненного цикла, выполняемых при запуске и завершении работы FNaSR.

        Хук может быть зарегистрирован в качестве функции запуска или завершения. В ходе выполнения
        жизненный цикл обрабатывает каждый зарегистрированный хук в заданном порядке.

        Для каждого хука жизненный цикл использует следующую последовательность:
            init()
            __call__()
            handle_exception(exc)  # только если __call__() завершился с ошибкой

        init() вызывается перед __call__().
        Его сбой записывается в логах, а хук пропускается

        Метод __call__() выполняет основную операцию хука.
        Если она вызывает
        исключение, жизненный цикл фиксирует сбой в логах и вызывает handle_exception()
        с исходным исключением.

        handle_exception() — это этап восстановления после сбоя в __call__(). Он может
        восстанавливать состояние или выполнять очистку

        Один и тот же жизненный цикл используется как для хуков запуска, так и для хуков завершения.
        Разница заключается лишь в том, на каком этапе жизненного цикла хук регистрируется
        и выполняется.

        Порядок выполнения хуков определяется их зарегистрированным параметром `order`.

        Если хук зарегистрирован с once=True, жизненный цикл выполняет его не более одного раза за соответствующую коллекцию хуков.
        """
        def init(self):
            """
            Инициализирует хук перед его основным выполнением.

            Этот метод является альтернативой __init__.

            __init__ выполняется сразу же после создания объекта хука.
            В этот момент другие компоненты FNaSR, необходимые хуку, могут ещё
            не быть инициализированы. init() выполняется позже, непосредственно
            перед __call__(), когда жизненный цикл уже достиг
            соответствующей стадии выполнения хука.

            Жизненный цикл выполняет эти стадии в следующем порядке:
                init()
                __call__()

            Если init() генерирует исключение, оно записывается в логах, а хук пропускается

            Поэтому метод init() может использоваться для инициализации, зависящей от
            компонентов или состояния, подготовленных ранее выполненными хуками жизненного цикла.

            Исключение, сгенерированное методом init(), не передаётся в handle_exception().
            Метод handle_exception() используется только для исключений, сгенерированных методом __call__()
            Поэтому изменять состояние в этой методе запрещено.
            """
            pass

        def __call__(self):
            """
            Выполнить основную логику хука.

            Этот метод представляет собой основной этап выполнения хука и должен быть
            переопределён подклассами.

            Жизненный цикл вызывает __call__() после init(). Если __call__() генерирует
            исключение, жизненный цикл записывает это исключение в логах, а затем вызывает
            handle_exception() с исходным исключением.

            Исключение, сгенерированное методом __call__(), не останавливает выполнение
            остальных хуков жизненного цикла.
            """
            raise FNaSRNotImplementedError

        def handle_exception(self, exc):
            """
            Обработка исключения, сгенерированного методом __call__().

            Этот метод вызывается только в том случае, если основное выполнение хука
            (__call__()) завершилось с ошибкой.

            Исходное исключение передаётся в качестве `exc`.

            Цель этого метода - привести хук и любое состояние, на которое повлияло
            его частичное выполнение, в приемлемое состояние. Он может выполнять
            очистку, восстанавливать состояние, отменять частично примененные изменения или выполнять
            другие действия по восстановлению, необходимые хуку.

            Если handle_exception() сам генерирует исключение, это исключение записывается в логах

            Исключения, сгенерированные init(), не обрабатываются этим методом.
            """
            pass

    def add_start_fn(fn, order=0, once=False):
        order = int(order)
        if not callable(fn):
            raise FNaSRTypeError("fn должен быть вызываемым объектом, а не '{}'".format(type(fn)))
        with _store_lock:
            if order not in _store["start_fn"]:
                raise FNaSRException("'{}' order не существует".format(order))
            _store["start_fn"][order].append((fn, bool(once),))

    def add_quit_fn(fn, order=0, once=False):
        order = int(order)
        if not callable(fn):
            raise FNaSRTypeError("fn должен быть вызываемым объектом, а не '{}'".format(type(fn)))
        with _store_lock:
            if order not in _store["quit_fn"]:
                raise FNaSRException("'{}' order не существует".format(order))
            _store["quit_fn"][order].append((fn, bool(once),))

    # Я решил сделать именно так чтобы это не превратилось в новый init, а order создавались осознано и при необходимости
    def create_start_fn_order(new_order):
        new_order = int(new_order)
        with _store_lock:
            if new_order in _store["start_fn"]:
                raise FNaSRException("'{}' order уже существует".format(new_order))
            _store["start_fn"][new_order] = list()

    def create_quit_fn_order(new_order):
        new_order = int(new_order)
        with _store_lock:
            if new_order in _store["quit_fn"]:
                raise FNaSRException("'{}' order уже существует".format(new_order))
            _store["quit_fn"][new_order] = list()

    def has_start_fn_order(order):
        with _store_lock:
            return int(order) in _store["start_fn"]

    def has_quit_fn_order(order):
        with _store_lock:
            return int(order) in _store["quit_fn"]


    def start_mod():
        if renpy.game.context().init_phase:
            raise FNaSRException("start_mod нельзя вызывать во время инициализации")

        with _store_lock:
            if _store["initialized"]:
                return

            if _store["base_initialized"]:
                raise FNaSRRuntimeError("Базовое состояние уже было проинициализировано, но инициализация ещё не закончилась, вероятно start_mod был запущен в одном из хуков")

        try:
            ViewportManager.init()
            resources.init()
        except Exception:
            raise FNaSRRuntimeError("Ошибка инициализации основных систем мода\n" + _traceback.format_exc())

        def _error(header):
            renpy.log("FNaSR | start | {}\n{}".format(header, _traceback.format_exc()))

        with _store_lock:
            _store["base_initialized"] = True
            _store["old"]["preferences_gl_powersave"] = renpy.store._preferences.gl_powersave
            _store["old"]["preferences_gl_framerate"] = renpy.store._preferences.gl_framerate
            _store["old"]["config_image_cache_size_mb"] = renpy.store.config.image_cache_size_mb
            _store["old"]["config_allow_skipping"] = renpy.store.config.allow_skipping
            _store["old"]["config_has_autosave"] = renpy.store.config.has_autosave
            _store["old"]["config_rollback_enabled"] = renpy.store.config.rollback_enabled
            _store["old"]["config_has_quicksave"] = renpy.store.config.has_quicksave
            _store["old"]["config_window_title"] = renpy.store.config.window_title
            _store["old"]["config_name"] = renpy.store.config.name
            _store["old"]["config_version"] = renpy.store.config.version

        try:
            renpy.store._errorhandling.ignore = False
            renpy.store._errorhandling.rollback = False
            renpy.store._errorhandling.reload = False
            renpy.store._errorhandling.console = False
        except Exception:
            _error("Error path renpy.store._errorhandling")

        renpy.store._autosave = False
        renpy.config.new_substitutions = False

        with _store_lock:
            snapshot = []

            for order in sorted(_store["start_fn"]):
                snapshot.extend(_store["start_fn"][order])

            snapshot = tuple(snapshot)

        for fn, once in snapshot:
            with _store_lock:
                if once and fn in _store["called_start_fn"]:
                    continue

            _run_hook(fn, _error)

            if once:
                with _store_lock:
                    if fn not in _store["called_start_fn"]:
                        _store["called_start_fn"].append(fn)

        renpy.store._preferences.gl_powersave = False
        renpy.store._preferences.gl_framerate = 144
        renpy.store.config.image_cache_size_mb = 400
        renpy.store.config.allow_skipping = False
        renpy.store.config.has_autosave = False
        renpy.store.config.rollback_enabled = False
        renpy.store.config.has_quicksave = False
        renpy.store.config.window_title = "Пять Ночей в Совёнке Remaster"
        renpy.store.config.name = "FNaSR"
        renpy.store.config.version = "v19.09.2026"

        renpy.store.night_time()
        renpy.store.persistent.sprite_time = "night"
        renpy.store.save_name = "FNaSR | Как ты сохранился?"

        game_cycle_system = get_system("cycle")

        renpy.config.quit_callbacks.append(quit_mod)
        if game_cycle_system is not None:
            renpy.config.quit_callbacks.append(game_cycle_system.stop)
            with _store_lock:
                _store["_game_cycle_system.stop"] = game_cycle_system.stop

        with _store_lock:
            _store["initialized"] = True

    def quit_mod():
        if renpy.game.context().init_phase:
            raise FNaSRException("quit_mod нельзя вызывать во время инициализации")

        with _store_lock:
            if not _store["initialized"]:
                return

            _store["initialized"] = False 
            _store["base_initialized"] = False

        def _error(header):
            renpy.log(
                "FNaSR | quit | {}\n{}".format(
                    header,
                    _traceback.format_exc()
                )
            )

        renpy.store._autosave = True
        renpy.config.new_substitutions = True

        renpy.config.quit_callbacks.remove(quit_mod)
        stop_fn = _store.get("_game_cycle_system.stop")
        if stop_fn is not None:
            renpy.config.quit_callbacks.remove(stop_fn)

        with _store_lock:
            renpy.store._preferences.gl_powersave =  _store["old"]["preferences_gl_powersave"]
            renpy.store._preferences.gl_framerate =  _store["old"]["preferences_gl_framerate"]
            renpy.store.config.image_cache_size_mb = _store["old"]["config_image_cache_size_mb"]
            renpy.store.config.allow_skipping =      _store["old"]["config_allow_skipping"]
            renpy.store.config.has_autosave =        _store["old"]["config_has_autosave"]
            renpy.store.config.has_quicksave =       _store["old"]["config_has_quicksave"]
            renpy.store.config.rollback_enabled =    _store["old"]["config_rollback_enabled"]
            renpy.store.config.window_title =        _store["old"]["config_window_title"]
            renpy.store.config.name =                _store["old"]["config_name"]
            renpy.store.config.version =             _store["old"]["config_version"]

        try:
            renpy.store._errorhandling.ignore = True
            renpy.store._errorhandling.rollback = True
            renpy.store._errorhandling.reload = True
            renpy.store._errorhandling.console = True
        except Exception:
            _error("Error path renpy.store._errorhandling")

        with _store_lock:
            snapshot = []

            for order in sorted(_store["quit_fn"]):
                snapshot.extend(_store["quit_fn"][order])

            snapshot = tuple(snapshot)

        for fn, once in snapshot:
            with _store_lock:
                if once and fn in _store["called_quit_fn"]:
                    continue

            _run_hook(fn, _error)

            if once:
                with _store_lock:
                    if fn not in _store["called_quit_fn"]:
                        _store["called_quit_fn"].append(fn)

        renpy.store.save_name = ""

    def _run_hook(fn, log):
        hook_name = getattr(fn, "__name__", repr(fn))

        init = getattr(fn, "init", None)

        if init is not None:
            try:
                init()
            except Exception:
                log("Хук не смог инициализироваться ({}):".format(hook_name))
                return

        try:
            fn()
        except Exception as exc:
            log("Ошибка в хуке ({}):".format(hook_name))

            handle_exception = getattr(fn, "handle_exception", None)

            if handle_exception is not None:
                try:
                    if not callable(handle_exception):
                        raise FNaSRTypeError("handle_exception хука '{}' должен быть вызываемым объектом".format(hook_name))

                    handle_exception(exc)
                except Exception:
                    log("Хук не смог обработать исключение ({}):".format(hook_name))

    def after_load_FNaSR():
        if "FNaSR" in renpy.store.save_name:
            renpy.error("The 'Five Nights at Sovenk Remaster' mod does not support the renpy save system.")

    renpy.config.after_load_callbacks.append(after_load_FNaSR)

    for i in range(-1, 2):
        if not has_start_fn_order(i):
            create_start_fn_order(i)
        if not has_quit_fn_order(i):
            create_quit_fn_order(i)
