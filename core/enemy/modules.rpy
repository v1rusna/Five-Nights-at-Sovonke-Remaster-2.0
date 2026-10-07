# modules.rpy
init -2 python in v1FNaSR:
    class EnemyMoveModule(EnemyModule):
        def __init__(
            self, path,
            speed=1.0,
            auto_generate=False,
            max_movement_opportunities=3,
            attempts_move_fn=None
        ):
            super(EnemyMoveModule, self).__init__()

            if attempts_move_fn is not None and not callable(attempts_move_fn):
                raise FNaSRTypeError("'attempts_move_fn' должен быть вызываемым, пришло: {}".format(type(attempts_move_fn)))

            if path is None:
                path = ()
            elif is_string(path):
                path = (path,)
            elif not isinstance(path, Iterable):
                raise FNaSRTypeError("'path' должен быть итерируемым, пришло: {}".format(type(path)))

            if not is_number(speed) or speed < 0:
                raise FNaSRTypeError("'speed' должен быть числом пришло: {}".format(type(speed)))

            self._setattr("_path", list(path))
            self._setattr("_cursor", 0)
            self._setattr("_auto_generate", bool(auto_generate))
            self._setattr("_movement_opportunities", 0)
            self._setattr("_max_movement_opportunities", max_movement_opportunities)
            self._setattr("_speed", float(speed))

            self._attempts_move_fn = attempts_move_fn

        @property
        def current_location_id(self):
            if not len(self._path):
                return None
            return self._path[self._cursor]

        def on_include(self, enemy):
            context = enemy.context
            
            if context.get("location_system") is None:
                context.location_system = require_system("location")

            if context.get("game_time") is None:
                context.game_time = require_system("time")

        def start(self, context):
            for location_id in self._path:
                context.location_system.require_location(location_id)
            self._move(context)

        def update(self, context):
            if not len(self._path):
                return

            if self.move_change(context):
                self.step_forward()
                if not self._move(context):
                    self._cursor = 0
                    self._move(context)

        def _move(self, context, location=None):
            if location is None:
                location = context.location_system.require_location(self.current_location_id)
            try:
                context.enemy.move(location)
                return True
            except DoorClose:
                return False

        def move_change(self, context):
            self._movement_opportunities += 1
            if self._movement_opportunities >= self._max_movement_opportunities:
                self._movement_opportunities = 0
                game_time_factor = context.game_time.total_hours * 10
                return (renpy.random.randint(1, 1000) + game_time_factor) * self._speed >= 800
            return False
        
        def step_forward(self):
            if not len(self._path):
                return
            self._cursor += 1
            if self._cursor > len(self._path) - 1:
                self._cursor = 0
            return self.current_location_id

        def step_back(self):
            if not len(self._path):
                return
            self._cursor -= 1
            if self._cursor < 0:
                self._cursor = len(self._path) - 1
            return self.current_location_id




        

