# camera.rpy
init python in v1FNaSR:
    class CameraInfo(object):

        _BREAK_IMAGE = None

        def __init__(self, num, align, rotate=None, identical_ids=None):
            if not isinstance(align, Iterable):
                raise FNaSRTypeError("align должен быть Iterable, а не '{}'".format(type(align)))
            for i in align:
                if not isinstance(i, float):
                    raise FNaSRTypeError("Все элементы align должны быть типа 'float', а не '{}'".format(type(i)))
            if rotate is None:
                rotate = 0
            if identical_ids is None:
                identical_ids = []
            if not isinstance(identical_ids, Iterable):
                raise FNaSRTypeError("identical_ids должен быть Iterable, а не '{}'".format(type(align)))

            self._num = to_text(num)   # str
            self._align = tuple(align)        # tuple[float, float]
            self._rotate = int(rotate) # int
            self._identical = frozenset(identical_ids)
            self._active = True
            self._break_time = 0.0

        @classmethod
        def _get_break_image(cls):
            if cls._BREAK_IMAGE is None:
                cls._BREAK_IMAGE = Fixed(
                    Solid("#000"),
                    Text("CAMERA\nOFFLINE", color="#FF0000", xalign=0.5, yalign=0.5)
                )
            return cls._BREAK_IMAGE

        @property
        def num(self):
            return self._num

        @property
        def align(self):
            return self._align

        @property
        def rotate(self):
            return self._rotate

        @property
        def is_active(self):
            return self._active

        @property
        def break_time(self):
            return self._break_time

        @property
        def identical_ids(self):
            return self._identical

        def add_break_time(self, time):
            self._break_time += time

        def to_repair(self):
            self._break_time <= 0.0

        def get_break_image(self):
            if self._break_time <= 0:
                return None
            return self._get_break_image()

        def enable(self):
            self._active = True

        def disable(self):
            self._active = False






