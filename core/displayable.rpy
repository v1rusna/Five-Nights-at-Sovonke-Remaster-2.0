# displayable.rpy
init python in v1FNaSR:
    import math as _math
    import pygame as _pygame


    class DistanceButton(renpy.Displayable):
        __slots__ = (
            "child",

            "radius",
            "opaque_radius",
            "falloff",

            "alpha",

            "child_width",
            "child_height",

            "width",
            "height",
        )

        def __init__(
            self,
            child,
            radius=200.0,
            opaque_radius=0.0,
            falloff=1.0
        ):
            renpy.Displayable.__init__(self)

            self.child = child

            self.radius = float(radius)
            self.opaque_radius = float(opaque_radius)
            self.falloff = float(falloff)

            self.alpha = 0.0

            self.child_width = 0
            self.child_height = 0

            self.width = 0
            self.height = 0

        def _calculate_alpha(self, x, y):
            """
            Возвращает alpha в зависимости от расстояния
            курсора до центра DistanceButton.
            """

            center_x = self.width / 2.0
            center_y = self.height / 2.0

            distance = _math.hypot(
                x - center_x,
                y - center_y
            )

            if distance <= self.opaque_radius:
                return 1.0

            if distance >= self.radius:
                return 0.0

            distance_range = self.radius - self.opaque_radius

            progress = (
                distance - self.opaque_radius
            ) / distance_range

            alpha = 1.0 - progress

            if self.falloff != 1.0:
                alpha = pow(alpha, self.falloff)

            return alpha

        def render(self, width, height, st, at):
            child = renpy.render(
                self.child,
                width,
                height,
                st,
                at
            )

            child_width, child_height = child.get_size()

            self.child_width = child_width
            self.child_height = child_height

            self.width = max(
                child_width,
                int(self.radius * 2.0)
            )

            self.height = max(
                child_height,
                int(self.radius * 2.0)
            )

            result = renpy.Render(
                self.width,
                self.height
            )

            child_transform = renpy.store.Transform(
                self.child,
                alpha=self.alpha
            )

            child_render = renpy.render(
                child_transform,
                self.width,
                self.height,
                st,
                at
            )

            x = (self.width - child_width) / 2.0
            y = (self.height - child_height) / 2.0

            result.blit(
                child_render,
                (x, y)
            )

            return result

        def event(self, ev, x, y, st):
            new_alpha = self._calculate_alpha(x, y)

            if new_alpha != self.alpha:
                self.alpha = new_alpha
                renpy.redraw(self, 0)

            child_x = (
                x - (self.width - self.child_width) / 2.0
            )

            child_y = (
                y - (self.height - self.child_height) / 2.0
            )

            return self.child.event(
                ev,
                child_x,
                child_y,
                st
            )

        def visit(self):
            return [self.child]

    class HoldingMouseImageButton(renpy.Displayable):
        __slots__ = (
            "displayable",

            "idle",
            "clicked",

            "width",
            "height",

            "allow_alternate",

            "click_action",
            "unclick_action",

            "_mouse_pressed",
            "_keyboard_pressed",

            "_clicked",
        )

        def __init__(
            self,
            idle,
            clicked=None,
            click_action=None,
            unclick_action=None,
            allow_alternate=False,
            **kwargs
        ):
            super(HoldingMouseImageButton, self).__init__(**kwargs)

            self.displayable = renpy.displayable(idle)

            self.idle = self.displayable
            self.clicked = renpy.displayable(clicked) if clicked is not None else self.idle

            self.width = 0
            self.height = 0

            self.allow_alternate = allow_alternate

            self.click_action = click_action if click_action is not None else NullAction()
            self.unclick_action = unclick_action if unclick_action is not None else NullAction()

            self._mouse_pressed = False
            self._keyboard_pressed = False

            self._clicked = False

        def _update_pressed_state(self):
            clicked = self._mouse_pressed or self._keyboard_pressed

            if clicked == self._clicked:
                return

            self._clicked = clicked

            if clicked:
                self.displayable = self.clicked
                action = self.click_action
            else:
                self.displayable = self.idle
                action = self.unclick_action

            renpy.display.behavior.run(action)
            renpy.redraw(self, 0.0)

        def keyboard_down(self):
            if not self._keyboard_pressed:
                self._keyboard_pressed = True
                self._update_pressed_state()

        def keyboard_up(self):
            if self._keyboard_pressed:
                self._keyboard_pressed = False
                self._update_pressed_state()

        def force_unclick(self):
            was_clicked = self._clicked

            self._mouse_pressed = False
            self._keyboard_pressed = False
            self._clicked = False

            self.displayable = self.idle

            if was_clicked:
                renpy.display.behavior.run(self.unclick_action)
                renpy.redraw(self, 0.0)

        def render(self, width, height, st, at):
            child_r = renpy.render(self.displayable, width, height, st, at)
            self.width, self.height = child_r.get_size()

            render = renpy.Render(self.width, self.height)
            render.blit(child_r, (0, 0))

            _pygame.time.set_timer(renpy.display.core.PERIODIC, renpy.display.core.PERIODIC_INTERVAL)

            return render

        def event(self, ev, x, y, st):
            if (0 <= x <= self.width) and (0 <= y <= self.height):
                if ev.type == _pygame.MOUSEBUTTONDOWN and (ev.button == 1 or (ev.button == 3 and self.allow_alternate)):
                    self._mouse_pressed = True
                    self._update_pressed_state()

                    return self.displayable.event(ev, x, y, st)

            if ev.type == _pygame.MOUSEBUTTONUP and self._mouse_pressed:
                self._mouse_pressed = False
                self._update_pressed_state()

                return self.displayable.event(ev, x, y, st)

            return None

        def visit(self):
            return [self.idle, self.clicked]
