# location.rpy
init python in v1FNaSR:

    # ------------------------------------------------------------------
    # Направления
    #
    #   8  1  2        1 — север         5 — юг
    #   7  +  3        2 — северо-восток 6 — юго-запад
    #   6  5  4        3 — восток        7 — запад
    #                  4 — юго-восток    8 — северо-запад
    #
    # Противоположное направление вычисляется, а не хранится в таблице.
    # ------------------------------------------------------------------
    DIRECTION_NORTH = 1
    DIRECTION_NORTH_EAST = 2
    DIRECTION_EAST = 3
    DIRECTION_SOUTH_EAST = 4
    DIRECTION_SOUTH = 5
    DIRECTION_SOUTH_WEST = 6
    DIRECTION_WEST = 7
    DIRECTION_NORTH_WEST = 8

    DIRECTION_MIN = DIRECTION_NORTH
    DIRECTION_MAX = DIRECTION_NORTH_WEST
    DIRECTION_COUNT = DIRECTION_MAX - DIRECTION_MIN + 1
    _DIRECTION_HALF_TURN = DIRECTION_COUNT // 2


    def is_valid_direction(direction):
        """True, если direction — настоящий 'int' (не 'bool') в диапазоне 1..8."""
        return is_strict_integer(direction) and DIRECTION_MIN <= direction <= DIRECTION_MAX


    def get_opposite_direction(direction):
        """
        Возвращает противоположное направление (разворот на 180°).
        1 <-> 5, 2 <-> 6, 3 <-> 7, 4 <-> 8.
        """
        if not is_strict_integer(direction):
            raise FNaSRTypeError("Направление должно быть 'int', а не '{}'.".format(type(direction)))
        if not DIRECTION_MIN <= direction <= DIRECTION_MAX:
            raise FNaSRException(
                "Направление должно быть в диапазоне {}..{}, получено {!r}.".format(
                    DIRECTION_MIN, DIRECTION_MAX, direction
                )
            )
        return ((direction + _DIRECTION_HALF_TURN - 1) % DIRECTION_COUNT) + 1


    # ------------------------------------------------------------------
    # Нормализация и валидация связей
    # ------------------------------------------------------------------
    def _normalize_id(value):
        if not is_strict_integer(value):
            raise FNaSRTypeError(
                "ID локации должен быть 'int' (не 'bool'), а не '{}': {!r}.".format(type(value), value)
            )
        return int(value)


    def _normalize_direction(value):
        if not is_strict_integer(value):
            raise FNaSRTypeError(
                "Направление должно быть 'int' (не 'bool'), а не '{}': {!r}.".format(type(value), value)
            )
        value = int(value)
        if not is_valid_direction(value):
            raise FNaSRException(
                "Направление должно быть в диапазоне {}..{}, получено {!r}.".format(
                    DIRECTION_MIN, DIRECTION_MAX, value
                )
            )
        return value


    def _normalize_pair(location_id, direction, owner_id=None):
        """
        Проверяет и приводит связь к виду (location_id, direction) из двух 'int'.
        Если передан owner_id — связь локации с самой собой запрещена.
        """
        location_id = _normalize_id(location_id)
        direction = _normalize_direction(direction)
        if owner_id is not None and location_id == owner_id:
            raise FNaSRException("Локация '{}' не может быть связана сама с собой.".format(owner_id))
        return (location_id, direction)


    def _split_item(item):
        """Разбирает один элемент loc_connections: 'list'/'tuple' ровно из двух значений."""
        if not isinstance(item, (list, tuple)):
            raise FNaSRTypeError(
                "Связь должна быть парой [[location_id, direction] ('list' или 'tuple'), "
                "а не '{}'".format(type(item))
            )
        if len(item) != 2:
            raise FNaSRException(
                "Связь должна состоять ровно из двух элементов [[location_id, direction], "
                "получено элементов: {} ({!r}).".format(len(item), item)
            )
        return item[0], item[1]


    def _normalize_connections(connections, owner_id):
        """
        Приводит параметр 'loc_connections' к нормализованному dict {location_id: direction}.

        Формат входа: [[location_id, direction], ...] (или кортежи) либо None.
        Каждый location_id может встретиться не более одного раза — в том числе
        с тем же самым направлением: дубль считается ошибкой данных.
        """
        if connections is None:
            return {}
        if isinstance(connections, bool):
            raise FNaSRTypeError("Параметр 'connections' не может быть 'bool'.")
        if is_string(connections):
            raise FNaSRTypeError("Параметр 'connections' не может быть строкой.")
        if isinstance(connections, dict):
            raise FNaSRTypeError(
                "Параметр 'connections' должен быть списком пар [[[[location_id, direction], ...], а не 'dict'."
            )
        if not isinstance(connections, Iterable):
            raise FNaSRTypeError(
                "Параметр 'connections' должен быть 'Iterable' пар или 'NoneType', "
                "а не '{}'.".format(type(connections))
            )

        result = {}
        for item in connections:
            try:
                raw_id, raw_direction = _split_item(item)
            except Exception as e:
                raise FNaSRException("Ошибка в локации '{}': {}".format(owner_id, e))
            location_id, direction = _normalize_pair(raw_id, raw_direction, owner_id)
            if location_id in result:
                raise FNaSRException(
                    "Локация '{}' указана в связях локации '{}' более одного раза "
                    "(направления {} и {}): для одной локации допустима только одна связь.".format(
                        location_id, owner_id, result[location_id], direction
                    )
                )
            result[location_id] = direction
        return result


    def _format_map(mapping):
        """Детерминированное представление {id: direction} для repr"""
        return "{%s}" % ", ".join("%d: %d" % pair for pair in sorted(iter_items(mapping)))


    class _LocationConnections(object):
        """
        Контейнер связей локации с другими локациями.

        Связь — пара (location_id, direction), где direction — направление, в котором
        относительно ВЛАДЕЛЬЦА находится связанная локация (1 — север ... 8 — северо-запад).

        Внутреннее хранение — два словаря {location_id: direction}:
            * _explicit — связи, заданные явно: {target_id: direction},
                            «target находится в направлении direction от меня»;
            * _auto     — обратные связи, выводимые системой: {source_id: opposite_direction},
                            «source ссылается на меня в направлении d, значит он находится
                            в направлении, противоположном d».

        Инварианты (соблюдаются во всех состояниях, а не предполагаются от вызывающего кода):
            1. Один location_id — максимум одно направление: это свойство самого dict.
            2. Ключи _explicit и _auto не пересекаются: если связь объявлена явно, auto для
                того же location_id не хранится. Поэтому «полный» список связей — это
                объединение непересекающихся словарей и в нём нет ни дублей, ни противоречий.
            3. Явная связь не противоречит выводимой из явных связей других локаций
                (это проверяет LocationSystem.generate_connections()).
            4. Связи с самой собой нет.

        Разделение explicit/auto необходимо, чтобы при удалении явной связи система могла
        корректно пересчитать автоматические, а не оставлять "зависшие" связи.

        ВНИМАНИЕ: `_explicit`/`_auto` и `_purge_target` используются напрямую из
        `LocationSystem` — это осознанное решение, классы образуют единый, тесно
        связанный модуль, а не публичный API.
        """

        __slots__ = ("_loc", "_explicit", "_auto")

        def __init__(self, loc, connections):
            self._loc = loc
            self._explicit = _normalize_connections(connections, loc.id)
            self._auto = {}

        @property
        def main_location(self):
            return self._loc

        @property
        def explicit(self):
            """Снимок явных связей: frozenset пар (location_id, direction)."""
            return frozenset(iter_items(self._explicit))

        @property
        def auto(self):
            """Снимок автоматических связей: frozenset пар (location_id, direction)."""
            return frozenset(iter_items(self._auto))

        def get_direction(self, location_id, default=None):
            """Направление связи с location_id (explicit или auto) либо default, если связи нет."""
            if not is_strict_integer(location_id):
                return default
            location_id = int(location_id)
            if location_id in self._explicit:
                return self._explicit[location_id]
            return self._auto.get(location_id, default)

        def _add_auto(self, location_id, direction):
            """
            Добавление автоматической (обратной) связи. Пересчёт графа не запускает.

            Защищает инварианты: не даёт создать auto-связь, дублирующую или
            противоречащую явной, и не даёт записать второе направление для того же ID.
            """
            location_id, direction = _normalize_pair(location_id, direction, self._loc.id)

            declared = self._explicit.get(location_id)
            if declared is not None:
                if declared != direction:
                    raise FNaSRException(
                        "Явная связь локации '{}' с '{}' (направление {}) противоречит "
                        "выведенной автоматически (направление {}).".format(
                            self._loc.id, location_id, declared, direction
                        )
                    )
                return

            existing = self._auto.get(location_id)
            if existing is not None and existing != direction:
                raise FNaSRException(
                    "Локация '{}' уже имеет автоматическую связь с '{}' (направление {}), "
                    "новое направление {} конфликтует.".format(self._loc.id, location_id, existing, direction)
                )
            self._auto[location_id] = direction

        def _reset_auto(self):
            """Сброс автоматических связей перед пересчётом графа."""
            self._auto.clear()

        def _purge_target(self, location_id):
            """
            Удаляет связь с location_id из explicit и auto (по ID: локация исчезает целиком,
            и её направление больше ничего не значит).
            """
            self._explicit.pop(location_id, None)
            self._auto.pop(location_id, None)

        def add(self, location_id, direction):
            """
            Явное добавление связи с последующим пересчётом графа системы.

            Если явная связь с location_id уже есть — FNaSRException (даже с тем же
            направлением): это ошибка в логике вызывающего кода. Сменить направление
            можно так: discard(location_id), затем add(location_id, new_direction).

            Если новая связь противоречит связям других локаций, пересчёт бросит
            FNaSRException, а добавление будет откатено.
            """
            location_id, direction = self._validate_pair(location_id, direction)

            existing = self._explicit.get(location_id)
            if existing is not None:
                raise FNaSRException(
                    "Локация '{}' уже имеет явную связь с '{}' (направление {}). "
                    "Для смены направления сначала вызовите discard({}).".format(
                        self._loc.id, location_id, existing, location_id
                    )
                )

            self._explicit[location_id] = direction
            try:
                self._regenerate()
            except Exception:
                del self._explicit[location_id]
                raise

        def remove(self, location_id):
            """
            Явное удаление связи по location_id. Бросает FNaSRKeyError, если явной связи нет.
            """
            location_id = self._validate_id(location_id)
            if location_id not in self._explicit:
                if location_id in self._auto:
                    raise FNaSRKeyError(
                        "Связь локации '{}' с '{}' автоматическая; она исчезнет сама, "
                        "когда будет удалена явная связь на стороне '{}'.".format(
                            self._loc.id, location_id, location_id
                        )
                    )
                raise FNaSRKeyError(
                    "Связь с id '{}' отсутствует у локации '{}'.".format(location_id, self._loc.id)
                )
            del self._explicit[location_id]
            self._regenerate()

        def discard(self, location_id):
            """Безопасное удаление явной связи по location_id (ничего не делает, если её нет)."""
            location_id = self._validate_id(location_id)
            if location_id in self._explicit:
                del self._explicit[location_id]
                self._regenerate()

        def _regenerate(self):
            loc_sys = self._loc.location_system
            if loc_sys is not None:
                loc_sys.generate_connections()

        def _validate_id(self, value):
            return _normalize_id(value)

        def _validate_pair(self, location_id, direction):
            return _normalize_pair(location_id, direction, self._loc.id)

        def _merged(self):
            merged = dict(self._auto)
            merged.update(self._explicit)
            return merged

        def __len__(self):
            return len(self._merged())

        def __contains__(self, location_id):
            """
            `2 in connections` — есть ли связь (явная или автоматическая) с location_id=2.

            Ключ связи — location_id, поэтому проверка идёт по ID, а не по паре.
            Не бросает исключений: всё, что не является настоящим 'int' (строки, bool,
            кортежи), просто не содержится. Направление узнаётся через get_direction().
            """
            if not is_strict_integer(location_id):
                return False
            location_id = int(location_id)
            return location_id in self._explicit or location_id in self._auto

        def __iter__(self):
            return iter(self.to_list())

        def to_list(self):
            """Все связи (explicit + auto), отсортированные по ID: [(location_id, direction), ...]."""
            return sorted(iter_items(self._merged()))

        def __repr__(self):
            return "_LocationConnections(explicit=%s, auto=%s)" % (
                _format_map(self._explicit), _format_map(self._auto)
            )


    class Location(object):
        __slots__ = (
            "_id", "_name", "_image", "_loc_connections",
            "_tablet", "_ambient", "_camera", "_loc_sys",
            "_parallax_image", "_door", "_bulb", "_on_enter_fn"
        )

        def __init__(self, location_id, name, image, loc_connections=None, ambient=None, door=None, bulb=None, on_enter_fn=None):
            if door is not None and not isinstance(door, Door):
                raise FNaSRTypeError("'door' должен быть объектом класса 'Door', передано: {}".format(type(door)))
            if bulb is not None and not isinstance(bulb, Bulb):
                raise FNaSRTypeError("'bulb' должен быть объектом класса 'Bulb', передано: {}".format(type(bulb)))
            if on_enter_fn is not None and not callable(on_enter_fn):
                raise FNaSRTypeError("'on_enter_fn' должен быть вызываемым объектом, передано: {}".format(type(on_enter_fn)))

            self._id = int(location_id)
            self._name = to_text(name)
            self._image = image
            self._parallax_image = Parallax(
                image,
                1.15,     # итоговый zoom: прежний zoom * 1.1, который давал camera
                None,    # anchor: None -> центр области
                0.07,    # power
                sharpness_factor=0.1,
                fill_viewport=True
            )
            self._tablet = None
            self._ambient = ambient
            self._door = door
            self._bulb = bulb
            self._on_enter_fn = on_enter_fn
            self._camera = None
            self._loc_sys = None
            self._loc_connections = _LocationConnections(self, loc_connections)
            self._camera_button = None

        @property
        def location_system(self):
            return self._loc_sys

        @property
        def id(self):
            return self._id

        @property
        def name(self):
            return self._name

        @property
        def image(self):
            if self._bulb is not None and not self._bulb.is_on:
                return self._bulb.dark_image
            return self._image

        @property
        def parallax_image(self):
            if self._bulb is not None and not self._bulb.is_on:
                self._parallax_image.set_displayable(self._bulb.dark_image)
            else:
                self._parallax_image.set_displayable(self._image)
            return self._parallax_image

        @property
        def ambient(self):
            return self._ambient

        @property
        def connections(self):
            """Полный список связей [(location_id, direction), ...]: явные + автоматические."""
            return self._loc_connections.to_list()

        @property
        def explicit_connections(self):
            """Только явно заданные связи [(location_id, direction), ...], без автоматических."""
            return sorted(self._loc_connections.explicit)

        @property
        def camera(self):
            return self._camera

        @property
        def tablet(self):
            return self._tablet

        @property
        def door(self):
            return self._door
        
        @property
        def bulb(self):
            return self._bulb

        @property
        def ui_camera_button(self):
            return self._camera_button

        def on_enter(self, entity):
            if self._on_enter_fn is None:
                return
            return self._on_enter_fn(self, entity)

        def set_camera(self, camera_info):
            if not isinstance(camera_info, CameraInfo):
                raise FNaSRTypeError(
                    "camera_info должен быть объектом класса 'CameraInfo', а не '{}'".format(type(camera_info))
                )
            self._camera = camera_info

        def _attach_tablet(self, tablet):
            self._tablet = tablet

        def _detach_tablet(self):
            self._tablet = None

        def create_camera_button(self, tablet, recreate=False):
            if not recreate and self._camera_button is not None:
                return

            if not isinstance(tablet, Tablet):
                raise FNaSRTypeError("tablet должен быть 'Tablet', пришло: {}".format(type(tablet)))

            if self._camera is None:
                raise FNaSRValueError("Невозможно создать кнопку пакеры так как камера не задана")

            viewport = ViewportManager.current()

            v1_camera_map_idle_t = renpy.store.Transform(
                InitImages.camera_map.cam_idle,
                xalign=0.5,
                yalign=0.5
            )

            v1_camera_map_hover_t = renpy.store.Transform(
                InitImages.camera_map.cam_hover,
                xalign=0.5,
                yalign=0.5
            )
            
            cam_text = renpy.store.Text(
                text=to_text(self._camera.num),
                size=int(viewport.scale_scalar(11)),
                font=resources.fonts["FiveFontsatFreddy's-Regular"],
                xalign=0.28 if len(self._camera.num) == 2 else 0.23,
                yalign=1.0
            )

            cam_button = renpy.store.Button(
                child=cam_text,
                idle_background=v1_camera_map_idle_t,
                hover_background=v1_camera_map_hover_t,
                align=(self._camera.align[0], self._camera.align[1]),
                xsize=int(viewport.scale_scalar(70)),
                ysize=int(viewport.scale_scalar(50)),
                action=(renpy.store.Function(tablet.select, self._id), renpy.store.Function(tablet.safe_discharge, 1))
            )

            if self._camera.rotate:
                cam_button = renpy.store.At(cam_button, renpy.store.v1_cam_rotate_t_FNaSR(self._camera.rotate or 0))

            self._camera_button = cam_button

        def __repr__(self):
            return "Location(id=%r, name=%r, connections=%r)" % (
                self._id, self._name, self._loc_connections.to_list()
            )


    class LocationSystem(object):
        __slots__ = ("_locations",)

        def __init__(self):
            self._locations = dict()

        @property
        def locations(self):
            return dict(self._locations)

        def get_location(self, location_id):
            return self._locations.get(int(location_id))

        def require_location(self, location_id):
            location = self._locations.get(int(location_id))
            if location is None:
                raise FNaSRKeyError("Локация с id '{}' не зарегистрирована.".format(location_id))
            return location

        def has_location(self, location_id):
            return int(location_id) in self._locations

        def _validate_registration(self, location, overwrite):
            if not isinstance(location, Location):
                raise FNaSRTypeError("location должен быть 'Location', а не '{}'".format(type(location)))
            if not overwrite and location.id in self._locations:
                raise FNaSRException("Локация с id '{}' уже существует".format(location.id))

        def _attach(self, location, overwrite):
            self._validate_registration(location, overwrite)

            old = self._locations.get(location.id) if overwrite else None
            if old is not None:
                if old._tablet is not None:
                    raise FNaSRException("В локации '{}' есть планшет, нельзя перезаписывать локации с планшетом".format(old.id))
                old._loc_sys = None
                old._loc_connections._reset_auto()

            location._loc_sys = self
            self._locations[location.id] = location

        def _restore_registry(self, backup, touched):
            for location in touched:
                if isinstance(location, Location):
                    location._loc_sys = None
                    location._loc_connections._reset_auto()

            self._locations.clear()
            self._locations.update(backup)
            for location in iter_values(self._locations):
                location._loc_sys = self

            self.generate_connections()

        def register(self, location, overwrite=False, _regenerate=True):
            if not _regenerate:
                self._attach(location, overwrite)
                return
            self.register_many([location], overwrite=overwrite)

        def register_many(self, locations, overwrite=False):
            locations = list(locations)
            backup = dict(self._locations)
            try:
                for location in locations:
                    self._attach(location, overwrite)
                self.generate_connections()
            except Exception:
                self._restore_registry(backup, locations)
                raise

        def unregister(self, location_id):
            location_id = int(location_id)
            if location_id not in self._locations:
                raise FNaSRKeyError("Локация с id '{}' не зарегистрирована".format(location_id))

            location = self._locations[location_id]
            if location.tablet is not None:
                raise FNaSRException(
                    "Локация '{}' ещё содержит планшет '{}'; сначала переместите "
                    "или удалите его через TabletManager".format(location_id, location.tablet.tag)
                )

            removed = self._locations.pop(location_id)
            removed._loc_sys = None
            removed._loc_connections._reset_auto()

            for loc in iter_values(self._locations):
                loc._loc_connections._purge_target(location_id)

            self.generate_connections()

        def generate_connections(self):
            locations = self._locations

            computed = {}
            for loc_id in iter_keys(locations):
                computed[loc_id] = {}

            for source in iter_values(locations):
                for target_id, direction in iter_items(source._loc_connections._explicit):
                    target = locations.get(target_id)
                    if target is None:
                        continue

                    reverse = get_opposite_direction(direction)
                    declared = target._loc_connections._explicit.get(source.id)
                    if declared is not None:
                        if declared != reverse:
                            raise FNaSRException(
                                "Противоречие направлений: локация '{}' считает '{}' направлением {}, "
                                "поэтому '{}' должна указывать на '{}' направлением {}, "
                                "а указывает направлением {}.".format(
                                    source.id, target_id, direction,
                                    target_id, source.id, reverse, declared
                                )
                            )
                        continue

                    computed[target_id][source.id] = reverse

            for loc_id, auto in iter_items(computed):
                connections = locations[loc_id]._loc_connections
                connections._reset_auto()
                for source_id, reverse in iter_items(auto):
                    connections._add_auto(source_id, reverse)

        def __iter__(self):
            return iter(iter_values(dict(self._locations)))

    register_system("location", LocationSystem())

init python in v1FNaSR:
    def _v1_location_info_FNaSR(context):
        location = context.ps.current_player.current_location
        info = [
            "Имя: {}".format(location.name),
            "Связи: {}".format(location.connections),
            "Явные связи: {}".format(location.explicit_connections),
            "Сгенерированные связи: {}".format([loc_conn_data for loc_conn_data in location.connections if loc_conn_data not in location.explicit_connections]),
            "Всего локаций: {}".format(len(location.location_system.locations))
        ]
        if location.bulb:
            info.append("Свет: {}".format("{color=#0ac80a}включен{/color}" if location.bulb.is_on else "{color=#c80a0a}выключен{/color}"))
        return "\n".join(info)

    _dsp = DebugSection(
        DebugText(lambda context: "Локация: {}".format(context.ps.current_player.current_location.id), order=0, style="v1_text_16_style_FNaSR"),
        DebugText(_v1_location_info_FNaSR, order=1),
    order=0)

    _dsp.context.ps = require_system("player")

    debug.add_element(_dsp, group="Location")

    del _v1_location_info_FNaSR
    del _dsp






