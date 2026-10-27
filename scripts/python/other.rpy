# other.rpy
init -1 python in v1FNaSR:
    import threading as _threading
    from itertools import chain as _chain

    class _ImageStore(object):
        def __init__(self):
            self._lock = _threading.RLock()
            self._items = list()

        @staticmethod
        def normalize_align(align):
            if not isinstance(align, (list, tuple,)):
                raise FNaSRTypeError("'align' должен быть списком или кортежем, получено: {}".format(type(align)))
            if len(align) != 2:
                raise FNaSRValueError("'align' должен состоять из 2 элементов, получено: {}".format(len(align)))
            for i in range(2):
                if not is_number(align[i]):
                    raise FNaSRValueError("align[{}] должен быть числом, получено: {}".format(i, align[i]))
            return tuple(align)

        def snapshot(self):
            with self._lock:
                return tuple(self._items)

        def insert(self, image, align=(0.5, 0.5), index=None):
            align = self.normalize_align(align)
            with self._lock:
                if index is None:
                    index = len(self._items)
                self._items.insert(index, (image, align))

        def insert_if_absent(self, image, align=(0.5, 0.5), index=None):
            align = self.normalize_align(align)
            with self._lock:
                if self.has(image):
                    return
                self.insert(image, align, index)

        def set_align(self, image, align, remove_all=False):
            align = self.normalize_align(align)
            with self._lock:
                for i, (im, _) in enumerate(tuple(self._items)):
                    if image == im:
                        self._items[i] = (im, align)
                        if not remove_all:
                            return

        def remove(self, image, remove_all=False):
            with self._lock:
                for i in range(len(self._items) - 1, -1, -1):
                    if image == self._items[i][0]:
                        del self._items[i]
                        if not remove_all:
                            return

        def has(self, image):
            with self._lock:
                for im, _ in self._items:
                    if image == im:
                        return True
            return False

        def clear(self):
            with self._lock:
                del self._items[:]


    class _VisibilityResolver(object):
        def __init__(self):
            self._em = None
            self._pm = None
            self._player = None

        def reset(self):
            self._em = None
            self._pm = None
            self._player = None

        def _get_enemy_manager(self):
            if self._em is None:
                self._em = require_system("enemy")
            return self._em

        def _get_player_manager(self):
            if self._pm is None:
                self._pm = require_system("player")
            return self._pm

        def _get_player(self):
            if self._player is None:
                self._player = self._get_player_manager().current_player
            return self._player

        def visible_enemies(self):
            player = self._get_player()
            if player is None:
                return tuple()
            current_location = player.current_location
            if current_location is None:
                return tuple()

            is_tablet = player.is_open_tablet
            visible_ids = set()
            if is_tablet:
                selected = current_location.tablet.selected
                if selected is not None:
                    location_selected = current_location.location_system.get_location(selected)
                    if location_selected is not None:
                        visible_ids.add(selected)
                        visible_ids.update(location_selected.camera.identical_ids)

            pairs = list()
            for enemy in self._get_enemy_manager().iter_current_group:
                loc = enemy.current_location
                if loc is None or enemy.is_invisible:
                    continue
                if is_tablet:
                    if loc.id in visible_ids:
                        pairs.append((enemy.sprite, enemy.align))
                elif loc.id == current_location.id:
                    pairs.append((enemy.parallax_sprite, enemy.align))
            return tuple(pairs)

        def visible_images(self, images):
            player = self._get_player()
            if player is None:
                return tuple()
            is_tablet = player.is_open_tablet
            return tuple(
                (im, align) for im, align in images
                if is_tablet != isinstance(im, Parallax)
            )

    class _EnemyListRenderer(object):
        def __init__(self, store, resolver):
            self._store = store
            self._resolver = resolver

        def build_images(self):
            return self._resolver.visible_images(self._store.snapshot())

        def build_enemies(self):
            return self._resolver.visible_enemies()

        def build(self):
            return self.build_enemies() + self.build_images()

        def iter_sees(self):
            return iter(self.build())


    class EnemyVisualizer(object):
        _store = _ImageStore()
        _resolver = _VisibilityResolver()
        _renderer = _EnemyListRenderer(_store, _resolver)

        # --- рендер ---
        @classmethod
        def iter_sees(cls):
            return cls._renderer.iter_sees()

        @classmethod
        def iter_images(cls):
            return iter(cls._renderer.build_images())

        @classmethod
        def iter_sees_enemies(cls):
            return iter(cls._renderer.build_enemies())

        # --- хранилище ---
        @classmethod
        def insert_image(cls, image, align=(0.5, 0.5), index=None):
            cls._store.insert(image, align, index)

        @classmethod
        def insert_image_if_absent(cls, image, align=(0.5, 0.5), index=None):
            cls._store.insert_if_absent(image, align, index)

        @classmethod
        def set_align(cls, image, align, remove_all=False):
            cls._store.set_align(image, align, remove_all)

        @classmethod
        def remove_image(cls, image, remove_all=False):
            cls._store.remove(image, remove_all)

        @classmethod
        def has_image(cls, image):
            return cls._store.has(image)

        @classmethod
        def clear_images(cls):
            cls._store.clear()

        @classmethod
        def reset(cls):
            cls._resolver.reset()
            cls._store.clear()

    class EnemyVisualizerHandler(GameObject):
        def reset(self):
            EnemyVisualizer.reset()

    require_system("cycle").register(EnemyVisualizerHandler())
