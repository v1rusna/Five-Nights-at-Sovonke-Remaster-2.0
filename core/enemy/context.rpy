# context.rpy
init -4 python in v1FNaSR:
    class EnemyContext(DebugContext):
        __slots__ = ("_enemy",)

        def __init__(self, enemy):
            if not isinstance(enemy, BaseEnemy):
                raise FNaSRTypeError("'enemy' должен быть 'BaseEnemy', пришло: {}".format(type(enemy)))

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
