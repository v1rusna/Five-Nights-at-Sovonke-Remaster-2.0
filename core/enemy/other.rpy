# other
init -5 python in v1FNaSR:
    import collections as _collections
    import random as _random

    class EnemyContext(DebugContext):
        __slots__ = ("_enemy",)

        def __init__(self, enemy):
            if not isinstance(enemy, BaseEnemy):
                raise FNaSRTypeError("'enemy' должен быть 'BaseEnemy', получено: {}".format(type(enemy)))

            super(EnemyContext, self).__init__()
            object.__setattr__(self, "_enemy", enemy)

        @property
        def enemy(self):
            return self._enemy

        def __setattr__(self, name, value):
            if name == "_enemy":
                object.__setattr__(self, name, value)
            else:
                super(EnemyContext, self).__setattr__(name, value)

    # Пока что генератор игнорирует направления, но в будущем можно избавится от хранения пути у противника
    # Например если игрок защитился то противник отступает на n локаций назад
    # то есть если игрок на севере, то отступить на 2 локации на юг, или юго-запад, или юго-восток и так далее
    class PathGenerator(object):
        _location_system = None
        _player_manager = None

        @classmethod
        def _get_location_system(cls):
            if cls._location_system is None:
                cls._location_system = get_system("location")

            return cls._location_system

        @classmethod
        def _get_player_manager(cls):
            if cls._player_manager is None:
                cls._player_manager = get_system("player")

            return cls._player_manager

        @staticmethod
        def _snapshot_graph(locations):
            """Создаёт снимок графа: {location_id: ((neighbor_id, direction), ...)}."""
            return dict(
                (location_id, tuple(location.connections))
                for location_id, location in iter_items(locations)
            )

        @classmethod
        def generate_path(cls, start_location_id=None, end_location_id=None):
            """
            Строит путь от заданной локации до цели.

            Если start_location_id не указан, выбирает случайную точку
            появления и строит путь от неё до цели.

            Если end_location_id не указан, целью становится текущая
            локация игрока.

            Возвращает список ID локаций или None, если путь не найден.
            """
            if start_location_id is None:
                return cls.generate_spawn_path(end_location_id)

            location_system = cls._get_location_system()
            start_location_id = _normalize_id(start_location_id)

            if end_location_id is None:
                player_manager = cls._get_player_manager()
                end_location_id = player_manager.current_player.current_location.id

            end_location_id = _normalize_id(end_location_id)

            with _LOCATION_LOCK:
                location_system.require_location(start_location_id)
                location_system.require_location(end_location_id)

                locations = location_system.locations
                graph = cls._snapshot_graph(locations)

            return cls.find_path(
                start_location_id,
                end_location_id,
                graph
            )

        @classmethod
        def generate_spawn_path(cls, end_location_id=None, distance_group_count=3):
            """
            Выбирает случайную точку из нескольких самых дальних групп
            расстояний и строит путь до целевой локации.

            Если цель не указана, используется текущая локация игрока.

            Возвращает список ID локаций или None, если нет подходящей точки.
            """
            if not is_strict_integer(distance_group_count) or distance_group_count < 1:
                raise FNaSRValueError("'distance_group_count' должен быть положительным int.")

            location_system = cls._get_location_system()

            if end_location_id is None:
                player_manager = cls._get_player_manager()
                end_location_id = player_manager.current_player.current_location.id

            end_location_id = _normalize_id(end_location_id)

            with _LOCATION_LOCK:
                location_system.require_location(end_location_id)

                locations = location_system.locations
                graph = cls._snapshot_graph(locations)

            distances = cls.location_distances(end_location_id, graph)
            distance_groups = cls.group_by_distance(distances)

            farthest_distances = sorted(
                distance_groups.keys(),
                reverse=True
            )[:distance_group_count]

            spawn_candidates = []

            for distance in farthest_distances:
                for location_id in distance_groups[distance]:
                    if location_id != end_location_id:
                        spawn_candidates.append(location_id)

            if not spawn_candidates:
                return None

            spawn_location_id = _random.choice(spawn_candidates)

            return cls.find_path(
                spawn_location_id,
                end_location_id,
                graph
            )

        @staticmethod
        def find_path(start_id, target_id, graph):
            """BFS. Возвращает кратчайший путь по числу переходов или None."""
            if start_id not in graph or target_id not in graph:
                return None

            if start_id == target_id:
                return [start_id]

            # Для каждой посещённой локации запоминаем предшественника.
            previous = {start_id: None}
            queue = _collections.deque([start_id])

            while queue:
                current = queue.popleft()

                for next_id, _ in graph[current]:
                    # Пропускаем отсутствующие вершины и уже посещённые.
                    if next_id not in graph or next_id in previous:
                        continue

                    previous[next_id] = current

                    if next_id == target_id:
                        path = []
                        node = target_id

                        while node is not None:
                            path.append(node)
                            node = previous[node]

                        path.reverse()
                        return path

                    queue.append(next_id)

            return None

        @staticmethod
        def location_distances(start_id, graph):
            """Возвращает {location_id: расстояние от start_id}."""
            if start_id not in graph:
                return {}

            distances = {start_id: 0}
            queue = _collections.deque([start_id])

            while queue:
                current = queue.popleft()
                next_distance = distances[current] + 1

                for next_id, _ in graph[current]:
                    if next_id not in graph or next_id in distances:
                        continue

                    distances[next_id] = next_distance
                    queue.append(next_id)

            return distances

        @staticmethod
        def group_by_distance(distances):
            """Группирует ID локаций по расстоянию."""
            grouped = {}

            for location_id, distance in iter_items(distances):
                grouped.setdefault(distance, []).append(location_id)

            return grouped

    class EnemyScreamer(object):
        _CAMERA_LAYER = "master"
        _OVERLAY_LAYER = "screens"
        _SOUND_CHANNEL = "screamer"

        _FADE_NAME = "v1_black_fade_FNaSR"
        _FADE_ZORDER = 49
        _SPRITE_ZORDER = 50

        _SCREAMER_DURATION = 2
        _BLACKOUT_DURATION = 1

        def __init__(
            self,
            sprite,
            sound_screamer=None,
            screamer_t=None,
            camera_t=None,
            bg_t=None,
            is_screen_t=False,
            is_black_fade=False
        ):
            if sound_screamer is None:
                sound_screamer = resources.sounds.sfx["enemy_screamer_1"]

            if screamer_t is None:
                screamer_t = renpy.store.v1_slavya_screamer_t_FNaSR

            if camera_t is None:
                camera_t = renpy.store.v1_general_screamer_camera_t_FNaSR

            if bg_t is None:
                bg_t = renpy.store.v1_fading_t_FNaSR(0.8, 0.0, 0.85, renpy.store._warper.easein_quad)

            self._sprite = sprite
            self._sound_screamer = sound_screamer

            self._screamer_t = screamer_t
            self._camera_t = camera_t
            self._bg_t = bg_t
            self._is_screen_t = bool(is_screen_t)
            self._is_black_fade = bool(is_black_fade)

        @main_thread_only
        def __call__(self):
            image_name = "v1_animation_enemy_screamer_FNaSR"

            audio.play(self._sound_screamer, self._SOUND_CHANNEL)

            try:
                self._show_effects(image_name)
                renpy.block_rollback()
                renpy.pause(self._SCREAMER_DURATION, hard=True)
            finally:
                self._hide_effects(image_name)

            self._show_blackout()

        def _show_effects(self, image_name):
            if self._is_black_fade:
                renpy.show(
                    name=self._FADE_NAME,
                    at_list=[self._bg_t()],
                    layer=self._OVERLAY_LAYER,
                    what=renpy.store.Solid("#000"),
                    zorder=self._FADE_ZORDER
                )

            renpy.show(
                name=image_name,
                at_list=[self._screamer_t],
                layer=self._OVERLAY_LAYER,
                what=self._sprite,
                zorder=self._SPRITE_ZORDER
            )

            self._set_camera([self._camera_t])

        def _hide_effects(self, image_name):
            if self._is_black_fade:
                renpy.hide(self._FADE_NAME, self._OVERLAY_LAYER)

            renpy.hide(image_name, self._OVERLAY_LAYER)

            self._set_camera([])

        def _set_camera(self, at_list):
            renpy.show_layer_at(
                at_list=at_list,
                layer=self._CAMERA_LAYER,
                reset=False,
                camera=True
            )

            if self._is_screen_t:
                renpy.show_layer_at(
                    at_list=at_list,
                    layer=self._OVERLAY_LAYER,
                    reset=False,
                    camera=True
                )

        def _show_blackout(self):
            renpy.show("black")
            renpy.block_rollback()
            renpy.pause(self._BLACKOUT_DURATION, hard=True)


init python:
    v1FNaSR.audio.register_channel("screamer", "sound", loop=False)


