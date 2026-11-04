# -*- coding: utf-8 -*-
# core/gameloop/validator.rpy
init -5 python in v1FNaSR:
    import threading as _threading
    import collections as _collections
    import functools as _functools
    import traceback as _traceback

    class ValidatorTools:
        DEFAULT_GROUP = "FNaSR"

        ValidationResult = _collections.namedtuple("ValidationResult", ("validator", "executed", "passed", "details"))

        @staticmethod
        def call_helper(fn):
            @_functools.wraps(fn)
            def wrapper(*args, **kwargs):
                if is_main_thread():
                    return fn(*args, **kwargs)
                return main_executor.submit_and_wait(fn, *args, **kwargs)
            return wrapper

        @staticmethod
        def _expect(value, predicate, name, expected):
            if not predicate(value):
                raise FNaSRTypeError("'{}' должен быть {}, получено: {}".format(name, expected, type(value)))

        @staticmethod
        def _to_group(group):
            if group is None:
                return ValidatorGroup.current()
            if is_string(group):
                return ValidatorGroup.get(group)
            ValidatorTools._expect(group, lambda g: isinstance(g, ValidatorGroup), "group", "'ValidatorGroup', строкой или None")
            return group


        @staticmethod
        def validate():
            error, msg, results = Validator.validate_all()
            if error:
                raise ValidateError(msg)


    class ValidatorGroup(native_object):
        __slots__ = ("_name", "_validators")

        _registry = _collections.OrderedDict()
        _current = None
        _lock = _threading.RLock()

        @classmethod
        def create(cls, name):
            return cls(name)

        @classmethod
        def get(cls, name):
            with cls._lock:
                group = cls._registry.get(name)
            if group is None:
                raise FNaSRValueError("Группа валидаторов '{}' не найдена.".format(name))
            return group

        @classmethod
        def all_groups(cls):
            with cls._lock:
                return tuple(cls._registry.values())

        @classmethod
        def delete(cls, name):
            if name == ValidatorTools.DEFAULT_GROUP:
                raise FNaSRValueError("Группу '{}' удалять нельзя.".format(ValidatorTools.DEFAULT_GROUP))
            with cls._lock:
                group = cls.get(name)
                del cls._registry[name]
                if cls._current is group:
                    cls._current = cls._registry[ValidatorTools.DEFAULT_GROUP]


        @classmethod
        def select(cls, group):
            with cls._lock:
                if group is None:
                    group = cls._registry[ValidatorTools.DEFAULT_GROUP]
                else:
                    group = ValidatorTools._to_group(group)

                    if cls._registry.get(group.name) is not group:
                        raise FNaSRValueError("Группа '{}' не зарегистрирована.".format(group.name))

                cls._current = group
                return group

        @classmethod
        def current(cls):
            with cls._lock:
                return cls._current


        def __init__(self, name):
            ValidatorTools._expect(name, is_string, "name", "строкой")
            self._name = name
            self._validators = _collections.OrderedDict()
            with self._lock:
                if name in self._registry:
                    raise FNaSRValueError("Группа валидаторов '{}' уже существует.".format(name))
                self._registry[name] = self

        @property
        def name(self):
            return self._name


        def add(self, validator, replace=False):
            ValidatorTools._expect(validator, lambda v: isinstance(v, Validator), "validator", "'Validator'")
            with self._lock:
                if validator.name in self._validators and not replace:
                    raise FNaSRValueError("Валидатор '{}' уже есть в группе '{}'.".format(validator.name, self._name))
                self._validators[validator.name] = validator

        def replace(self, validator):
            ValidatorTools._expect(validator, lambda v: isinstance(v, Validator), "validator", "'Validator'")
            with self._lock:
                if validator.name not in self._validators:
                    raise FNaSRValueError("Валидатор '{}' не найден в группе '{}'.".format(validator.name, self._name))
                self._validators[validator.name] = validator

        def remove(self, validator):
            name = validator.name if isinstance(validator, Validator) else validator
            with self._lock:
                if name not in self._validators:
                    raise FNaSRValueError("Валидатор '{}' не найден в группе '{}'.".format(name, self._name))
                del self._validators[name]

        def clear(self):
            with self._lock:
                self._validators.clear()


        def get_validators(self):
            with self._lock:
                return tuple(self._validators.values())

        def __contains__(self, name):
            with self._lock:
                return name in self._validators

        def __len__(self):
            with self._lock:
                return len(self._validators)


        @ValidatorTools.call_helper
        def validate_all(self):
            lines = [Validator._FAIL_HEADER, "Список валидации (группа '{}'):".format(self._name)]
            results = []

            for validator in self.get_validators():
                try:
                    passed = validator.validate()
                    executed = True
                    details = "OK" if passed else validator.message
                except Exception:
                    passed = executed = False
                    details = "validate exception: {}".format(_traceback.format_exc())

                lines.append("{}: {}".format(validator.name, details))
                results.append(ValidatorTools.ValidationResult(validator, executed, passed, details))

            error = not all(r.passed for r in results)
            return error, "\n".join(lines), tuple(results)

        def __repr__(self):
            return "{}({})".format(type(self).__name__, self._name)

    ValidatorGroup._current = ValidatorGroup(ValidatorTools.DEFAULT_GROUP)

    class Validator(native_object):
        __slots__ = ("_name", "_message", "_condition_fn", "_correction_fn", "_last_result")

        _FAIL_HEADER = (
            "\nИгровой цикл не прошел валидацию.\nПерезапустите игру либо обратитесь "
            "к 'v1rus team'.\ntelegram channel: https://t.me/+VewEitmB66k0MmQy"
        )

        @staticmethod
        def select_group(group):
            return ValidatorGroup.select(group)

        @staticmethod
        def current_group():
            return ValidatorGroup.current()

        @staticmethod
        def get_validators(group=None):
            return ValidatorTools._to_group(group).get_validators()

        @staticmethod
        def validate_all(group=None):
            return ValidatorTools._to_group(group).validate_all()


        def __init__(self, name, message_error, condition_fn, correction_fn=None, groups=None):
            ValidatorTools._expect(name, is_string, "name", "строкой")
            ValidatorTools._expect(message_error, is_string, "message_error", "строкой")
            ValidatorTools._expect(condition_fn, callable, "condition_fn", "вызываемым")
            ValidatorTools._expect(correction_fn, lambda f: f is None or callable(f), "correction_fn", "вызываемым или None")

            self._name = name
            self._message = message_error
            self._condition_fn = condition_fn
            self._correction_fn = correction_fn
            self._last_result = None

            if groups is None or is_string(groups) or isinstance(groups, ValidatorGroup):
                groups = (groups,)

            added = []
            try:
                for group in [ValidatorTools._to_group(g) for g in groups]:
                    group.add(self)
                    added.append(group)
            except Exception:
                for group in added:
                    group.remove(self)
                raise

        @property
        def name(self):
            return self._name

        @property
        def message(self):
            return self._message

        @property
        def last_result(self):
            return self._last_result

        @ValidatorTools.call_helper
        def validate(self):
            if self._check():
                return True
            if self._correction_fn is None:
                return False
            self._correction_fn()
            return self._check()

        def _check(self):
            self._last_result = None
            self._last_result = bool(self._condition_fn())
            return self._last_result

        def __repr__(self):
            return "{}({})".format(type(self).__name__, self._name)


    class ValidateError(Exception):
        def __init__(self, message):
            super(ValidateError, self).__init__("{} | {}".format(FNaSRException.PREFIX, message))

    control_exceptions.register(ValidateError)

