"""Experimental fixed-shape records with explicit boundary validation.

This is a research prototype, not a proposed standard-library API.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import MISSING, dataclass, field, fields
from functools import lru_cache
from types import UnionType
from typing import (
    Any, Literal, Self, TypeVar, Union, dataclass_transform, get_args,
    get_origin, get_type_hints, overload,
)

T = TypeVar("T", bound=type)
_RESERVED = frozenset(("from_mapping", "to_mapping"))
_EXACT_TYPES = (bool, int, float, str, bytes)


class RecordValidationError(TypeError):
    """Input did not satisfy a record's declared fields."""


def _type_name(annotation: object) -> str:
    return getattr(annotation, "__name__", str(annotation))


def _fail(path: str, expected: object, value: object) -> None:
    raise RecordValidationError(
        f"{path}: expected {_type_name(expected)}, got "
        f"{type(value).__name__}")


def _check(value: object, annotation: object, path: str) -> None:
    """Validate a deliberately narrow, non-coercing annotation subset."""
    if annotation is Any or annotation is object:
        return
    if annotation is None or annotation is type(None):
        if value is None:
            return
        _fail(path, type(None), value)
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (Union, UnionType):
        for alternative in args:
            try:
                _check(value, alternative, path)
            except RecordValidationError:
                continue
            else:
                return
        _fail(path, annotation, value)
    if origin is Literal:
        if any(type(value) is type(item) and value == item
               for item in args):
            return
        _fail(path, annotation, value)
    if origin is list:
        if not isinstance(value, list):
            _fail(path, annotation, value)
        if args:
            for index, item in enumerate(value):
                _check(item, args[0], f"{path}[{index}]")
        return
    if origin is dict:
        if not isinstance(value, dict):
            _fail(path, annotation, value)
        if args:
            for key, item in value.items():
                _check(key, args[0], f"{path}.<key>")
                _check(item, args[1], f"{path}[{key!r}]")
        return
    if origin is tuple:
        if not isinstance(value, tuple):
            _fail(path, annotation, value)
        if not args:
            return
        if len(args) == 2 and args[1] is Ellipsis:
            for index, item in enumerate(value):
                _check(item, args[0], f"{path}[{index}]")
            return
        if len(value) != len(args):
            _fail(path, annotation, value)
        for index, (item, expected) in enumerate(zip(value, args)):
            _check(item, expected, f"{path}[{index}]")
        return
    if isinstance(annotation, type):
        if (type(value) is annotation if annotation in _EXACT_TYPES
                else isinstance(value, annotation)):
            return
        _fail(path, annotation, value)
    raise TypeError(f"Unsupported annotation {_type_name(annotation)}")


@lru_cache(maxsize=256)
def _schema(cls: type) -> tuple[tuple[str, object, bool], ...]:
    hints = get_type_hints(cls)
    return tuple(
        (f.name, hints[f.name],
         f.default is MISSING and f.default_factory is MISSING)
        for f in fields(cls)
    )


class Record:
    """Explicitly inherited API so static analyzers can resolve methods."""

    __slots__ = ()

    @classmethod
    def from_mapping(cls: type[Self], data: Mapping[str, object]) -> Self:
        if not isinstance(data, Mapping):
            raise RecordValidationError(f"{cls.__name__}: expected a mapping")
        schema = _schema(cls)
        names = {name for name, _, _ in schema}
        unexpected = set(data) - names
        if unexpected:
            raise RecordValidationError(
                f"{cls.__name__}: unknown fields "
                f"{sorted(map(repr, unexpected))!r}")
        missing = [name for name, _, required in schema
                   if required and name not in data]
        if missing:
            raise RecordValidationError(
                f"{cls.__name__}: missing fields {missing!r}")
        for name, annotation, _ in schema:
            if name in data:
                _check(data[name], annotation, f"{cls.__name__}.{name}")
        # Dataclasses do not automatically perform runtime type checks.
        return cls(**data)

    def to_mapping(self) -> dict[str, object]:
        """Return a *shallow* mapping of field names to values."""
        return {f.name: getattr(self, f.name) for f in fields(self)}


@overload
def record(cls: T, /, *, frozen: bool = False) -> T: ...


@overload
def record(cls: None = None, /, *, frozen: bool = False
           ) -> Callable[[T], T]: ...


@dataclass_transform(kw_only_default=True, field_specifiers=(field,))
def record(cls: T | None = None, /, *, frozen: bool = False
           ) -> T | Callable[[T], T]:
    """A slotted dataclass with the explicit Record mapping boundary.

    Callers must inherit Record. Direct construction and subsequent assignment
    intentionally do not validate types. from_mapping() does.
    """
    def decorate(target: T) -> T:
        if not issubclass(target, Record):
            raise TypeError("Records must inherit Record")
        collisions = _RESERVED & (
            set(getattr(target, "__annotations__", {})) | set(vars(target)))
        if collisions:
            raise TypeError(
                f"Reserved record field/method name: {sorted(collisions)!r}")
        return dataclass(slots=True, kw_only=True, frozen=frozen)(target)

    return decorate(cls) if cls is not None else decorate
