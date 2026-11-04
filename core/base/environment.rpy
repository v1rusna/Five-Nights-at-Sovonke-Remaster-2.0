# -*- coding: utf-8 -*-
# core/base/environment.rpy
init -5 python in v1FNaSR:
    import threading as _threading
    import re as _re
    import keyword as _keyword
    import copy as _copy

    class EngineStateSnapshot(native_object):
        __slots__ = ("_snapshots", "_lock",)

        def __init__(self):
            self._snapshots = dict()
            self._lock = _threading.RLock()
            
        def capture(self, attr_path, new_value=MISSING, copy_fn=None):
            if copy_fn is not None and not callable(copy_fn):
                raise FNaSRTypeError("'copy_fn' must be callable; received: {}".format(type(copy_fn)))

            with self._lock:
                parts = self._split(attr_path)
                last_obj = renpy
                current_obj = renpy
                
                for part in parts:
                    self._validate_attr(part)
                    try:
                        last_obj = current_obj
                        current_obj = getattr(current_obj, part)
                    except AttributeError as e:
                        raise FNaSRAttributeError(e)

                if copy_fn is not None:
                    self._snapshots[attr_path] = copy_fn(current_obj)
                else:
                    try:
                        self._snapshots[attr_path] = _copy.deepcopy(current_obj)
                    except Exception:
                        self._snapshots[attr_path] = current_obj

                if new_value is not MISSING:
                    last_attr = parts[-1]
                    setattr(last_obj, last_attr, new_value)

        def safe_capture(self, attr_path, new_value=MISSING, copy_fn=None):
            if  copy_fn is not None and not callable(copy_fn):
                raise FNaSRTypeError("'copy_fn' must be callable; received: {}".format(type(copy_fn)))
            try:
                self.capture(attr_path, new_value, copy_fn)
            except Exception as e:
                log.write("warning | Unable to save the attribute path '{}': {}".format(attr_path, e))

        def restore(self, attr_path, copy_fn=None):
            if  copy_fn is not None and not callable(copy_fn):
                raise FNaSRTypeError("'copy_fn' must be callable; received: {}".format(type(copy_fn)))
            with self._lock:
                if attr_path not in self._snapshots:
                    raise FNaSRKeyError("Key '{}' was not found.".format(attr_path))

                parts = self._split(attr_path)
                saved_value = self._snapshots[attr_path]

                current_obj = renpy
                for part in parts[:-1]:
                    self._validate_attr(part)
                    try:
                        current_obj = getattr(current_obj, part)
                    except AttributeError as e:
                        raise FNaSRAttributeError(e)

                last_attr = parts[-1]
                self._validate_attr(last_attr)

                if copy_fn is not None:
                    restored_value = copy_fn(saved_value)
                else:
                    try:
                        restored_value = _copy.deepcopy(saved_value)
                    except Exception:
                        restored_value = saved_value

                setattr(current_obj, last_attr, restored_value)

        def safe_restore(self, attr_path, copy_fn=None):
            if  copy_fn is not None and not callable(copy_fn):
                raise FNaSRTypeError("'copy_fn' must be callable; received: {}".format(type(copy_fn)))
            try:
                self.restore(attr_path, copy_fn)
            except Exception as e:
                log.write("warning | Unable to restore the attribute path '{}': {}".format(attr_path, e))

        def restore_all(self, copy_fn_map=None):
            if copy_fn_map is None:
                copy_fn_map = dict()
            if not isinstance(copy_fn_map, dict):
                raise FNaSRTypeError("'copy_fn_map' must be a dictionary or None; received: {}".format(type(copy_fn_map)))
            for attr_path, copy_fn in iter_items(copy_fn_map):
                if not is_string(attr_path):
                    raise FNaSRTypeError("Key 'copy_fn_map[{}]' must be a string; received: '{}'".format(repr(attr_path), type(attr_path)))
                if  copy_fn is not None and not callable(copy_fn):
                    raise FNaSRTypeError("'copy_fn' must be callable; received: {}".format(type(copy_fn)))

            with self._lock:
                result = {True: [], False: []}
                for attr_path in list(self._snapshots.keys()):
                    try:
                        self.restore(attr_path, copy_fn_map.get(attr_path))
                        result[True].append(attr_path)
                    except Exception:
                        result[False].append(attr_path)

                return tuple(result[True]), tuple(result[False])

        def is_capture(self, attr_path):
            with self._lock:
                return attr_path in self._snapshots

        def _split(self, attr_path):
            if not is_string(attr_path):
                raise FNaSRTypeError("Path must be a string.")
            return attr_path.split(".")

        def _validate_attr(self, attr):
            if not is_string(attr):
                raise FNaSRTypeError("The attribute name must be a string; result: {}".format(type(attr)))
                
            if not _re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', attr):
                raise FNaSRValueError("The attribute name '{}' is invalid in Python.".format(attr))
                
            if _keyword.iskeyword(attr):
                raise FNaSRValueError("Python keywords ({}) are not allowed.".format(attr))
                
            return attr

        def __contains__(self, attr_path):
            return self.is_capture(attr_path)

        def __enter__(self):
            self._lock.acquire()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            try:
                self._lock.release()
            except RuntimeError:
                pass
            return False

    state_snapshot = EngineStateSnapshot()
