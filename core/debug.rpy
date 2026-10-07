# debug.rpy
init -5 python in v1FNaSR:
    import traceback as _traceback
    import time as _time

    def color_text(text, color):
        if color is None:
            return text
        return "{color=%s}%s{/color}" % (color, text)

    def _get_frame_times():
        interface = getattr(renpy.display, "interface", None)

        if interface is None:
            return None

        return getattr(interface, "frame_times", None)

    def get_average_render_fps():
        times = _get_frame_times()

        if not times or len(times) < 2:
            return 0.0

        dt = times[-1] - times[0]

        return (len(times) - 1) / dt if dt > 0 else 0.0


    def get_render_fps(samples=10):
        times = _get_frame_times()

        if not times or len(times) < 2:
            return 0.0

        start = max(0, len(times) - samples - 1)
        recent = times[start:]

        if len(recent) < 2:
            return 0.0

        dt = recent[-1] - recent[0]

        return (len(recent) - 1) / dt if dt > 0 else 0.0

    class LogSystem(object):
        def error(self, msg=None, format_exc=None):
            if msg is None:
                msg = "error"
            if format_exc is None:
                format_exc = _traceback.format_exc()
            renpy.log("FNaSR | %s:" % msg)
            renpy.log(format_exc)

        def __call__(self, msg, value=None):
            text = to_text(msg)
            if value is not None:
                text += ": " + repr(value)

            renpy.log("FNaSR | "+text)

    log = LogSystem()

    def _safe_element_get(element, disable_error=True):
        try:
            return element.get()
        except Exception as e:
            log.error("Ошибка debug элемента {}".format(repr(element)))
            if disable_error:
                element.set_error(e)

    class DebugContext(object):
        __slots__ = ("_data",)

        def __init__(self):
            object.__setattr__(self, "_data", {})

        def set(self, k, v):
            self._data[k] = v

        def get(self, key, default=None):
            return self._data.get(key, default)

        def clear(self):
            self._data.clear()

        def items(self):
            return self._data.items()

        def keys(self):
            return self._data.keys()

        def values(self):
            return self._data.values()

        def update(self, data):
            try:
                self._data.update(data)
            except ValueError as e:
                raise FNaSRValueError(e)

        def __getattr__(self, name):
            if name in self._data:
                return self._data[name]
            raise FNaSRAttributeError("'{}' object has no attribute '{}'".format(self.__class__.__name__, name))

        def __setattr__(self, name, value):
            if name == "_data":
                object.__setattr__(self, name, value)
            else:
                self._data[name] = value

        def __delattr__(self, name):
            if name in self._data:
                del self._data[name]
            else:
                raise FNaSRAttributeError("'{}' object has no attribute '{}'".format(self.__class__.__name__, name))

        def __contains__(self, name):
            return name in self._data

        def __len__(self):
            return len(self._data)

        def __iter__(self):
            return iter(self._data)

        def __repr__(self):
            return "<DebugContext len={} at {}>".format(len(self._data), hex(id(self)))

    class DebugElement(object):
        def __init__(self, order=0, condition=None):
            if condition is not None and not callable(condition):
                raise FNaSRTypeError("'condition' must be callable and return a boolean; received: {}".format(type(condition)))
            self._enable = True
            self._error = None
            self._order = int(order)
            self._condition = condition
            self._context = DebugContext()

        @property
        def is_enabled(self):
            return self._enable

        @property
        def order(self):
            return self._order

        @property
        def check_condition(self):
            if self._condition is None:
                return True
            try:
                return self._call_with_context(self._condition)
            except Exception as e:
                log.error("Element '{}' caused an exception in 'check_condition'".format(self.__repr__()))
                self.set_error(e)
                return False

        @property
        def context(self):
            return self._context

        @property
        def has_error(self):
            return self._error is not None

        @property
        def error(self):
            return self._error

        def enable(self):
            self._enable = True

        def disable(self):
            self._enable = False

        def set_error(self, error):
            self._error = to_text(error)
            self._enable = False

        def clear_error(self):
            self._error = None

        def get(self):
            raise FNaSRNotImplementedError()

        def matches(self, query):
            """
            Содержит ли последний показанный текст элемента подстроку query.

            query приходит уже в нижнем регистре и не пустой. Вызывать нужно ПОСЛЕ get(),
            потому что текст берётся из кэша последнего get(), а не вычисляется заново.
            Элемент без собственного текста ничего не находит.
            """
            return False

        def count_element_states(self):
            if self:
                return 1, 0
            return 0, 1

        def _call_with_context(self, fn):
            return fn(self._context)

        def __bool__(self):
            return self._enable

        __nonzero__ = __bool__

        def __repr__(self):
            return "<v1FNaSR.{}(enable={}, order={}) at {}>".format(
                self.__class__.__name__,
                self._enable, self._order,
                hex(id(self))
            )

    class DebugText(DebugElement):
        def __init__(self, fn, style="v1_text_12_style_FNaSR", **kwargs):
            if not callable(fn):
                raise FNaSRTypeError("'fn' must be a callable; passed: {}".format(type(fn)))

            super(DebugText, self).__init__(**kwargs)

            self._fn = fn
            self._style = style

            self._renpy_obj = None
            self._previous_content = None

        def get(self):
            content = self._call_with_context(self._fn)

            if content == self._previous_content:
                return self._renpy_obj

            self._previous_content = content
            self._renpy_obj = renpy.store.Text(
                content,
                style=self._style,
                substitute=False
            )

            return self._renpy_obj

        def matches(self, query):
            if self._previous_content is None:
                return False
            return query in to_text(self._previous_content).lower()

    class DebugButton(DebugElement):
        def __init__(self, text_fn, fn, style="v1_move_location_button_FNaSR", text_style="v1_text_12_style_FNaSR", **kwargs):
            if not callable(text_fn):
                raise FNaSRTypeError("'text_fn' must be a callable; passed: {}".format(type(text_fn)))
            if not callable(fn):
                raise FNaSRTypeError("'fn' must be a callable; passed: {}".format(type(fn)))

            super(DebugButton, self).__init__(**kwargs)

            self._text_fn = text_fn
            self._fn = fn
            self._style = style
            self._text_style = text_style

            self._previous_content = None
            self._renpy_obj = None

            self._clicked = lambda: self._call_with_context(self._fn)

        @property
        def text(self):
            return self._call_with_context(self._text_fn)

        def get(self):
            content = self._call_with_context(self._text_fn)

            if content != self._previous_content:
                self._previous_content = content

                self._renpy_obj = renpy.store.TextButton(
                    content,
                    clicked=self._clicked,
                    xalign=0.0,
                    style=self._style,
                    text_style=self._text_style
                )

            return self._renpy_obj

        def matches(self, query):
            if self._previous_content is None:
                return False
            return query in to_text(self._previous_content).lower()

    class DebugSection(DebugElement):
        def __init__(self, *elements, **kwargs):
            for element in elements:
                if not isinstance(element, DebugElement):
                    raise FNaSRTypeError("'elements' must consist solely of 'DebugElement'; the following was received: {}".format(type(element)))

            super(DebugSection, self).__init__(**kwargs)

            self._section = list(elements)
            self._cache_ids = list()
            self._renpy_obj = None

            self._sorted_elements = sorted(self._section, key=lambda el: el.order)

        @property
        def elements(self):
            return list(self._section)

        @property
        def sorted_elements(self):
            return self._sorted_elements

        def _collect(self):
            contents = []
            error = True
            for element in self.sorted_elements:
                if not element:
                    continue

                for k, v in self._context.items():
                    if k not in element.context:
                        element.context.set(k, v)

                if not element.check_condition:
                    error = False
                    continue

                content = self._safe_get(element)
                if content is not None:
                    contents.append(content)

            return contents, (error and not contents)

        def _build(self, contents):
            ids = [id(content) for content in contents]

            if ids == self._cache_ids:
                return self._renpy_obj

            self._cache_ids = ids

            box = renpy.store.VBox()
            for content in contents:
                box.add(content)
            self._renpy_obj = box

            return self._renpy_obj

        def get(self):
            contents, failed = self._collect()

            if failed:
                self.disable()
                return

            return self._build(contents)

        def matches(self, query):
            for element in self._section:
                if element and element.check_condition and element.matches(query):
                    return True
            return False

        def count_element_states(self):
            active = 0
            inactive = 0

            for element in self._section:
                a, i = element.count_element_states()
                active += a
                inactive += i

            return active, inactive

        def _safe_get(self, element, disable_error=True):
            try:
                return element.get()
            except Exception as e:
                log.error("Секция {}: Ошибка debug элемента {}'".format(self.__repr__(), repr(element)))
                if disable_error:
                    element.set_error(e)

        def __repr__(self):
            return "<Section elements={} is {}>".format(len(self._section), super(DebugSection, self).__repr__())

    class DebugRow(DebugSection):
        def _build(self, contents):
            ids = [id(content) for content in contents]

            if ids == self._cache_ids:
                return self._renpy_obj

            self._cache_ids = ids

            box = renpy.store.HBox()
            for content in contents:
                box.add(content)
            self._renpy_obj = box

            return self._renpy_obj

    class DebugFold(DebugSection):
        _INDENT = 14

        def __init__(self, title, *elements, **kwargs):
            expanded = kwargs.pop("expanded", False)

            super(DebugFold, self).__init__(*elements, **kwargs)

            self._title = to_text(title)
            self._expanded = bool(expanded)

            self._header = None
            self._header_state = None

            self._fold_ids = None
            self._fold_obj = None

        @property
        def is_expanded(self):
            return self._expanded

        def expand(self):
            self._expanded = True

        def collapse(self):
            self._expanded = False

        def toggle(self):
            self._expanded = not self._expanded
            renpy.restart_interaction()

        def _get_header(self, opened):
            if self._header is None or self._header_state != opened:
                self._header_state = opened
                self._header = renpy.store.TextButton(
                    ("- " if opened else "+ ") + self._title,
                    clicked=self.toggle,
                    xalign=0.0,
                    style="v1_move_location_button_FNaSR",
                    text_style="v1_text_12_style_FNaSR"
                )
            return self._header

        def get(self):
            opened = self._expanded or bool(debug.query)

            body = None
            if opened:
                contents, failed = self._collect()
                if contents:
                    body = self._build(contents)

            header = self._get_header(opened)

            ids = (id(header), id(body))
            if ids == self._fold_ids:
                return self._fold_obj

            self._fold_ids = ids

            box = renpy.store.VBox()
            box.add(header)

            if body is not None:
                row = renpy.store.HBox()
                row.add(renpy.store.Null(width=self._INDENT))
                row.add(body)
                box.add(row)

            self._fold_obj = box

            return self._fold_obj

        def matches(self, query):
            if query in self._title.lower():
                return True
            return super(DebugFold, self).matches(query)

        def __repr__(self):
            return "<Fold title={!r} expanded={} is {}>".format(
                self._title, self._expanded, super(DebugFold, self).__repr__()
            )

    class DebugIf(DebugElement):
        def __init__(self, if_condition, element, else_element, **kwargs):
            if not callable(if_condition):
                raise FNaSRTypeError("'if_condition' must be callable; passed: {}".format(type(if_condition)))

            if not isinstance(element, DebugElement):
                raise FNaSRTypeError("'element' must be 'DebugElement'; received: {}".format(type(element)))

            if not isinstance(else_element, DebugElement):
                raise FNaSRTypeError("'else_element' must be 'DebugElement'; received: {}".format(type(else_element)))

            super(DebugIf, self).__init__(**kwargs)

            self._if_condition = if_condition
            self._element = element
            self._else_element = else_element

        @property
        def is_if_condition(self):
            return self._call_with_context(self._if_condition)

        def get(self):
            element = (
                self._element
                if self._call_with_context(self._if_condition)
                else self._else_element
            )

            if not element:
                return

            for k, v in self._context.items():
                if k not in element.context:
                    element.context.set(k, v)

            if not element.check_condition:
                return

            return element.get()

        def matches(self, query):
            element = (
                self._element
                if self.is_if_condition
                else self._else_element
            )
            return element.matches(query)

        def count_element_states(self):
            element = (
                self._element
                if self.is_if_condition
                else self._else_element
            )
            return element.count_element_states()

    class DebugGroup(object):
        def __init__(self, name, title=None, order=0):
            name = to_text(name)
            if title is None:
                title = name
            title = to_text(title)

            self._name = name
            self._title = title
            self._order = int(order)

            self._elements = list()
            self._enable = False

            self._header = None

            self._sorted_elements = sorted(self._elements, key=lambda el: el.order)

        @property
        def name(self):
            return self._name

        @property
        def title(self):
            return self._title

        @property
        def order(self):
            return self._order

        @property
        def elements(self):
            return list(self._elements)

        @property
        def sorted_elements(self):
            return self._sorted_elements

        @property
        def is_enabled(self):
            return self._enable

        @property
        def header(self):
            """Заголовок группы для результатов поиска (создаётся один раз)."""
            if self._header is None:
                self._header = renpy.store.Text(
                    "{color=#8ab4ff}== " + self._title + " =={/color}",
                    style="v1_text_12_style_FNaSR",
                    substitute=False
                )
            return self._header

        def label(self, max_len=10):
            """Текст вкладки: название (обрезанное до max_len), зелёное если группа включена."""
            title = self._title
            if len(title) > max_len:
                title = title[:max_len] + "..."
            color = "{color=#0ac80a}" if self._enable else "{color=#c80a0a}"
            return color + title + "{/color}"

        def enable(self):
            self._enable = True

        def disable(self):
            self._enable = False

        def add_element(self, element):
            if not isinstance(element, DebugElement):
                raise FNaSRTypeError("element должен быть 'DebugElement', пришло: {}".format(type(element)))

            if element not in self._elements:
                self._elements.append(element)
                self._sorted_elements = sorted(self._elements, key=lambda el: el.order)

        def discard_element(self, element):
            if not isinstance(element, DebugElement):
                raise FNaSRTypeError("element должен быть 'DebugElement', пришло: {}".format(type(element)))

            if element in self._elements:
                self._elements.remove(element)
                self._sorted_elements = sorted(self._elements, key=lambda el: el.order)

        def has_element(self, element):
            return element in self._elements

        def iteration_content(self, disable_error=True, query=None):
            """
            Итерация по displayable'ам элементов группы.
            query (нижний регистр) оставляет только элементы, текст которых содержит запрос.
            """
            for element in self.sorted_elements:
                if element and element.check_condition:
                    content = _safe_element_get(element, disable_error)
                    if content is None:
                        continue
                    if query and not element.matches(query):
                        continue
                    yield content

        def count_element_states(self):
            """Количество включённых/выключенных DebugElement."""
            active = 0
            inactive = 0

            for element in self._elements:
                a, i = element.count_element_states()
                active += a
                inactive += i

            return active, inactive

        def count_total_elements(self):
            a, i = self.count_element_states()
            return a + i

        def __iter__(self):
            return iter(sorted(self._elements, key=lambda el: el.order))

        def __len__(self):
            return len(self._elements)

    class Debug(object):
        def __init__(self):
            self._groups = dict()
            self.create_group("General", order=-9999)

            self._fps_timestamps = list()
            self._fps = 0.0

            self._active = True

            self._solo = True

            self._query_raw = ""
            self._query = ""

            self._input_mode = False

        @property
        def calls_per_second(self):
            return self._fps

        @property
        def is_activity(self):
            return self._active

        @property
        def is_solo(self):
            return self._solo

        @property
        def mode_label(self):
            if self._solo:
                return "{color=#0ac80a}Solo{/color}"
            return "{color=#c8c80a}Multi{/color}"

        @property
        def query(self):
            """Нормализованный поисковый запрос ('' если поиск не активен)."""
            return self._query

        @property
        def query_raw(self):
            return self._query_raw

        @property
        def is_input_mode(self):
            return self._input_mode

        def enable_input_mode(self):
            self._input_mode = True

        def disenable_input_mode(self):
            self._input_mode = False

        def set_query(self, text):
            raw = "" if text is None else to_text(text)
            self._query_raw = raw
            self._query = raw.strip().lower()

        def clear_query(self):
            self.set_query("")

        def activate(self):
            self._active = True

        def deactivate(self):
            self._active = False
            del self._fps_timestamps[:]

        def toggle_solo(self):
            self._solo = not self._solo

            if self._solo:
                enabled = [g for g in self.get_sorted_groups() if g.is_enabled]
                for group in enabled[1:]:
                    group.disable()

        def toggle_group(self, name):
            group = self.get_group(to_text(name))
            if group is None:
                raise FNaSRValueError("The group '{}' does not exist".format(to_text(name)))

            if self._solo:
                turn_on = not group.is_enabled
                for other in self._groups.values():
                    other.disable()
                if turn_on:
                    group.enable()
            elif group.is_enabled:
                group.disable()
            else:
                group.enable()

        def _update_fps(self):
            now = _time.time()
            self._fps_timestamps.append(now)

            cutoff = now - 1.0
            self._fps_timestamps = [t for t in self._fps_timestamps if t > cutoff]

            self._fps = len(self._fps_timestamps)

        def iter_groups(self):
            return iter(list(self._groups.values()))

        def get_sorted_groups(self):
            return sorted(self._groups.values(), key=lambda g: g.order)

        def get_group_rows(self, size):
            """Непустые группы, разбитые на строки по size вкладок (для экрана)."""
            groups = [g for g in self.get_sorted_groups() if len(g)]
            size = max(1, int(size))
            return [groups[i:i + size] for i in range(0, len(groups), size)]

        def create_group(self, name, title=None, order=0, overwrite=False):
            group = DebugGroup(name, title, order)
            self._register(group, overwrite)
            return group

        def register_group(self, group, overwrite=False):
            self._register(group, overwrite)

        def has_group(self, group_name):
            return to_text(group_name) in self._groups

        def get_group(self, name):
            return self._groups.get(name)

        def add_element(self, element, group="General", group_autocreate=False):
            self._get_and_validate_group(group, group_autocreate).add_element(element)

        def discard_element(self, element, group="General", group_autocreate=False):
            self._get_and_validate_group(group, group_autocreate).discard_element(element)

        def has_element(self, element, group="General", group_autocreate=False):
            return self._get_and_validate_group(group, group_autocreate).has_element(element)

        def iteration_content(self, disable_error=True):
            self._update_fps()
            query = self._query

            for group in self.get_sorted_groups():
                if not query and not group.is_enabled:
                    continue

                header_pending = bool(query)
                for content in group.iteration_content(disable_error, query):
                    if header_pending:
                        header_pending = False
                        box = renpy.store.VBox()
                        box.add(group.header)
                        box.add(content)
                        content = box
                    yield content

        def count_element_states(self):
            active_el = inactive_el = 0
            for group in self.get_sorted_groups():
                active, inactive = group.count_element_states()
                active_el += active
                inactive_el += inactive

            return active_el, inactive_el

        def count_total_elements(self):
            total_elements = 0
            for group in self.get_sorted_groups():
                total_elements += group.count_total_elements()
            return total_elements

        def _validate_group(self, name, group_autocreate):
            name = to_text(name)
            if not self.has_group(name):
                if not group_autocreate:
                    raise FNaSRValueError("Группы '{}' не существует".format(name))
                self.create_group(name)

        def _get_and_validate_group(self, name, group_autocreate):
            self._validate_group(name, group_autocreate)
            return self.get_group(name)

        def _register(self, group, overwrite):
            if not isinstance(group, DebugGroup):
                if isinstance(group, dict):
                    group = DebugGroup(**group)
                elif isinstance(group, Iterable) and not is_string(group) and 0 < len(group) <= 3:
                    group = DebugGroup(*group)
                else:
                    raise FNaSRTypeError("group должен быть 'DebugGroup', получено: {}.".format(type(group)))
            if not overwrite and group.name in self._groups:
                raise FNaSRException("Группа '{}' уже существует".format(group.name))

            self._groups[group.name] = group

        def __iter__(self):
            return iter(list(self._groups))

        def __contains__(self, item):
            return self.has_group(item)

        def __len__(self):
            return len(self._groups)

    class DebugQueryInput(renpy.store.InputValue):
        default = True

        def get_text(self):
            return debug.query_raw

        def set_text(self, s):
            debug.set_query(s)

    debug = Debug()
    debug_query_input = DebugQueryInput()
    debug.create_group("Debug", order=-1)
    debug.create_group("System")
    debug.create_group("Player", order=1)
    debug.create_group("Location", order=2)
    debug.create_group("Night", order=3)
    debug.create_group("Enemy", order=4)

