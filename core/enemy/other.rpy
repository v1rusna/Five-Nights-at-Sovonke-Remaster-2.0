init -5 python in v1FNaSR:
    import collections as _collections
    import random as _random

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
            if not is_strict_integer(distance_group_count)or distance_group_count < 1:
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
