# -*- coding: utf-8 -*-
# core/reset.rpy
init -10 python in v1FNaSR:
    class ResetLogicCode(native_object):
        VALUE = 0    # присвоить по ссылке: атомы, неизменяемые кортежи, frozenset, чужие объекты
        LIST = 1     # список: восстановить содержимое на месте
        DICT = 2     # словарь: восстановить содержимое на месте
        CHILD = 3    # вложенный ResetLogic: вызвать его reset()
        SET = 4      # множество: восстановить содержимое на месте
        CLONE = 5    # присвоить свежую копию (кортеж с вложенными контейнерами)
        NO_ATTR = object()


    class ResetLogic(native_object):
        def __init__(self):
            super(ResetLogic, self).__init__()
            state = native_object.__getattribute__(self, '__dict__')
            state['_reset_to_default'] = dict()
            state['_fast_reset'] = None

        @staticmethod
        def _empty_like(proto):
            cls = type(proto)
            if cls is list or cls is dict or cls is set:
                return cls()
            if isinstance(proto, dict):
                factory = getattr(proto, 'default_factory', ResetLogicCode.NO_ATTR)  # defaultdict
                if factory is not ResetLogicCode.NO_ATTR:
                    return cls(factory)
            return cls()

        @staticmethod
        def _rebuild_tuple(proto, items):
            cls = type(proto)
            if cls is tuple:
                return tuple(items)
            make = getattr(cls, '_make', None)
            return make(items) if make is not None else cls(items)

        @staticmethod
        def _clone(val, memo=None):
            if isinstance(val, ResetLogic):
                return val
            if not isinstance(val, (list, dict, set, tuple)):
                return val

            if memo is None:
                memo = {}
            else:
                done = memo.get(id(val))
                if done is not None:
                    return done

            clone = ResetLogic._clone
            if isinstance(val, list):
                new = ResetLogic._empty_like(val)
                memo[id(val)] = new
                new.extend([clone(x, memo) for x in val])
                return new
            if isinstance(val, dict):
                new = ResetLogic._empty_like(val)
                memo[id(val)] = new
                new.update([(k, clone(v, memo)) for k, v in val.items()])
                return new
            if isinstance(val, set):
                new = ResetLogic._empty_like(val)
                memo[id(val)] = new
                new.update(val)
                return new

            items = [clone(x, memo) for x in val]
            result = val
            for new_item, old_item in zip(items, val):
                if new_item is not old_item:
                    result = ResetLogic._rebuild_tuple(val, items)
                    break
            memo[id(val)] = result
            return result

        @staticmethod
        def _is_deep(val):
            if isinstance(val, (list, dict, set)):
                return True
            if isinstance(val, tuple):
                for x in val:
                    if ResetLogic._is_deep(x):
                        return True
            return False

        @staticmethod
        def _collect_children(val, out, seen):
            if isinstance(val, ResetLogic):
                if id(val) not in seen:
                    seen.add(id(val))
                    out.append(val)
                return
            if not isinstance(val, (list, tuple, set, frozenset, dict)):
                return
            if id(val) in seen:
                return
            seen.add(id(val))
            collect = ResetLogic._collect_children
            if isinstance(val, dict):
                for k, v in val.items():
                    collect(k, out, seen)
                    collect(v, out, seen)
            else:
                for x in val:
                    collect(x, out, seen)

        @staticmethod
        def _raw_get(obj, attr):
            try:
                return native_object.__getattribute__(obj, attr)
            except AttributeError:
                return None

        @staticmethod
        def _log_error(message):
            try:
                log.error(message)
            except Exception:
                pass

        @staticmethod
        def make_reset_method(default_dict, raw=()):
            if not default_dict:
                def reset_nothing(self):
                    return None
                return reset_nothing

            OP_VALUE = ResetLogicCode.VALUE
            OP_LIST = ResetLogicCode.LIST
            OP_DICT = ResetLogicCode.DICT
            OP_CHILD = ResetLogicCode.CHILD
            OP_SET = ResetLogicCode.SET
            OP_CLONE = ResetLogicCode.CLONE

            ops = []
            for attr, snap in default_dict.items():
                is_raw = attr in raw
                setter = native_object.__setattr__ if is_raw else setattr

                if isinstance(snap, ResetLogic):
                    ops.append((attr, OP_CHILD, snap, False, (), is_raw, setter))
                    continue

                children = []
                ResetLogic._collect_children(snap, children, set())

                deep = False
                if isinstance(snap, list):
                    op = OP_LIST
                    deep = any(ResetLogic._is_deep(x) for x in snap)
                elif isinstance(snap, dict):
                    op = OP_DICT
                    deep = any(ResetLogic._is_deep(v) for v in snap.values())
                elif isinstance(snap, set):
                    op = OP_SET
                elif ResetLogic._is_deep(snap):
                    op = OP_CLONE
                else:
                    op = OP_VALUE
                ops.append((attr, op, snap, deep, tuple(children), is_raw, setter))

            ops = tuple(ops)
            clone = ResetLogic._clone
            raw_get = ResetLogic._raw_get

            def reset(self):
                attr = None
                try:
                    for attr, op, snap, deep, children, is_raw, setter in ops:
                        if op == OP_VALUE:
                            setter(self, attr, snap)
                        elif op == OP_LIST:
                            cur = raw_get(self, attr) if is_raw else getattr(self, attr, None)
                            if isinstance(cur, list):
                                if deep:
                                    memo = {id(snap): cur}  # ссылки на сам список ведут на cur
                                    cur[:] = [clone(x, memo) for x in snap]
                                else:
                                    cur[:] = snap
                            else:
                                setter(self, attr, clone(snap))
                        elif op == OP_DICT:
                            cur = raw_get(self, attr) if is_raw else getattr(self, attr, None)
                            if isinstance(cur, dict):
                                cur.clear()
                                if snap:
                                    if deep:
                                        memo = {id(snap): cur}
                                        cur.update([(k, clone(v, memo)) for k, v in snap.items()])
                                    else:
                                        cur.update(snap)
                            else:
                                setter(self, attr, clone(snap))
                        elif op == OP_CHILD:
                            cur = raw_get(self, attr) if is_raw else getattr(self, attr, None)
                            if cur is not snap:
                                setter(self, attr, snap)
                                cur = snap
                            cur.reset()
                            continue
                        elif op == OP_SET:
                            cur = raw_get(self, attr) if is_raw else getattr(self, attr, None)
                            if isinstance(cur, set):
                                cur.clear()
                                if snap:
                                    cur.update(snap)
                            else:
                                setter(self, attr, clone(snap))
                        else:  # OP_CLONE
                            setter(self, attr, clone(snap))

                        for child in children:
                            child.reset()
                except Exception:
                    ResetLogic._log_error("ResetLogic | %s.reset: error on attribute %r" % (type(self).__name__, attr))
                    raise

            return reset

        def _setattr(self, attr, val, use_object=False):
            state = native_object.__getattribute__(self, '__dict__')

            default = state.get('_reset_to_default')
            if not isinstance(default, dict):
                default = state['_reset_to_default'] = dict()

            if use_object:
                native_object.__setattr__(self, attr, val)
                current = native_object.__getattribute__(self, attr)
            else:
                setattr(self, attr, val)
                current = getattr(self, attr)

            default[attr] = self._clone(current)

            raw = state.get('_reset_raw')
            if use_object:
                if raw is None:
                    raw = state['_reset_raw'] = set()
                raw.add(attr)
            elif raw is not None:
                raw.discard(attr)

            state['_fast_reset'] = None

        def reset(self):
            state = native_object.__getattribute__(self, '__dict__')
            if state.get('_reset_active'):
                return

            fast_reset = state.get('_fast_reset')
            if fast_reset is None:
                default = state.get('_reset_to_default')
                if not isinstance(default, dict):
                    return
                fast_reset = self.make_reset_method(default, state.get('_reset_raw', ()))
                state['_fast_reset'] = fast_reset

            state['_reset_active'] = True
            try:
                fast_reset(self)
            finally:
                state['_reset_active'] = False
