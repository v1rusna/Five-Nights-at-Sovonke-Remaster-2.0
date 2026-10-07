init python in v1FNaSR:
    class LocationCreateHook(BaseHook):
        def init(self):
            def _on_enter_escape(self, entity):
                if isinstance(entity, Player):
                    require_system("night").finish(False)
                    renpy.jump("v1_quit_FNaSR")

            self._locations = [
                # Локации с камерой.
                (
                    {
                        "location_id": 1,
                        "name": "площадь",
                        "image": "anim v1_ext_square_night_party_anim_FNaSR",
                        "loc_connections": [(2,2), (7,4), (9,7), (13,5), (14, 7), (17,6), (18,8)],
                    },
                    CameraInfo(1, (0.491, 0.411)),
                ),
                (
                    {
                        "location_id": 2,
                        "name": "медпункт",
                        "image": resources.images.bg["v1_ext_aidpost_night_FNaSR"],
                        "loc_connections": [(1,6), (3,2), (4,8), (18,7), (-9,1)],
                    },
                    CameraInfo(2, (0.528, 0.281), -57),
                ),
                (
                    {
                        "location_id": 3,
                        "name": "библиотека",
                        "image": resources.images.bg["v1_ext_library_night_FNaSR"],
                        "loc_connections": [(2,6), (4,7), (8,1), (18,7), (-8,1)],
                    },
                    CameraInfo(3, (0.6, 0.163), -21),
                ),
                (
                    {
                        "location_id": 4,
                        "name": "треугольный домик",
                        "image": resources.images.bg["v1_ext_house_of_mt_night_FNaSR"],
                        "loc_connections": [(3,3), (2,4), (18,6), (-1,1)],
                    },
                    CameraInfo(4, (0.485, 0.1622)),
                ),
                (
                    {
                        "location_id": 5,
                        "name": "спортплощадка",
                        "image": resources.images.bg["v1_ext_playground_night_FNaSR"],
                        "loc_connections": [(6,7)],
                    },
                    CameraInfo(5, (0.77, 0.475)),
                ),
                (
                    {
                        "location_id": 6,
                        "name": "пляж",
                        "image": resources.images.bg["v1_ext_beach_night_FNaSR"],
                        "loc_connections": [(5,3), (15,7)],
                    },
                    CameraInfo(6, (0.689, 0.511)),
                ),
                (
                    {
                        "location_id": 7,
                        "name": "столовая",
                        "image": resources.images.bg["v1_ext_dining_hall_away_night_FNaSR"],
                        "loc_connections": [(1,8), (13,5), (9,7), (15,3), (17,6), (-2,1)],
                    },
                    CameraInfo(7, (0.526, 0.45), 33, [-2]),
                ),
                (
                    {
                        "location_id": 8,
                        "name": "сцена",
                        "image": resources.images.bg["v1_ext_stage_normal_night_FNaSR"],
                        "loc_connections": [(3,5)],
                    },
                    CameraInfo(8, (0.582, 0.108)),
                ),
                (
                    {
                        "location_id": 9,
                        "name": "кружки",
                        "image": resources.images.bg["v1_ext_clubs_night_FNaSR"],
                        "loc_connections": [(12,7), (10,1), (14,2), (1,3), (7,3), (13,4), (17,5), (-4, 1)],
                    },
                    CameraInfo(9, (0.321, 0.456)),
                ),
                (
                    {
                        "location_id": 10,
                        "name": "муз-клуб",
                        "image": resources.images.bg["v1_ext_musclub_night_FNaSR"],
                        "loc_connections": [(11,1), (9,5), (14,4), (-5,1)],
                    },
                    CameraInfo(10, (0.3433, 0.304), -19),
                ),
                (
                    {
                        "location_id": 11,
                        "name": "лес",
                        "image": resources.images.bg["ext_path_night"],
                        "loc_connections": [(10,5), (-6,1)],
                    },
                    CameraInfo(11, (0.3, 0.174), -16),
                ),
                (
                    {
                        "location_id": 12,
                        "name": "остановка",
                        "image": resources.images.bg["v1_ext_camp_entrance_night_FNaSR"],
                        "loc_connections": [(9,3), (-11,7)],
                    },
                    CameraInfo(12, (0.218, 0.479)),
                ),
                (
                    {
                        "location_id": 13,
                        "name": "лодочная станция",
                        "image": resources.images.bg["v1_ext_boathouse_night_FNaSR"],
                        "loc_connections": [(1,1), (7,1), (9,8), (17,7), (22,5)],
                    },
                    CameraInfo(13, (0.498, 0.655), -7),
                ),
                (
                    {
                        "location_id": 14,
                        "name": "админ-корпус",
                        "image": resources.images.bg["v1_ext_admin_night_FNaSR"],
                        "loc_connections": [(1,3), (9,6), (10,8), (18,1)],
                    },
                    CameraInfo(14, (0.426, 0.37)),
                ),
                (
                    {
                        "location_id": 15,
                        "name": "склады",
                        "image": resources.images.bg["v1_ext_storage_night_FNaSR"],
                        "loc_connections": [(6,3), (7,7)],
                        "ambient": ["electrical_panel", True],
                    },
                    CameraInfo(15, (0.615, 0.445)),
                ),
                (
                    {
                        "location_id": 16,
                        "name": "старый корпус",
                        "image": resources.images.bg["v1_ext_old_building_night_FNaSR"],
                        "loc_connections": [(17,2), (-10,1)],
                    },
                    None # CameraInfo(16, (0.232, 0.955), 7),
                ),
                (
                    {
                        "location_id": 17,
                        "name": "южные домики",
                        "image": resources.images.bg["ext_houses_night"],
                        "loc_connections": [(16,6), (9,1), (1,2), (7,2), (13,3)],
                    },
                    CameraInfo(17, (0.385, 0.61), -42),
                ),
                (
                    {
                        "location_id": 18,
                        "name": "северные домики",
                        "image": resources.images.bg["ext_houses_reverse_night"],
                        "loc_connections": [(4,2), (14,5), (1,4), (2,3), (3,3)],
                    },
                    CameraInfo(18, (0.45, 0.25)),
                ),
                (
                    {
                        "location_id": 19,
                        "name": "o. ближний",
                        "image": resources.images.bg["ext_island_night"],
                        "loc_connections": [(13,1)],
                    },
                    None # CameraInfo(19, (0.45, 0.85), 15),
                ),
                (
                    {
                        "location_id": 20,
                        "name": "баня",
                        "image": resources.images.bg["ext_bathhouse_night"],
                        "loc_connections": [(-6,6)],
                    },
                    CameraInfo(20, (0.35, 0.1)),
                ),

                # Обычные локации.
                (
                    {
                        "location_id": -1,
                        "name": "внутрь тре-ого домика",
                        "image": resources.images.bg["R_int_mt_house_night_light"],
                        "door": Door(),
                        "bulb": Bulb(resources.images.bg["R_int_mt_house_night"]),
                        "loc_connections": [(4,5)],
                    },
                    None,
                ),
                (
                    {
                        "location_id": -2,
                        "name": "крыльцо столовой",
                        "image": resources.images.bg["ext_dining_hall_near_night"],
                        "loc_connections": [(7,5), (-3,1)],
                    },
                    None,
                ),
                (
                    {
                        "location_id": -3,
                        "name": "внутрь столовой",
                        "image": resources.images.bg["int_dining_hall_night"],
                        "door": Door(),
                        "loc_connections": [(-2,5)],
                    },
                    None,
                ),
                (
                    {
                        "location_id": -4,
                        "name": "внутрь кружков",
                        "image": resources.images.bg["int_clubs_male_night_7dl"],
                        "door": Door(),
                        "loc_connections": [(9,5)],
                    },
                    None,
                ),
                (
                    {
                        "location_id": -5,
                        "name": "внутрь муз-клуба",
                        "image": resources.images.bg["int_musclub_night_nolight"],
                        "loc_connections": [(10,5)],
                    },
                    None,
                ),
                (
                    {
                        "location_id": -6,
                        "name": "вглубь леса",
                        "image": resources.images.bg["ext_path2_night"],
                        "loc_connections": [(11,5), (-7,8), (20,2)],
                    },
                    None,
                ),
                (
                    {
                        "location_id": -7,
                        "name": "поляна",
                        "image": resources.images.bg["v1_ext_polyana_night_FNaSR"],
                        "loc_connections": [(-6,4)],
                    },
                    None,
                ),
                (
                    {
                        "location_id": -8,
                        "name": "внутрь библиотеки",
                        "image": resources.images.bg["int_library_night_light"],
                        "door": Door(),
                        "loc_connections": [(3,5)],
                    },
                    None,
                ),
                (
                    {
                        "location_id": -9,
                        "name": "внутрь медпункта",
                        "image": resources.images.bg["int_aidpost_no_light_night_7dl"],
                        "door": Door(),
                        "loc_connections": [(2,5)],
                    },
                    None,
                ),
                (
                    {
                        "location_id": -10,
                        "name": "внутрь старого корпуса",
                        "image": resources.images.bg["int_old_building_night"],
                        "loc_connections": [(16,5)],
                    },
                    None,
                ),
                (
                    {
                        "location_id": -11,
                        "name": "дорога",
                        "image": resources.images.bg["ext_road_night2"],
                        "loc_connections": [(12,3),(-12,1)],
                    },
                    None,
                ),
                (
                    {
                        "location_id": -12,
                        "name": "убежать",
                        "image": "black",
                        "loc_connections": [(-11,5)],
                        "on_enter_fn": _on_enter_escape
                    },
                    None,
                ),
            ]

            self._camp_tablet_location_id = -1

            self._registered = []
            self._camp_tablet = None

        def __call__(self):
            self._registered[:] = []
            self._camp_tablet = None

            location_system = require_system("location")

            tablet_manager = require_system("tablet")

            camp_tablet = tablet_manager.create_tablet("camp")
            self._camp_tablet = camp_tablet

            for location_data, camera in self._locations:
                location = Location(**location_data)

                if camera is not None:
                    location.set_camera(camera)
                    camp_tablet.register(location.id)
                    location.create_camera_button(camp_tablet)

                location_system.register(location, _regenerate=False)

                self._registered.append(location.id)

            location_system.generate_connections()

            tablet_manager.move_tablet(camp_tablet, self._camp_tablet_location_id)
            camp_tablet._setattr("_location_id", self._camp_tablet_location_id)

        def handle_exception(self, exc):
            location_system = get_system("location")

            if location_system is None:
                renpy.log("FNaSR | LocationCreateHook | location_system не был зарегистрирован")
                return

            tablet_manager = get_system("tablet")

            if tablet_manager is not None and self._camp_tablet is not None:
                if tablet_manager.has_tablet(self._camp_tablet.tag):
                    tablet_manager.delete_tablet(self._camp_tablet.tag)

            for location_id in reversed(self._registered):
                if location_system.has_location(location_id):
                    location_system.unregister(location_id)

            self._camp_tablet = None
            self._registered[:] = []

    class NightCreateHook(BaseHook):
        def init(self):
            self._nights = 5
            self._start_location_id = -1
            self._callbacks = {}

        def __call__(self):
            ns = require_system("night")
            for i in range(1, self._nights+1):
                ns.register_night(
                    "night_{}".format(i),
                    title="Night {}".format(i),
                    start_location_id=self._start_location_id,
                    sequence=MAIN_SEQUENCE
                )

            ns.register_night("night_6", title="6th Night", requires="night_5")
            ns.register_night("custom", title="Custom Night", requires="night_6")

        def handle_exception(self, exc):
            renpy.log("FNaSR | NightCreateHook | {}".format(exc))
            ns = get_system("night")
            if ns is None:
                return

            for i in range(1, self._nights+1):
                n = "night_{}".format(i)
                if ns.has_night(n):
                    ns.unregister(n)

    class EnemyCreateHook(BaseHook):
        def init(self):
            self._enemy_list = [
                {
                    "tag": "us",
                    "name": "Ульяна",
                    "sprite": "us angry pioneer",
                    "color": "#FF3200"
                }
            ]

            self._modules = {
                "us": [lambda: EnemyMoveModule((-3, -2, 7, 1, 2, 4, -1))]
            }

        def __call__(self):
            def _debug_text(context):
                enemy = context.enemy
                info = [
                    "name: {}".format(enemy.name),
                    "modules: {}".format(len(enemy.modules)),
                    "sprite: {}".format(enemy.sprite),
                    "nights start: {}".format(enemy.nights_start),
                    "special night: {}".format(enemy.special_night),
                    "current location id: {}".format(enemy.current_location.id),
                    "current location name: {}".format(enemy.current_location.name),
                ]
                return color_text("\n".join(info), enemy.color)

            cycle = require_system("cycle")
            for i, enemy_data in enumerate(self._enemy_list):
                try:
                    enemy = Enemy(**enemy_data)
                    for module in self._modules.get(enemy.tag, []):
                        enemy.add_module(module())
                except Exception:
                    log.error("Ошибка создания врага '{}'".format(enemy_data.get("tag")))
                else:
                    df = DebugFold(color_text(enemy.tag, enemy.color),
                        DebugText(_debug_text),
                    order=i)
                    df.context.enemy = enemy

                    try:
                        cycle.register(enemy)
                    except Exception:
                        log.error("Ошибка регистрации врага '{}'".format(enemy_data.get("tag")))
                    else:
                        debug.add_element(df, group="Enemy")

        def handle_exception(self, exc):
            log("EnemyCreateHook | handle_exception: {}".format(exc))
        

    def _init_other():
        require_system("player").create_player("main")

    add_start_fn(LocationCreateHook(), once=True)
    add_start_fn(NightCreateHook(), once=True)
    add_start_fn(EnemyCreateHook(), once=True)
    add_start_fn(_init_other, once=True)

    del _init_other
