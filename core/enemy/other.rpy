init -5 python in v1FNaSR:
    class EnemyPath(object):
        def __init__(self, *path):
            self._current_location = None
            self._old_location = None

            self.paths = []
            self.path_map = {}

            for i, p in enumerate(paths, 1):
                self.paths.append(p)
                self.path_map[i] = p
