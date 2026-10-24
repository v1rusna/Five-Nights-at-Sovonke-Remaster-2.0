
# base.rpy
init -3 python in v1FNaSR:
    import traceback as _traceback
    import threading as _threading
    from weakref import WeakSet as _WeakSet

    _created_enemy = _WeakSet()
    _created_enemy_lock = _threading.Lock()
    def _register_enemy(enemy):
        if not isinstance(enemy, BaseEnemy):
            return
        with _created_enemy_lock:
            _created_enemy.add(enemy)
    def get_created_enemy():
        with _created_enemy_lock:
            created_enemy = tuple(_created_enemy)
        return created_enemy

    def recolor_enemy_sprite(sprite):
        return renpy.store.Transform(sprite, matrixcolor=renpy.store.SaturationMatrix(0.4))

    class EnemyModule(ResetLogic):
        __slots__ = ("_error", "_freeze",)

        dependent_modules = tuple()
        conflicting_modules = tuple()

        def __init__(self):
            super(EnemyModule, self).__init__()
            self._error = None
            self._freeze = False

        @property
        def error(self):
            return self._error

        @property
        def freezing(self):
            return self._freeze

        def set_error(self, text=None):
            if text is None:
                text = _traceback.format_exc()
            self._error = text

        def clear_error(self):
            self._error = None

        def freeze(self):
            self._freeze = True

        def unfreeze(self):
            self._freeze = False


        def on_include(self, enemy):
            pass

        def start(self, context):
            pass

        def tick_update(self, context, dt):
            pass

        def update(self, context):
            pass
        
        def get_debug_list_texts(self, enemy_context):
            return tuple()

        def __repr__(self):
            return "<{} error={} freezed={}>".format(type(self).__name__, self._error is not None, self._freeze)

    class BaseEnemy(GameObject, BaseAI):
        def __init__(self, modules=None):
            super(BaseEnemy, self).__init__()
 
            self._modules = list()
            self._types_modules = set()
            self._context = EnemyContext(self)

            if isinstance(modules, (list, tuple,)):
                for module in modules:
                    self.add_module(module)

        @property
        def context(self):
            return self._context

        @property
        def modules(self):
            return tuple(self._modules)

        @property
        def types_modules(self):
            return tuple(self._types_modules)

        @property
        def errors(self):
            errors = []
            for m in self.modules:
                if m.error:
                    errors.append("{}: {}".format(repr(m), m.error))
            return tuple(errors)

        def add_module(self, module):
            if not isinstance(module, EnemyModule):
                raise FNaSRTypeError("'module' должен быть наследником 'EnemyModule', получено: {}".format(type(module)))

            type_module = type(module)

            if type_module is EnemyModule:
                raise FNaSRTypeError("Нельзя добавлять родительский модуль 'EnemyModule'.")

            if type_module in self._types_modules:
                raise FNaSRTypeError("Модуль типа '{}' уже добавлен.".format(type_module))

            for cls_m in module.dependent_modules:
                if cls_m not in self._types_modules:
                    raise FNaSRValueError("Модуль '{!r}' зависит от модуля '{}' который не подключен.".format(module, cls_m))

            for cls_m in module.conflicting_modules:
                if cls_m in self._types_modules:
                    raise FNaSRValueError("Модуль '{!r}' конфликтует с уже подключённым модулем '{}'.".format(module, cls_m))

            for m in self._modules:
                if type_module in m.conflicting_modules:
                    raise FNaSRValueError("Модуль '{!r}' конфликтует с уже подключённым модулем '{}'.".format(module, m))

            module.on_include(self)

            self._modules.append(module)
            self._types_modules.add(type_module)

        def remove_module(self, module):
            try:
                self._modules.remove(module)
            except ValueError as e:
                raise FNaSRValueError(e)

            type_module = type(module)
            has_same_type = any(
                type(other) is type_module
                for other in self._modules
            )

            if not has_same_type:
                self._types_modules.discard(type_module)

        def remove_module(self, module):
            if module not in self._modules:
                raise FNaSRValueError("Модуль '{}' не подключён к противнику.".format(repr(module)))

            type_module = type(module)

            dependents = [
                other
                for other in self._modules
                if other is not module
                and type_module in other.dependent_modules
            ]

            if dependents:
                raise FNaSRValueError("Нельзя удалить модуль '{}': от него зависят модули: {}.".format(repr(module), ", ".join(repr(other) for other in dependents)))

            self._modules.remove(module)
            self._types_modules.discard(type_module)

        def has_module(self, module):
            return module in self._modules

        def start(self):
            for module in self._modules:
                if module.error:
                    continue
                self._safe_call(module, "start", self._context)

        def tick_update(self, dt, refresh_time):
            self.current_refresh_time = refresh_time
            self._accumulated_time += dt

            for module in self._modules:
                if module.error or module.freezing:
                    continue
                self._safe_call(module, "tick_update", self._context, dt)

            while self._consume_refresh(refresh_time):
                self.update()

        def update(self):
            for module in self._modules:
                if module.error or module.freezing:
                    continue
                self._safe_call(module, "update", self._context)

        def reset(self):
            for module in self._modules:
                self._safe_call(module, "reset", self._context)

            super(BaseEnemy, self).reset()

        def _safe_call(self, module, name_fn, *args, **kwargs):
            fn = getattr(module, name_fn, None)
            if fn is None:
                return
            try:
                fn(*args, **kwargs)
            except Exception:
                module.set_error()


    class Enemy(BaseEnemy):
        def __init__(self, tag, name, sprite, color=None, nights_start=None, special_night=None, **kwargs):
            super(Enemy, self).__init__(**kwargs)

            if not is_string(tag):
                raise FNaSRTypeError("'tag' должен быть строкой, получено: {}".format(type(tag)))

            if not is_string(name):
                raise FNaSRTypeError("'name' должен быть строкой, получено: {}".format(type(name)))

            if not is_string(sprite):
                raise FNaSRTypeError("'sprite' должен быть строкой, получено: {}".format(type(sprite)))

            if color is not None and not is_string(color):
                raise FNaSRTypeError("'color' должен быть строкой, получено: {}".format(type(color)))

            if special_night is None:
                special_night = ()
            elif is_string(special_night):
                special_night = (special_night,)
            elif not isinstance(special_night, (list, tuple, set,)):
                raise FNaSRTypeError("'special_night' должен быть списком, кортежем или множеством, получено: {}".format(type(special_night)))

            if nights_start is not None:
                nights_start = int(nights_start)

            self._tag = tag
            self._nights_start = nights_start
            self._special_night = set(special_night)
            self._name = name
            self._color = color
            self._setattr("_align", (0.5, 0.5))

            self._sprite_path = sprite
            self._sprite = recolor_enemy_sprite(sprite)
            self._parallax_sprite = Parallax(
                displayable=self._sprite,
                zoom=1.15,
                anchor=None,
                power=0.10,
                sharpness_factor=0.1,
                fill_viewport=True
            )

            _register_enemy(self)

        @property
        def tag(self):
            return self._tag

        @property
        def nights_start(self):
            return self._nights_start

        @property
        def special_night(self):
            return tuple(self._special_night)

        @property
        def name(self):
            return self._name

        @property
        def color(self):
            return self._color

        @property
        def align(self):
            return self._align

        @property
        def sprite_path(self):
            return self._sprite_path

        @property
        def sprite(self):
            return self._sprite

        @property
        def parallax_sprite(self):
            return self._parallax_sprite

        def set_align(self, x=None, y=None):
            if x is None:
                x = renpy.random.uniform(0.1, 0.9)
            if y is None:
                y = 0.5

            x = float(x)
            y = float(y)

            self._align = (x, y,)


