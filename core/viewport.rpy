# -*- coding: utf-8 -*-
init -1 python in v1FNaSR:
    from __future__ import division

    _NUMERIC_TYPES = integer_types + (float,)

    def _is_number(value):
        return isinstance(value, _NUMERIC_TYPES) and not isinstance(value, bool)

    def _round_or_none(value):
        if value is None:
            return None
        return int(round(value))


    class ViewportError(Exception):
        pass


    class Viewport(object):
        __slots__ = (
            "virtual_width", "virtual_height",
            "host_width", "host_height",
            "scale", "offset_x", "offset_y",
        )

        def __init__(self, virtual_width, virtual_height, host_width, host_height):
            for name, value in (
                ("virtual_width", virtual_width),
                ("virtual_height", virtual_height),
                ("host_width", host_width),
                ("host_height", host_height),
            ):
                if value is None:
                    raise ViewportError(
                        "Viewport: %r is None, ожидалось положительное число" % name
                    )
                if not _is_number(value):
                    raise ViewportError(
                        "Viewport: %r должен быть числом, получено %r (%s)"
                        % (name, value, type(value))
                    )
                if value <= 0:
                    raise ViewportError(
                        "Viewport: %r должен быть положительным, получено %r" % (name, value)
                    )

            self.virtual_width = float(virtual_width)
            self.virtual_height = float(virtual_height)
            self.host_width = float(host_width)
            self.host_height = float(host_height)

            scale_x = self.host_width / self.virtual_width
            scale_y = self.host_height / self.virtual_height

            self.scale = min(scale_x, scale_y)

            self.offset_x = (self.host_width - self.virtual_width * self.scale) / 2.0
            self.offset_y = (self.host_height - self.virtual_height * self.scale) / 2.0

        def scale_scalar(self, value):
            if value is None:
                return None
            return value * self.scale

        def to_host_point(self, x, y):
            return (
                self.offset_x + x * self.scale,
                self.offset_y + y * self.scale,
            )

        def to_host_size(self, width=None, height=None):
            return (
                self.scale_scalar(width),
                self.scale_scalar(height),
            )

        def to_host_rect(self, x, y, width=None, height=None):
            hx, hy = self.to_host_point(x, y)
            hw, hh = self.to_host_size(width, height)
            return hx, hy, hw, hh

        def __repr__(self):
            return (
                "Viewport(virtual=%gx%g, host=%gx%g, scale=%.6f, offset=(%.2f, %.2f))"
                % (
                    self.virtual_width, self.virtual_height,
                    self.host_width, self.host_height,
                    self.scale, self.offset_x, self.offset_y,
                )
            )


    class ViewportManager(object):
        VIRTUAL_WIDTH = 1920
        VIRTUAL_HEIGHT = 1080

        _current = None

        @classmethod
        def init(cls, host_width=None, host_height=None):
            if host_width is None:
                host_width = renpy.config.screen_width
            if host_height is None:
                host_height = renpy.config.screen_height

            cls._current = Viewport(
                cls.VIRTUAL_WIDTH, cls.VIRTUAL_HEIGHT,
                host_width, host_height,
            )
            return cls._current

        # update — просто смысловой алиас для вызова по событию ресайза,
        # читается понятнее в контексте. Буквально тот же метод, отдельную
        # сущность заводить не стали (YAGNI).
        update = init

        @classmethod
        def current(cls):
            if cls._current is None:
                raise ViewportError(
                    "ViewportManager не инициализирован. Нужно вызвать "
                    "ViewportManager.init() до первого использования "
                    "build_transform()/scale_image()/scale_font_size()."
                )
            return cls._current

        @classmethod
        def is_initialized(cls):
            return cls._current is not None

    def build_transform(child, x=MISSING, y=MISSING, width=MISSING, height=MISSING,
                    zoom=MISSING, anchor=MISSING, rotate=MISSING, alpha=MISSING,
                    viewport=None):
        vp = viewport or ViewportManager.current()

        kwargs = {}

        if x is not MISSING:
            if not _is_number(x):
                raise ViewportError(
                    "build_transform: x должен быть числом, получено %r" % (x,)
                )

            hx, _ = vp.to_host_point(x, 0)
            kwargs["xpos"] = _round_or_none(hx)

        if y is not MISSING:
            if not _is_number(y):
                raise ViewportError(
                    "build_transform: y должен быть числом, получено %r" % (y,)
                )

            _, hy = vp.to_host_point(0, y)
            kwargs["ypos"] = _round_or_none(hy)

        if width is not MISSING:
            hw = vp.scale_scalar(width) if width is not None else None
            kwargs["xsize"] = _round_or_none(hw)

        if height is not MISSING:
            hh = vp.scale_scalar(height) if height is not None else None
            kwargs["ysize"] = _round_or_none(hh)

        if zoom is not MISSING:
            kwargs["zoom"] = vp.scale_scalar(zoom)

        if anchor is not MISSING:
            kwargs["anchor"] = anchor

        if rotate is not MISSING:
            kwargs["rotate"] = rotate

        if alpha is not MISSING:
            kwargs["alpha"] = alpha

        return renpy.store.Transform(child, **kwargs)


    def build_image(filename, **kwargs):
        return build_transform(filename, **kwargs)


    def scale_image(image, width, height, viewport=None):
        vp = viewport or ViewportManager.current()

        hw, hh = vp.to_host_size(width, height)
        hw = _round_or_none(hw)
        hh = _round_or_none(hh)

        if not hw or not hh:
            raise ViewportError(
                "scale_image: некорректный итоговый размер %r x %r "
                "(width=%r height=%r)" % (hw, hh, width, height)
            )

        return renpy.store.im.Scale(image, hw, hh)


    def scale_font_size(base_size, min_ratio=0.75, viewport=None):
        vp = viewport or ViewportManager.current()

        if not _is_number(base_size) or base_size <= 0:
            raise ViewportError(
                "scale_font_size: base_size должен быть положительным числом, получено %r"
                % (base_size,)
            )

        scaled = base_size * vp.scale
        floor = base_size * min_ratio

        if scaled < floor:
            scaled = floor

        return int(round(scaled))
