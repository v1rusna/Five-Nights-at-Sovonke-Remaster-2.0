# night.rpy
init -1 python in v1FNaSR:

    from collections import OrderedDict

    MAIN_SEQUENCE = "main"

    def _check_text_id(value, what):
        """Проверяет, что значение — непустая строка."""
        if not is_string(value):
            raise FNaSRTypeError("{} должен быть строкой, передано: {}.".format(what, type(value)))

        if not value:
            raise FNaSRException("{} не может быть пустым.".format(what))


    class NightLockedError(FNaSRException):
        """Ночь ещё не открыта."""


    class Night(object):
        __slots__ = (
            "_id", "_title", "_start_location_id", "_end_of_shift",
            "_requires", "_start_callback", "_end_callback"
        )

        def __init__(
            self,
            night_id,
            title=None,
            start_location_id=None,
            end_of_shift=6,
            requires=(),
            start_callback=None,
            end_callback=None
        ):
            _check_text_id(night_id, "night_id")

            if title is None:
                title = night_id
            else:
                _check_text_id(title, "title")

            if start_location_id is not None and not is_integer(start_location_id):
                raise FNaSRTypeError("start_location_id должен быть 'int', передано: {}.".format(type(start_location_id)))

            if not is_integer(end_of_shift):
                raise FNaSRTypeError("end_of_shift должен быть 'int', передано: {}.".format(type(end_of_shift)))

            if is_string(requires):
                requires = (requires,)

            requires = tuple(requires)

            for dep in requires:
                _check_text_id(dep, "requires")

            if night_id in requires:
                raise FNaSRException("Ночь '{}' не может зависеть от самой себя.".format(night_id))

            if start_callback is not None and not callable(start_callback):
                raise FNaSRTypeError("start_callback должен быть вызываемым, передано: {}.".format(type(start_callback)))

            if end_callback is not None and not callable(end_callback):
                raise FNaSRTypeError("end_callback должен быть вызываемым, передано: {}.".format(type(end_callback)))

            self._id = night_id
            self._title = title
            self._start_location_id = start_location_id
            self._end_of_shift = end_of_shift
            self._requires = requires
            self._start_callback = start_callback
            self._end_callback = end_callback

        @property
        def id(self):
            return self._id

        @property
        def title(self):
            return self._title

        @property
        def start_location_id(self):
            return self._start_location_id

        @property
        def end_of_shift(self):
            return self._end_of_shift

        @property
        def requires(self):
            return self._requires

        def call_start(self):
            if self._start_callback is not None:
                self._start_callback(self)

        def call_end(self, completed):
            if self._end_callback is not None:
                self._end_callback(self, completed)

        def __repr__(self):
            return "<Night {!r}>".format(self._id)


    class NightSequence(object):
        __slots__ = ("_name", "_ordered_unlock", "_ids")

        def __init__(self, name, ordered_unlock=True):
            _check_text_id(name, "name")
            self._name = name
            self._ordered_unlock = bool(ordered_unlock)
            self._ids = []

        @property
        def name(self):
            return self._name

        @property
        def ordered_unlock(self):
            """Открывается ли ночь только после прохождения предыдущей."""
            return self._ordered_unlock

        @property
        def ids(self):
            return tuple(self._ids)

        @property
        def first(self):
            return self._ids[0] if self._ids else None

        @property
        def last(self):
            return self._ids[-1] if self._ids else None

        def __len__(self):
            return len(self._ids)

        def __iter__(self):
            return iter(self._ids)

        def __contains__(self, night_id):
            return night_id in self._ids

        def index_of(self, night_id):
            try:
                return self._ids.index(night_id)
            except ValueError:
                raise FNaSRKeyError("Ночь '{}' не входит в последовательность '{}'.".format(night_id, self._name))

        def get_next(self, night_id):
            i = self.index_of(night_id) + 1
            return self._ids[i] if i < len(self._ids) else None

        def get_previous(self, night_id):
            i = self.index_of(night_id)
            return self._ids[i - 1] if i > 0 else None

        def _append(self, night_id):
            self._ids.append(night_id)

        def _insert_after(self, anchor_id, night_id):
            self._ids.insert(self.index_of(anchor_id) + 1, night_id)

        def _remove(self, night_id):
            self._ids.remove(night_id)


    class NightSystem(object):
        def __init__(self):
            self._nights = OrderedDict()
            self._sequences = OrderedDict()
            self._completed = set()
            self._loaded = None
            self._running = False

            self.create_sequence(MAIN_SEQUENCE)

        # ----- Регистрация ночей --------------------------------------

        def register_night(
            self,
            night_id,
            title=None,
            start_location_id=None,
            end_of_shift=6,
            requires=(),
            start_callback=None,
            end_callback=None,
            sequence=None,
            after=None
        ):
            if night_id in self._nights:
                raise FNaSRException("Ночь '{}' уже существует.".format(night_id))

            night = Night(
                night_id,
                title=title,
                start_location_id=start_location_id,
                end_of_shift=end_of_shift,
                requires=requires,
                start_callback=start_callback,
                end_callback=end_callback
            )

            for dep in night.requires:
                if dep not in self._nights:
                    raise FNaSRKeyError("Для ночи '{}' указана зависимость '{}', но она не зарегистрирована.".format(night.id, dep))

            seq_name = sequence

            if after is not None:
                anchor_seq = self._find_sequence(self._resolve(after).id)

                if anchor_seq is None:
                    raise FNaSRException("Ночь '{}' не входит ни в одну последовательность, после неё нельзя вставить.".format(after))

                if sequence is not None and sequence != anchor_seq.name:
                    raise FNaSRException("Ночь '{}' находится в '{}', а не в '{}'.".format(after, anchor_seq.name, sequence))

                seq_name = anchor_seq.name

            elif sequence is not None:
                self.get_sequence(sequence)

            self._nights[night.id] = night

            if seq_name is not None:
                try:
                    self.add_to_sequence(night, seq_name, after=after)
                except Exception:
                    del self._nights[night.id]
                    raise

            return night

        def unregister_night(self, night):
            night = self._resolve(night)

            if self._loaded is night:
                raise FNaSRException("Нельзя удалить загруженную ночь '{}'.".format(night.id))

            for other in self._nights.values():
                if night.id in other.requires:
                    raise FNaSRException("Ночь '{}' не может быть удалена, так как от неё зависит ночь '{}'.".format(night.id, other.id))

            seq = self._find_sequence(night.id)

            if seq is not None:
                seq._remove(night.id)

            del self._nights[night.id]
            self._completed.discard(night.id)

        def has_night(self, night):
            if isinstance(night, Night):
                return self._nights.get(night.id) is night

            return night in self._nights

        def get_night(self, night):
            return self._resolve(night)

        def get_all_nights(self):
            return list(self._nights.values())

        # ----- Последовательности ------------------------------------

        def create_sequence(self, name, ordered_unlock=True):
            if name in self._sequences:
                raise FNaSRException("Последовательность '{}' уже существует.".format(name))

            seq = NightSequence(name, ordered_unlock)
            self._sequences[name] = seq
            return seq

        def delete_sequence(self, name):
            if name == MAIN_SEQUENCE:
                raise FNaSRException("Последовательность '{}' удалить нельзя.".format(name))

            self.get_sequence(name)
            del self._sequences[name]

        def has_sequence(self, name):
            return name in self._sequences

        def get_sequence(self, name=MAIN_SEQUENCE):
            try:
                return self._sequences[name]
            except KeyError:
                raise FNaSRKeyError("Последовательность '{}' не существует.".format(name))

        def add_to_sequence(self, night, sequence=MAIN_SEQUENCE, after=None):
            night = self._resolve(night)
            seq = self.get_sequence(sequence)
            current = self._find_sequence(night.id)

            if current is not None:
                raise FNaSRException("Ночь '{}' уже входит в последовательность '{}'.".format(night.id, current.name))

            if after is None:
                seq._append(night.id)
            else:
                anchor = self._resolve(after)

                if anchor.id not in seq:
                    raise FNaSRException("Ночь '{}' не входит в последовательность '{}'.".format(anchor.id, seq.name))

                seq._insert_after(anchor.id, night.id)

            try:
                self._check_reachable()
            except Exception:
                seq._remove(night.id)
                raise

            return night

        def remove_from_sequence(self, night):
            night = self._resolve(night)
            seq = self._find_sequence(night.id)

            if seq is None:
                raise FNaSRException("Ночь '{}' не входит ни в одну последовательность.".format(night.id))

            seq._remove(night.id)

        def validate(self):
            self._check_reachable()

        # ----- Навигация ---------------------------------------------

        def get_first_night(self, sequence=MAIN_SEQUENCE):
            first = self.get_sequence(sequence).first
            return None if first is None else self._nights[first]

        def get_last_night(self, sequence=MAIN_SEQUENCE):
            last = self.get_sequence(sequence).last
            return None if last is None else self._nights[last]

        def get_next_night(self, night):
            night = self._resolve(night)
            seq = self._find_sequence(night.id)

            if seq is None:
                return None

            next_id = seq.get_next(night.id)
            return None if next_id is None else self._nights[next_id]

        def get_previous_night(self, night):
            night = self._resolve(night)
            seq = self._find_sequence(night.id)

            if seq is None:
                return None

            prev_id = seq.get_previous(night.id)
            return None if prev_id is None else self._nights[prev_id]

        def has_next_night(self, night):
            return self.get_next_night(night) is not None

        def has_previous_night(self, night):
            return self.get_previous_night(night) is not None

        def get_nights(self, sequence=MAIN_SEQUENCE):
            """Ночи последовательности по порядку."""
            seq = self.get_sequence(sequence)
            return [self._nights[i] for i in seq.ids]

        def get_special_nights(self):
            """Ночи вне всех последовательностей."""
            return [
                n for n in self._nights.values()
                if self._find_sequence(n.id) is None
            ]

        def find_available_night(self, sequence=MAIN_SEQUENCE):
            """Первая не пройденная и открытая ночь последовательности
            или None (всё пройдено либо дальше путь закрыт)."""
            for night in self.get_nights(sequence):
                if night.id not in self._completed and self.is_unlocked(night):
                    return night

            return None

        def find_last_unlocked_night(self, sequence=MAIN_SEQUENCE):
            """Последняя открытая ночь последовательности или None
            (последовательность пуста либо закрыта даже первая ночь)."""
            for night in reversed(self.get_nights(sequence)):
                if self.is_unlocked(night):
                    return night

            return None

        def get_sequence_of(self, night):
            """Имя последовательности ночи или None."""
            seq = self._find_sequence(self._resolve(night).id)
            return None if seq is None else seq.name

        def is_special(self, night):
            return self.get_sequence_of(night) is None

        def get_position(self, night):
            """Позиция ночи в последовательности (с 1) или None."""
            night = self._resolve(night)
            seq = self._find_sequence(night.id)

            if seq is None:
                return None

            return seq.index_of(night.id) + 1

        # ----- Открытие и прогресс -----------------------------------

        def is_unlocked(self, night):
            night = self._resolve(night)
            return self._is_unlocked_with(night.id, self._completed)

        def is_completed(self, night):
            return self._resolve(night).id in self._completed

        def mark_completed(self, night):
            self._completed.add(self._resolve(night).id)

        def reset_progress(self):
            self._completed = set()

        def export_progress(self):
            """Список пройденных id в порядке регистрации (для сохранения)."""
            return [n for n in self._nights if n in self._completed]

        def import_progress(self, night_ids, ignore_unknown=False):
            """Заменяет прогресс. Неизвестный id — ошибка, если явно
            не указано ignore_unknown=True."""
            completed = set()

            for night_id in night_ids:
                if night_id in self._nights:
                    completed.add(night_id)
                elif not ignore_unknown:
                    raise FNaSRKeyError("Ночь '{}' из прогресса не зарегистрирована.".format(night_id))

            self._completed = completed

        # ----- Жизненный цикл ----------------------------------------

        @property
        def loaded(self):
            return self._loaded

        @property
        def is_running(self):
            return self._running

        def load(self, night, ignore_lock=False):
            night = self._resolve(night)

            if self._running:
                raise FNaSRException("Нельзя загрузить ночь, пока идёт '{}'.".format(self._loaded.id))

            if not ignore_lock and not self.is_unlocked(night):
                raise NightLockedError("Ночь '{}' ещё не открыта.".format(night.id))

            self._loaded = night

        def load_first(self, sequence=MAIN_SEQUENCE, ignore_lock=False):
            night = self.get_first_night(sequence)

            if night is None:
                raise FNaSRException("Последовательность '{}' пуста.".format(sequence))

            self.load(night, ignore_lock)

        def load_next(self, ignore_lock=False):
            if self._loaded is None:
                raise FNaSRException("Ни одна ночь не загружена.")

            night = self.get_next_night(self._loaded)

            if night is None:
                raise FNaSRException("После ночи '{}' нет следующей.".format(self._loaded.id))

            self.load(night, ignore_lock)

        def unload(self):
            if self._running:
                raise FNaSRException("Нельзя выгрузить ночь, пока она идёт.")

            self._loaded = None

        def start(self):
            """Начинает загруженную ночь и вызывает start_callback."""
            if self._loaded is None:
                raise FNaSRException("Ни одна ночь не загружена.")

            if self._running:
                raise FNaSRException("Ночь '{}' уже идёт.".format(self._loaded.id))

            self._running = True

            try:
                self._loaded.call_start()
            except Exception:
                self._running = False
                raise

        def finish(self, completed=True):
            if not self._running:
                raise FNaSRException("Нет идущей ночи.")

            night = self._loaded
            self._running = False

            if completed:
                self._completed.add(night.id)

            night.call_end(bool(completed))

        # ----- Внутреннее --------------------------------------------

        def _resolve(self, night):
            if isinstance(night, Night):
                if self._nights.get(night.id) is not night:
                    raise FNaSRKeyError("Ночь '{}' не зарегистрирована в этой системе.".format(night.id))

                return night

            if not is_string(night):
                raise FNaSRTypeError("Ночь должна быть 'str' или 'Night', передано: {}.".format(type(night)))

            try:
                return self._nights[night]
            except KeyError:
                raise FNaSRKeyError("Ночь '{}' не существует.".format(night))

        def _find_sequence(self, night_id):
            for seq in self._sequences.values():
                if night_id in seq:
                    return seq

            return None

        def _is_unlocked_with(self, night_id, completed):
            night = self._nights[night_id]

            for dep in night.requires:
                if dep not in completed:
                    return False

            seq = self._find_sequence(night_id)

            if seq is not None and seq.ordered_unlock:
                prev_id = seq.get_previous(night_id)

                if prev_id is not None and prev_id not in completed:
                    return False

            return True

        def _check_reachable(self):
            completed = set()
            progress = True

            while progress:
                progress = False

                for night_id in self._nights:
                    if night_id not in completed and self._is_unlocked_with(night_id, completed):
                        completed.add(night_id)
                        progress = True

            stuck = [n for n in self._nights if n not in completed]

            if stuck:
                raise FNaSRException("Ночи никогда не откроются (взаимная блокировка зависимостей и порядка): {}.".format(", ".join(stuck)))


    register_system("night", NightSystem())

    def _night_quit_fn():
        ns = require_system("night")
        if ns.is_running:
            ns.finish()
        ns.unload()
    add_quit_fn(_night_quit_fn)
    del _night_quit_fn

init python in v1FNaSR:
    _dsn = DebugSection(
        DebugText(lambda context: "Ночь: {}".format(context.ns.loaded.id), style="v1_text_16_style_FNaSR", order=0),
        DebugText(lambda context: "Следующая: {}".format(context.ns.get_next_night(context.ns.loaded).id if context.ns.get_next_night(context.ns.loaded) else "нет"), order=1),
        DebugText(lambda context: "Прошлая: {}".format(context.ns.get_previous_night(context.ns.loaded).id if context.ns.get_previous_night(context.ns.loaded) else "нет"), order=2),
        DebugText(lambda context: "title: {}".format(context.ns.loaded.title), order=3),
        DebugText(lambda context: "Конец смены в {}ч.".format(context.ns.loaded.end_of_shift), order=4),
        DebugText(lambda context: "Зависит от ночей: {}".format(context.ns.loaded.requires), order=5, condition=lambda context: len(context.ns.loaded.requires) > 0),
        order=0)

    _dsn.context.ns = require_system("night")

    debug.add_element(_dsn, group="Night")

    del _dsn
