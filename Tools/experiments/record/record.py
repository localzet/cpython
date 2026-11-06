"""Research prototype for fixed-shape objects with explicit mapping validation."""
from __future__ import annotations

from dataclasses import MISSING, dataclass, field, fields
from functools import lru_cache
from types import UnionType
from typing import (
    Any, Callable, Literal, TypeVar, Union, dataclass_transform,
    get_args, get_origin, get_type_hints, overload,
)

T = TypeVar("T", bound=type)
_RESERVED = frozenset(("from_mapping", "to_mapping"))


class RecordValidationError(TypeError):
    """A mapping value does not match its record schema."""


def _type_name(annotation: object) -> str:
    return getattr(annotation, "__name__", str(annotation))


def _valid(value: object, annotation: object) -> bool:
    """Check a deliberately limited annotation subset without coercion."""
    if annotation is Any or annotation is object:
        return True
    if annotation is None or annotation is type(None):
        return value is None

    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (Union, UnionType):
        return any(_valid(value, option) for option in args)
    if origin is Literal:
        return any(type(value) is type(item) and value == item
                   for item in args)
    if origin is list:
        return isinstance(value, list) and (
            not args or all(_valid(item, args[0]) for item in value))
    if origin is dict:
        return isinstance(value, dict) and (
            not args or all(_valid(k, args[0]) and _valid(v, args[1])
                            for k, v in value.items()))
    if origin is tuple:
        if not isinstance(value, tuple):
            return False
        if not args:
            return True
        if len(args) == 2 and args[1] is Ellipsis:
            return all(_valid(item, args[0]) for item in value)
        return len(args) == len(value) and all(
            _valid(item, expected)
            for item, expected in zip(value, args))
    if isinstance(annotation, type):
        # bool is a subclass of int; reject it for int schema fields.
        if annotation in (bool, int, float, str, bytes):
            return type(value) is annotation
        return isinstance(value, annotation)
    raise TypeError(f"Unsupported annotation {_type_name(annotation)}")


@lru_cache(maxsize=256)
def _schema(cls: type) -> tuple[tuple[str, object, bool], ...]:
    hints = get_type_hints(cls)
    return tuple(
        (f.name, hints[f.name],
         f.default is MISSING and f.default_factory is MISSING)
        for f in fields(cls)
    )


def _from_mapping(cls: type, data: Any):
    from collections.abc import Mapping
    if not isinstance(data, Mapping):
        raise RecordValidationError(f"{cls.__name__}: expected a mapping")
    schema = _schema(cls)
    names = {name for name, _, _ in schema}
    unexpected = set(data) - names
    if unexpected:
        raise RecordValidationError(
            f"{cls.__name__}: unknown fields {sorted(map(repr, unexpected))!r}")
    missing = [name for name, _, required in schema
               if required and name not in data]
    if missing:
        raise RecordValidationError(
            f"{cls.__name__}: missing fields {missing!r}")
    for name, annotation, _ in schema:
        if name in data and not _valid(data[name], annotation):
            raise RecordValidationError(
                f"{cls.__name__}.{name}: expected {_type_name(annotation)}, "
                f"got {type(data[name]).__name__}")
    return cls(**data)


def _to_mapping(self: object) -> dict[str, object]:
    return {f.name: getattr(self, f.name) for f in fields(self)}


@overload
def record(cls: T, *, frozen: bool = False) -> T: ...


@overload
def record(cls: None = None, *, frozen: bool = False) -> Callable[[T], T]: ...


@dataclass_transform(kw_only_default=True, field_specifiers=(field,))
def record(cls: T | None = None, *, frozen: bool = False):
    """Slotted dataclass plus validated from_mapping and shallow to_mapping.

    Direct construction and assignment deliberately do not validate types.
    """
    def decorate(target: T) -> T:
        annotations = getattr(target, "__annotations__", {})
        collisions = _RESERVED & (
            set(annotations) | set(vars(target)))
        if collisions:
            raise TypeError(
                f"Reserved record field/method name: {sorted(collisions)!r}")
        setattr(target, "from_mapping", classmethod(_from_mapping))
        setattr(target, "to_mapping", _to_mapping)
        return dataclass(slots=True, kw_only=True, frozen=frozen)(target)

    return decorate(cls) if cls is not None else decorate
