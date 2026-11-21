"""Deterministic JSON config identity; callers must supply a complete run spec."""
import hashlib
import json
import math


def _validate(value):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _validate(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _validate(item)
        return
    raise ValueError("Config must contain only finite JSON values and string keys")


def fingerprint(spec):
    if type(spec) is not dict or not spec:
        raise ValueError("Config must be a nonempty JSON object")
    _validate(spec)
    payload = json.dumps(spec, sort_keys=True, ensure_ascii=True,
                         allow_nan=False, separators=(",", ":"))
    return hashlib.sha256(("aurel-config-v1\n" + payload).encode("utf-8")).hexdigest()


def require_same_config(saved, current):
    if fingerprint(saved) != fingerprint(current):
        raise ValueError("Config changed; use a new run instead of reusing results")
