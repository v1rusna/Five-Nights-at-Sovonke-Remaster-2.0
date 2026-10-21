# screenManager.rpy

init -5 python in v1FNaSR:
    import threading as _threading

    class ScreenManager(object):
        __slots__ = ("_registry", "_replacements", "_lock",)

        def __init__(self):
            self._registry = _ScreensRegistry(
                "экранов",
                "Экран с ключом '{}' уже зарегистрирован",
                "Экран с ключом '{}' не найден",
                "Значение экрана должно быть итерируемым, а не '{}'"
            )

            self._replacements = {}
            self._lock = _threading.RLock()

        @main_thread_only
        def register_screen(
            self, screen_key, screen_names,
            overwrite=False, callback=None
        ):
            with self._lock:
                self._registry.register(
                    screen_key,
                    screen_names,
                    overwrite,
                    callback
                )

        @main_thread_only
        def delete_screen(self, screen_key):
            with self._lock:
                self._registry.delete(screen_key)

        @main_thread_only
        def edit_screen(
            self,
            screen_key,
            new_screen_names=MISSING,
            new_callback=MISSING
        ):
            with self._lock:
                self._registry.edit(
                    screen_key,
                    new_screen_names,
                    new_callback
                )

        def get_screen_data(self, screen_key, default=None):
            with self._lock:
                return self._registry.get(screen_key, default)

        def get_screen_names(self, screen_key, default=None):
            with self._lock:
                return self._registry.get_names(screen_key, default)

        def has_screen(self, screen_key):
            with self._lock:
                return self._registry.has(screen_key)

        @main_thread_only
        def show_screen(self, screen_key, **kwargs):
            with self._lock:
                screen_data = self._registry.get(screen_key)

            if screen_data is None:
                raise FNaSRRegisterError("Экран по ключу '{}' не найден".format(screen_key))

            screen_names, callback = screen_data

            callback(screen_names, "show", **kwargs)

        @main_thread_only
        def hide_screen(self, screen_key, **kwargs):
            with self._lock:
                screen_data = self._registry.get(screen_key)

            if screen_data is None:
                raise FNaSRRegisterError("Экран по ключу '{}' не найден".format(screen_key))

            screen_names, callback = screen_data
            callback(screen_names, "hide", **kwargs)

        @main_thread_only
        def hide_all_screen(self, directly=False, **kwargs):
            with self._lock:
                screen_data = self._registry.values()

            for screen_names, callback in screen_data:
                if directly:
                    _default_screen_handler(screen_names, "hide", **kwargs)
                else:
                    callback(screen_names, "hide", **kwargs)

        @main_thread_only
        def replace_screen(self, original_screen_name, name_new_screen):
            if is_initialized():
                raise FNaSRRegisterError("Нельзя заменять экраны после начала игры.")

            with self._lock:
                if original_screen_name in self._replacements:
                    raise FNaSRRegisterError("Экран '{}' уже был заменен.".format(original_screen_name))

                screens = renpy.display.screen.screens

                try:
                    original_screen = screens[(original_screen_name, None)]
                except KeyError:
                    raise FNaSRRegisterError("Исходный экран '{}' не найден.".format(original_screen_name))

                try:
                    replacement_screen = screens[(name_new_screen, None)]
                except KeyError:
                    raise FNaSRRegisterError("Экран-замена '{}' не найден.".format(name_new_screen))

                screens[(original_screen_name, None)] = replacement_screen

                self._replacements[original_screen_name] = (name_new_screen, original_screen)

        @main_thread_only
        def restore_screen(self, original_screen_name):
            if is_initialized():
                raise FNaSRRegisterError("Нельзя изменять экраны после начала игры.")

            with self._lock:
                data = self._replacements.get(original_screen_name)

                if data is None:
                    raise FNaSRRegisterError("Экран '{}' не был заменен.".format(original_screen_name))

                _, original_screen = data

                renpy.display.screen.screens[(original_screen_name, None)] = original_scree
                del self._replacements[original_screen_name]

        @main_thread_only
        def restore_all_screens(self):
            if is_initialized():
                raise FNaSRRegisterError("Нельзя изменять экраны после начала игры.")

            with self._lock:
                snapshot = dict(self._replacements)

            errors = []

            for original_name, data in iter_items(snapshot):
                replacement_name, original_screen = data

                try:
                    renpy.display.screen.screens[(original_name, None)] = original_screen
                except Exception as e:
                    errors.append((original_name, replacement_name, e))
                    continue

                with self._lock:
                    self._replacements.pop(original_name, None)

            if errors:
                message = "При восстановлении экранов произошли исключения:\n"

                for original_name, replacement_name, error in errors:
                    message += "{} <- {}: {}\n".format(
                        original_name,
                        replacement_name,
                        error
                    )

                raise FNaSRException(message)

        def is_replaced_screen(self, screen_name):
            with self._lock:
                return screen_name in self._replacements

    screen_manager = ScreenManager()

init python:
    v1FNaSR.add_quit_fn(lambda: v1FNaSR.screen_manager.hide_all_screen(True))
    v1FNaSR.add_quit_fn(v1FNaSR.screen_manager.restore_all_screens)
