"""Conservative relationships between a small subset of declared type values.

This is NOT runtime validator compatibility. Only a synthetic counterexample
can establish narrowing; unsupported annotations remain unknown.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin

_SCALARS = (str, int, float, bool, bytes, type(None))


@dataclass(frozen=True, slots=True)
class TypeEvidence:
    relation: Literal["included", "excluded", "unknown"]
    witness: str | None = None


def _branches(t: object) -> tuple[object, ...]:
    return get_args(t) if get_origin(t) in (Union, UnionType) else (t,)


def _matches(t: object, value: object, *, depth: int = 0) -> bool | None:
    if depth > 8:
        return None
    members = _branches(t)
    if len(members) > 1:
        answers = [_matches(m, value, depth=depth + 1) for m in members]
        if True in answers:
            return True
        return None if None in answers else False
    origin = get_origin(t)
    if origin is Literal:
        return any(type(value) is type(v) and value == v for v in get_args(t))
    if t in _SCALARS:
        return isinstance(value, t)
    if origin is list:
        args = get_args(t)
        if len(args) != 1:
            return None
        if not isinstance(value, list):
            return False
        answers = [_matches(args[0], v, depth=depth + 1) for v in value]
        return False if False in answers else None if None in answers else True
    if origin is dict:
        args = get_args(t)
        if len(args) != 2 or args[0] is not str:
            return None
        if not isinstance(value, dict):
            return False
        if any(not isinstance(k, str) for k in value):
            return False
        answers = [_matches(args[1], v, depth=depth + 1) for v in value.values()]
        return False if False in answers else None if None in answers else True
    if origin is tuple:
        args = get_args(t)
        if len(args) != 2 or args[1] is not Ellipsis:
            return None
        if not isinstance(value, tuple):
            return False
        answers = [_matches(args[0], v, depth=depth + 1) for v in value]
        return False if False in answers else None if None in answers else True
    return None


def _samples(t: object, *, depth: int = 0) -> tuple[object, ...]:
    if depth > 6:
        return ()
    members = _branches(t)
    if len(members) > 1:
        return tuple(x for m in members for x in _samples(m, depth=depth + 1))
    if get_origin(t) is Literal:
        return get_args(t)
    if t is str:
        return ("", "custom-extension", "string", "other")
    if t is int:
        return (0, 1, 42)
    if t is float:
        return (0.0, 1.5)
    if t is bool:
        return (False, True)
    if t is bytes:
        return (b"", b"x")
    if t is type(None):
        return (None,)
    origin, args = get_origin(t), get_args(t)
    if origin is list and len(args) == 1:
        return ([], *([x] for x in _samples(args[0], depth=depth + 1)))
    if origin is dict and len(args) == 2 and args[0] is str:
        return ({}, *({"key": x} for x in _samples(args[1], depth=depth + 1)))
    if origin is tuple and len(args) == 2 and args[1] is Ellipsis:
        return ((), *((x,) for x in _samples(args[0], depth=depth + 1)))
    return ()


def _finite(t: object) -> tuple[object, ...] | None:
    members = _branches(t)
    if len(members) > 1:
        values = [_finite(member) for member in members]
        if any(item is None for item in values):
            return None
        return tuple(x for item in values if item is not None for x in item)
    if get_origin(t) is Literal:
        return get_args(t)
    if t is type(None):
        return (None,)
    if t is bool:
        return (False, True)
    return None


def _subset_by_structure(old: object, new: object, depth: int = 0) -> bool | None:
    if old == new:
        return True
    if depth > 8 or old is Any or new is Any:
        return None
    parts = _branches(old)
    if len(parts) > 1:
        pieces = [_subset_by_structure(x, new, depth + 1) for x in parts]
        return True if all(x is True for x in pieces) else None
    options = _branches(new)
    if len(options) > 1:
        return True if any(_subset_by_structure(old, x, depth + 1)
                           is True for x in options) else None
    left, right = get_origin(old), get_origin(new)
    if old is bool and new is int:
        return True  # Static typing relation, not a strict runtime decoder.
    if left is Literal:
        return True if all(_matches(new, v) is True for v in get_args(old)) else None
    if old is type(None):
        return True if _matches(new, None) is True else None
    if left == right and left in (list, dict, tuple):
        a, b = get_args(old), get_args(new)
        if left is list and len(a) == len(b) == 1:
            return _subset_by_structure(a[0], b[0], depth + 1)
        if left is dict and len(a) == len(b) == 2 and a[0] is b[0] is str:
            return _subset_by_structure(a[1], b[1], depth + 1)
        if left is tuple and len(a) == len(b) == 2 and a[1] is b[1] is Ellipsis:
            return _subset_by_structure(a[0], b[0], depth + 1)
    return None


def assess_subset(allowed_before: object, allowed_after: object) -> TypeEvidence:
    """Assess declared subset inclusion; never infer unknown runtime behavior."""
    if allowed_before == allowed_after:
        return TypeEvidence("included")
    exhaustive = _finite(allowed_before)
    if exhaustive is not None:
        statuses = [_matches(allowed_after, value) for value in exhaustive]
        for value, status in zip(exhaustive, statuses):
            if status is False:
                return TypeEvidence("excluded", repr(value))
        if all(status is True for status in statuses):
            return TypeEvidence("included")
    for sample in _samples(allowed_before):
        if (_matches(allowed_before, sample) is True
                and _matches(allowed_after, sample) is False):
            return TypeEvidence("excluded", repr(sample))
    if _subset_by_structure(allowed_before, allowed_after) is True:
        return TypeEvidence("included")
    return TypeEvidence("unknown")
