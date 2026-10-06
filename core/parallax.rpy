
init python in v1FNaSR:
    class Parallax(renpy.Displayable):
        __slots__ = [
            "displayable",
            "zoom",
            "anchor",
            "power",
            "sharpness_factor",
            "enable_y_shift",

            "xoffset",
            "yoffset",

            "mouse_pos_x",
            "mouse_pos_y",

            "perspective",
            "r_power",

            "width",
            "height",

            "fill_viewport",
            "view_width",
            "view_height",

            "_transform",
        ]

        def __init__(self, displayable, zoom, anchor, power,
                    sharpness_factor=1.0, enable_y_shift=True,
                    fill_viewport=False, **kwargs):
            super(Parallax, self).__init__(**kwargs)

            self.displayable = renpy.displayable(displayable)

            self.zoom = zoom

            if anchor is None:
                self.anchor = None
            else:
                self.anchor = (float(anchor[0]), float(anchor[1]))

            self.power = float(power)
            self.sharpness_factor = float(sharpness_factor)
            self.enable_y_shift = enable_y_shift
            self.fill_viewport = bool(fill_viewport)

            self.xoffset = 0.0
            self.yoffset = 0.0

            self.mouse_pos_x = 0.0
            self.mouse_pos_y = 0.0

            self.width = 0
            self.height = 0
            self.view_width = 0
            self.view_height = 0

            self.perspective = None
            self.r_power = None

            self._transform = renpy.display.transform.Transform(
                self.displayable,
                zoom=self.zoom
            )

        def get_size(self):
            return (self.width, self.height)

        def set_displayable(self, displayable):
            """Меняет displayable и пересоздаёт кешированный Transform."""
            self.displayable = renpy.displayable(displayable)
            self._rebuild_transform()

        def set_zoom(self, zoom):
            """Меняет zoom и пересоздаёт кешированный Transform."""
            self.zoom = zoom
            self._rebuild_transform()

        def _rebuild_transform(self):
            """Пересоздаёт Transform при изменении displayable или zoom."""
            self._transform = renpy.display.transform.Transform(
                self.displayable,
                zoom=self.zoom
            )

        def _origin_shift(self):
            """
            Положение левого верхнего угла контента внутри Render
            (без учёта параллакса). В обычном режиме контент = Render -> (0, 0).
            """
            if not self.fill_viewport:
                return (0.0, 0.0)

            return (
                (self.view_width - self.width) / 2.0,
                (self.view_height - self.height) / 2.0,
            )

        def _anchor_point(self):
            """Точка (в координатах Render), при которой смещение равно нулю."""
            if self.anchor is not None:
                return self.anchor
            return (self.view_width / 2.0, self.view_height / 2.0)

        def _update_offset(self):
            """
            Плавно смещает xoffset/yoffset к позиции мыши.
            Вызывается из event(), а НЕ из render() - иначе renpy.redraw()
            внутри этого метода создаёт бесконечный цикл перерисовки.
            """
            anchor_x, anchor_y = self._anchor_point()

            self.xoffset += (
                (self.mouse_pos_x - (self.xoffset + anchor_x))
                * self.sharpness_factor
            )

            if self.enable_y_shift:
                self.yoffset += (
                    (self.mouse_pos_y - (self.yoffset + anchor_y))
                    * self.sharpness_factor
                )
            else:
                self.yoffset = 0.0

            renpy.redraw(self, 0)

        def render(self, width, height, st, at):
            x_shift = -(self.xoffset * self.power)
            y_shift = -(self.yoffset * self.power)

            child_r = renpy.render(self._transform, width, height, st, at)
            self.width, self.height = child_r.get_size()

            if self.fill_viewport:
                self.view_width, self.view_height = width, height
            else:
                self.view_width, self.view_height = self.width, self.height

            origin_x, origin_y = self._origin_shift()

            rv = renpy.Render(self.view_width, self.view_height)
            rv.subpixel_blit(child_r, (origin_x + x_shift, origin_y + y_shift))

            if self.fill_viewport:
                rv.xclipping = True
                rv.yclipping = True

            return rv

        def event(self, ev, x, y, st):
            self.mouse_pos_x = x
            self.mouse_pos_y = y
            self._update_offset()

            origin_x, origin_y = self._origin_shift()

            child_x = x - origin_x + (self.xoffset * self.power)
            child_y = y - origin_y + (self.yoffset * self.power)

            return self.displayable.event(ev, child_x, child_y, st)

        def visit(self):
            return [self.displayable]

        def __repr__(self):
            return (
                "V1ParallaxFNaSR(displayable=%r, zoom=%r, anchor=%r, power=%r)"
                % (self.displayable, self.zoom, self.anchor, self.power)
            )

    class ParallaxWrapper(object):
        """
        Обёртка над Ren'Py Displayable-классами (например ImageButton),
        позволяющая совместить параллакс-логику с поведением кнопки.

        Использование:
            btn = ParallaxWrapper(renpy.display.behavior.ImageButton,
                                idle_image, hover_image,
                                action=some_action)
        """

        def __new__(cls, class_wrappee, *args, **kwargs):
            _outer_cls = cls

            class Wrapped(class_wrappee):

                def __init__(self, *a, **k):
                    super(Wrapped, self).__init__(*a, **k)

                    self._wrapper = _outer_cls
                    self._v1items = []
                    self._reg_v1items = []

                    for i in a:
                        if isinstance(i, renpy.display.core.Displayable):
                            if i not in self._reg_v1items:
                                self._reg_v1items.append(i)
                                self._v1items.append({"d": i, "size": (0, 0)})

                    for _key, value in list(k.items()):
                        if isinstance(value, renpy.display.core.Displayable):
                            if value not in self._reg_v1items:
                                self._reg_v1items.append(value)
                                self._v1items.append({"d": value, "size": (0, 0)})

                def visit(self):
                    parent_visit = super(Wrapped, self).visit() or []
                    return list(parent_visit) + [item["d"] for item in self._v1items]

                def render(self, width, height, st, at):
                    for item in self._v1items:
                        r = renpy.render(item["d"], width, height, st, at)
                        item["size"] = r.get_size()

                    return super(Wrapped, self).render(width, height, st, at)

                def event(self, ev, x, y, st):
                    child_result = None

                    for item in self._v1items:
                        d = item["d"]
                        dw, dh = item["size"]

                        result = d.event(ev, x - dw // 2, y - dh // 2, st)

                        if result is not None and child_result is None:
                            child_result = result

                    parent_result = super(Wrapped, self).event(ev, x, y, st)
                    return parent_result if parent_result is not None else child_result

                def __repr__(self):
                    return "V1WrappedFNaSR(%s)" % super(Wrapped, self).__repr__()

            return Wrapped(*args, **kwargs)

        @staticmethod
        def _is_wrapped(instance):
            """True, если instance создан через ParallaxWrapper."""
            return (
                hasattr(instance, "_wrapper")
                and instance._wrapper is ParallaxWrapper
            )

        @staticmethod
        def get_wrapped_items(instance):
            """
            Возвращает копию списка параллакс-элементов
            [{"d": Displayable, "size": (w, h)}, ...] или [].
            """
            if ParallaxWrapper._is_wrapped(instance):
                return list(instance._v1items)
            return []

        @staticmethod
        def clear_wrapped_items(instance):
            """Очищает все параллакс-элементы обёрнутого объекта."""
            if ParallaxWrapper._is_wrapped(instance):
                instance._v1items = []
                instance._reg_v1items = []

        @staticmethod
        def add_wrapped_item(instance, displayable, size=None):
            """
            Добавляет Displayable в параллакс-список.
            Один и тот же объект не добавляется дважды.
            """
            if not ParallaxWrapper._is_wrapped(instance):
                return
            if not isinstance(displayable, renpy.display.core.Displayable):
                return
            if displayable in instance._reg_v1items:
                return

            size = size if size is not None else (0, 0)
            instance._reg_v1items.append(displayable)
            instance._v1items.append({"d": displayable, "size": size})