init python in v1FNaSR:
    _len = get_builtin("len")

    def _button_debug_activate(context):
        if debug.is_activity:
            debug.deactivate()
        else:
            debug.activate()
        renpy.restart_interaction()

    def _text_count_element_states(context):
        enabled, disabled = debug.count_element_states()
        return "total elements: {}\nenabled elements: {}\ndisabled elements: {}".format(enabled+disabled, enabled, disabled)

    debug.add_element(DebugText(lambda context: "calls per second: {}".format(debug.calls_per_second), style="v1_text_16_style_FNaSR"), group="Debug")
    debug.add_element(DebugText(_text_count_element_states, order=1), group="Debug")
    debug.add_element(DebugButton(
        lambda context: "Debug update: {}".format("{color=#0ac80a}active{/color}" if debug.is_activity else "{color=#c80a0a}inactive{/color}"),
        _button_debug_activate, order=2),
        group="Debug")

    debug.add_element(DebugFold(
        "Render / GC",
        DebugText(lambda context: "render fps: {:.2f}".format(get_render_fps()), order=-3),
        DebugText(lambda context: "average render fps: {:.2f}".format(get_average_render_fps()), order=-2),
        DebugText(lambda context: "Количество мусора: {}".format(_len(renpy.gc.garbage)), order=-1),
        DebugText(lambda context: "redraw queue: {}".format(_len(renpy.display.render.redraw_queue)), order=0),
        DebugText(lambda context: "Уникальных displayables: {}".format(_len(set(id(d) for _, d in renpy.display.render.redraw_queue))), order=1),
        DebugText(lambda context: "Размер кэша displayables: {}".format(_len(renpy.display.render.render_cache)), order=2),
        DebugText(lambda context: "Размер кэша renders: {}".format(sum(_len(renders) for renders in renpy.display.render.render_cache.values())), order=3),
        expanded=True
    ))

    @main_thread_only
    def _v1_debug_screen_callback(screen_names, state, **kwargs):
        if state == "show" and is_debug():
            for screen_name in screen_names:
                renpy.show_screen(screen_name, **kwargs)
            return

        if state == "hide":
            for screen_name in screen_names:
                renpy.hide_screen(screen_name, **kwargs)

    register_screen("debug", "V1DebugScreenFNaSR", callback=_v1_debug_screen_callback)

    del _button_debug_activate
    del _text_count_element_states
    del _v1_debug_screen_callback

