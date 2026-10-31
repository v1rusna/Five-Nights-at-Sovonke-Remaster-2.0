
# base.rpy
init -3 python in v1FNaSR:
    import traceback as _traceback
    import threading as _threading

    class EnemyModule(ResetLogic):
        __slots__ = ("_error", "_freeze", "_accumulated_time",)

        dependent_modules = tuple()
        conflicting_modules = tuple()
        optional_modules = tuple()

        @staticmethod
        def get_module(enemy, type_module, default=None):
            if not isinstance(enemy, Enemy):
                raise FNaSRTypeError("'enemy' должен быть 'Enemy', получено: {}".format(type(enemy)))

            for module in enemy.modules:
                if isinstance(module, type_module):
                    return module

            return default

        def __init__(self):
            super(EnemyModule, self).__init__()
            self._error = None
            self._setattr("_freeze", False)
            self._setattr("_accumulated_time", 0.0)

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

        def update(self, context, dt):
            pass

        def reset(self, context):
            super(EnemyModule, self).reset()

        def interval(self, seconds=1.0):
            if seconds <= 0:
                raise FNaSRCycleError("'seconds' must be strictly positive.")

            if self._accumulated_time < seconds:
                return False

            self._accumulated_time -= seconds
            return True

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

        def update(self, dt):
            for module in self._modules:
                if module.error or module.freezing:
                    continue
                self._safe_call(module, "update", self._context, dt)

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
                log.error("Module '{}' error".format(repr(module)))
                module.set_error()


    class Enemy(BaseEnemy):
        POSITIONS = 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9

        @staticmethod
        def recolor_sprite(sprite):
            return renpy.store.Transform(sprite, matrixcolor=renpy.store.SaturationMatrix(0.4))

        def __init__(self, tag, name, sprite, color=None, nights_start=None, special_night=None, **kwargs):
            modules = kwargs.pop("modules", None)
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
            self._setattr("_invisible", False)
            self._setattr("_replaced_sprite", None)
            self._setattr("_replaced_parallax_sprite", None)

            self._sprite_path = sprite
            self._sprite = self.recolor_sprite(sprite)
            self._parallax_sprite = Parallax(
                displayable=self._sprite,
                zoom=1.15,
                anchor=None,
                power=0.10,
                sharpness_factor=0.1,
                fill_viewport=True
            )

            if isinstance(modules, (list, tuple,)):
                for module in modules:
                    self.add_module(module)
            

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
            if self._replaced_sprite is not None:
                return self._replaced_sprite
            return self._sprite

        @property
        def parallax_sprite(self):
            if self._replaced_parallax_sprite is not None:
                return self._replaced_parallax_sprite
            return self._parallax_sprite

        @property
        def is_invisible(self):
            return self._invisible

        @is_invisible.setter
        def is_invisible(self, value):
            self._invisible = bool(value)

        @property
        def original_sprite(self):
            return self._sprite

        @property
        def original_parallax_sprite(self):
            return self._parallax_sprite

        @property
        def replaced_sprite(self):
            return self._replaced_sprite

        @property
        def replaced_parallax_sprite(self):
            return self._replaced_parallax_sprite

        @property
        def is_replaced_sprite(self):
            return (self._replaced_sprite is not None or
                    self._replaced_parallax_sprite is not None)

        def set_align(self, x=None, y=None):
            if x is None:
                # x = renpy.random.uniform(0.1, 0.9)
                x = renpy.random.choice(Enemy.POSITIONS)
            if y is None:
                y = 0.5

            x = float(x)
            y = float(y)

            self._align = (x, y,)

        def replace_sprite(self, sprite, parallax=False):
            if sprite is None:
                raise FNaSRTypeError("'sprite' не может быть 'NoneType'")
            if parallax:
                if not isinstance(sprite, Parallax) and not ParallaxWrapper.is_wrapped(sprite):
                    raise FNaSRTypeError("'sprite' должен быть 'Parallax', получено: {}".format(type(sprite)))
                self._replaced_parallax_sprite = sprite
            else:
                self._replaced_sprite = sprite

        def restore_sprite(self, parallax=False, all_sprite=False):
            if all_sprite:
                self._replaced_sprite = None
                self._replaced_parallax_sprite = None
            elif parallax:
                self._replaced_parallax_sprite = None
            else:
                self._replaced_sprite = None

    class EnemyManager(object):
        MAIN_GROUP = "FNaSR"

        def __init__(self):
            self._groups = dict()
            self._enemy_tags = dict()
            self._current_group = EnemyManager.MAIN_GROUP
            self._lock = _threading.RLock()

            self.create_group(EnemyManager.MAIN_GROUP)

        @property
        def selected_group(self):
            with self._lock:
                return self._current_group

        @property
        def iter_current_group(self):
            with self._lock:
                return self.iter_group(self._current_group)

        def create_group(self, group):
            self._validate_name_group(group)

            with self._lock:
                if group in self._groups:
                    raise FNaSRValueError("Группа '{}' уже существует.".format(group))

                self._groups[group] = set()

        def delete_group(self, group):
            self._validate_name_group(group)

            if group == EnemyManager.MAIN_GROUP:
                raise FNaSRValueError("Нельзя удалить группу '{}'.".format(EnemyManager.MAIN_GROUP))

            if group == self._current_group:
                raise FNaSRValueError("Нельзя удалить выбранную группу '{}'.".format(group))

            with self._lock:
                if group not in self._groups:
                    raise FNaSRValueError("Группа '{}' не существует.".format(group))

                cycle = require_system("cycle")
                enemies = tuple(self._groups[group])

                for enemy in enemies:
                    if cycle.is_registered(enemy):
                        cycle.unregister(enemy)
                    self._enemy_tags.pop(enemy.tag, None)

                del self._groups[group]

        def has_group(self, group):
            with self._lock:
                return group in self._groups

        def select_group(self, group):
            self._validate_name_group(group)

            with self._lock:
                if group not in self._groups:
                    raise FNaSRValueError("Группа '{}' не существует.".format(group))

                if group == self._current_group:
                    return

                if is_initialized():
                    raise FNaSRException("Нельзя менять группу после инициализации мода.")

                self._current_group = group

        def iter_group(self, group):
            self._validate_name_group(group)

            with self._lock:
                if group not in self._groups:
                    raise FNaSRValueError("Группа '{}' не существует.".format(group))

                enemies = tuple(self._groups[group])

            return iter(enemies)


        def create_enemy(self, *args, **kwargs):
            group = kwargs.pop("group", EnemyManager.MAIN_GROUP)
            enemy = Enemy(*args, **kwargs)
            self.register(enemy, group)
            return enemy

        def register(self, enemy, group=None, register_in_cycle=True):
            if group is None:
                group = EnemyManager.MAIN_GROUP
            self._validate_name_group(group)

            if not isinstance(enemy, Enemy):
                raise FNaSRTypeError("'enemy' должен быть 'Enemy', получено: {}".format(type(enemy)))

            with self._lock:
                if group not in self._groups:
                    raise FNaSRValueError("Группа '{}' не существует.".format(group))

                if enemy.tag in self._enemy_tags:
                    raise FNaSRValueError("Тег '{}' уже занят.".format(enemy.tag))

                if register_in_cycle:
                    cycle = require_system("cycle")
                    if not cycle.is_registered(enemy):
                        cycle.register(enemy)

                self._groups[group].add(enemy)
                self._enemy_tags[enemy.tag] = group

        def unregister(self, enemy_or_tag):
            if isinstance(enemy_or_tag, Enemy):
                tag = enemy_or_tag.tag
            elif is_string(enemy_or_tag):
                tag = enemy_or_tag
            else:
                raise FNaSRTypeError("'enemy_or_tag' должен быть строкой или 'Enemy', получено: {}".format(type(enemy_or_tag)))

            with self._lock:
                if tag not in self._enemy_tags:
                    raise FNaSRValueError("Противника с тегом '{}' не найдено.".format(tag))

                cycle = require_system("cycle")
                group = self._enemy_tags[tag]
                for enemy in self.iter_group(group):
                    if enemy.tag == tag:
                        if isinstance(enemy_or_tag, Enemy) and enemy is not enemy_or_tag:
                            raise FNaSRValueError("Переданный объект не является зарегистрированным противником.")
                        if cycle.is_registered(enemy):
                            cycle.unregister(enemy)
                        self._groups[group].discard(enemy)
                        del self._enemy_tags[tag]
                        break

        def has_enemy(self, tag):
            with self._lock:
                return tag in self._enemy_tags

        def get_enemy_group(self, tag):
            if not is_string(tag):
                raise FNaSRTypeError("Тег противника должен быть строкой, получено: {}".format(tag))
            with self._lock:
                if not tag in self._enemy_tags:
                    raise FNaSRValueError("Противник с тегом '{}' не найден.".format(tag))
                return self._enemy_tags[tag]

        def _validate_name_group(self, group):
            if not is_string(group):
                raise FNaSRTypeError("Имя группы должно быть строкой, получено: {}".format(type(group)))

    register_system("enemy", EnemyManager())