screen V1DebugScreenFNaSR(target_cps=15, elements_in_row=4, max_len_name_group=10, panel_width=0.3, panel_height=0.8, panel_background=None, scroll_drag=False, show_search=True, show_separators=False):
    zorder 100
    default target_dt = v1FNaSR.get_target_dt(target_cps)
    default show_menu = True

    key "K_BACKQUOTE" action SetScreenVariable("show_menu", not show_menu)

    if show_menu and v1FNaSR.debug.is_activity:
        timer target_dt repeat True action Function(renpy.restart_interaction)

    if show_menu:
        frame:
            background panel_background
            padding (0, 0)
            xsize panel_width

            vbox:
                spacing 2

                for groups in v1FNaSR.debug.get_group_rows(elements_in_row):
                    hbox:
                        for group in groups:
                            textbutton group.label(max_len_name_group):
                                style "v1_move_location_button_FNaSR"
                                text_style "v1_text_16_mod_button_FNaSR"
                                xalign 0.0
                                action Function(v1FNaSR.debug.toggle_group, group.name)

                if show_search:
                    hbox:
                        spacing 8
                        if v1FNaSR.debug.is_input_mode:
                            key "game_menu" action Function(v1FNaSR.debug.disenable_input_mode)
                            key "K_KP_ENTER" action Function(v1FNaSR.debug.disenable_input_mode)
                            text "Поиск:" style "v1_text_16_style_FNaSR"
                            input:
                                value v1FNaSR.debug_query_input
                                length 40
                                xminimum 140
                                color "#ffffff"
                                size 16
                        else:
                            textbutton "Поиск: {}".format(v1FNaSR.debug.query_raw):
                                style "v1_move_location_button_FNaSR"
                                text_style "v1_text_16_style_FNaSR" 
                                action Function(v1FNaSR.debug.enable_input_mode)
                        textbutton "{color=#c80a0a}X{/color}":
                            style "v1_move_location_button_FNaSR"
                            text_style "v1_text_16_mod_button_FNaSR"
                            action Function(v1FNaSR.debug.clear_query)
                        textbutton v1FNaSR.debug.mode_label:
                            style "v1_move_location_button_FNaSR"
                            text_style "v1_text_16_mod_button_FNaSR"
                            action Function(v1FNaSR.debug.toggle_solo)

                viewport:
                    id "v1_debug_viewport_FNaSR"
                    mousewheel True
                    draggable scroll_drag
                    yfill False
                    ymaximum int(config.screen_height * panel_height)

                    vbox:
                        for content in v1FNaSR.debug.iteration_content():
                            add content xalign 0.0
                            if show_separators:
                                text "---------------" style "v1_text_16_style_FNaSR"
