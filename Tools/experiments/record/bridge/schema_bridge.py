"""Explicit TypedDict-to-dataclass bridge (research prototype)."""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import MISSING, Field, dataclass, fields, is_dataclass
from types import UnionType
from typing import (
    Any, Generic, Literal, NoReturn, NotRequired, ReadOnly, Required,
    TypeVar, Union, cast, get_args, get_origin, get_type_hints, is_typeddict,
)

ModelT = TypeVar("ModelT")
ExtraPolicy = Literal["forbid", "ignore"]
_NONE_TYPE = type(None)
_EXACT_SCALARS = (str, bool, int, float, bytes)


class SchemaError(TypeError):
    """The dataclass and TypedDict describe incompatible data models."""


class ValidationError(TypeError):
    """Input does not satisfy the declared dataclass/TypedDict pair."""


@dataclass(frozen=True, slots=True)
class _Codec:
    decode: Callable[[object, str], object]
    encode: Callable[[object, str], object]


@dataclass(frozen=True, slots=True)
class _FieldPlan:
    name: str
    required: bool
    codec: _Codec


@dataclass(frozen=True, slots=True)
class _RecordPlan:
    model: type
    fields: tuple[_FieldPlan, ...]
    field_names: frozenset[str]
    required: frozenset[str]


def _err(path: str, expected: object, value: object) -> NoReturn:
    raise ValidationError(
        f"{path}: expected {expected!r}, got {type(value).__name__}")


def _unwrap(annotation: object) -> object:
    while get_origin(annotation) in (Required, NotRequired, ReadOnly):
        annotation = get_args(annotation)[0]
    return annotation


def _optional(annotation: object) -> object | None:
    origin = get_origin(annotation)
    if origin not in (Union, UnionType):
        return None
    args = get_args(annotation)
    inner = [arg for arg in args if arg is not _NONE_TYPE]
    if len(args) == 2 and len(inner) == 1:
        return inner[0]
    raise SchemaError(
        f"Unsupported union {annotation!r}; only T | None is supported")


def _codec(model_ann: object, wire_ann: object,
           parents: frozenset[tuple[type, type]],
           extra: ExtraPolicy) -> _Codec:
    model_ann = _unwrap(model_ann)
    wire_ann = _unwrap(wire_ann)

    model_optional = _optional(model_ann)
    wire_optional = _optional(wire_ann)
    if model_optional is not None or wire_optional is not None:
        if model_optional is None or wire_optional is None:
            raise SchemaError(
                f"Optionality differs: {model_ann!r} vs {wire_ann!r}")
        inner = _codec(model_optional, wire_optional, parents, extra)

        def decode_optional(value: object, path: str) -> object:
            return None if value is None else inner.decode(value, path)

        def encode_optional(value: object, path: str) -> object:
            return None if value is None else inner.encode(value, path)

        return _Codec(decode_optional, encode_optional)

    if isinstance(model_ann, type) and is_dataclass(model_ann):
        if not is_typeddict(wire_ann):
            raise SchemaError(
                f"Nested dataclass {model_ann!r} needs a TypedDict schema")
        plan = _build(model_ann, wire_ann, parents, extra)
        return _Codec(
            lambda value, path: _decode(plan, value, path, extra),
            lambda value, path: _encode(plan, value, path, extra))

    left_origin = get_origin(model_ann)
    right_origin = get_origin(wire_ann)
    if left_origin is list or right_origin is list:
        if left_origin is not list or right_origin is not list:
            raise SchemaError(
                f"Container mismatch: {model_ann!r} vs {wire_ann!r}")
        la, ra = get_args(model_ann), get_args(wire_ann)
        if len(la) != 1 or len(ra) != 1:
            raise SchemaError("Parameterized list[T] required")
        item = _codec(la[0], ra[0], parents, extra)

        def convert_list(value: object, path: str,
                         forward: bool) -> object:
            if type(value) is not list:
                _err(path, "list", value)
            method = item.decode if forward else item.encode
            return [method(obj, f"{path}[{i}]")
                    for i, obj in enumerate(cast(list[object], value))]

        return _Codec(
            lambda v, p: convert_list(v, p, True),
            lambda v, p: convert_list(v, p, False))

    if left_origin is dict or right_origin is dict:
        if left_origin is not dict or right_origin is not dict:
            raise SchemaError(
                f"Container mismatch: {model_ann!r} vs {wire_ann!r}")
        la, ra = get_args(model_ann), get_args(wire_ann)
        if (len(la) != 2 or len(ra) != 2
                or la[0] is not str or ra[0] is not str):
            raise SchemaError("Only dict[str, T] is supported")
        item = _codec(la[1], ra[1], parents, extra)

        def convert_dict(value: object, path: str,
                         forward: bool) -> object:
            if type(value) is not dict:
                _err(path, "dict", value)
            method = item.decode if forward else item.encode
            result: dict[str, object] = {}
            for key, val in cast(dict[object, object], value).items():
                if type(key) is not str:
                    _err(f"{path}.<key>", "str", key)
                k = cast(str, key)
                result[k] = method(val, f"{path}[{k!r}]")
            return result

        return _Codec(
            lambda v, p: convert_dict(v, p, True),
            lambda v, p: convert_dict(v, p, False))

    if left_origin is Literal or right_origin is Literal:
        if model_ann != wire_ann:
            raise SchemaError(
                f"Literal mismatch: {model_ann!r} vs {wire_ann!r}")
        options = get_args(model_ann)

        def check_literal(value: object, path: str) -> object:
            if any(type(value) is type(x) and value == x for x in options):
                return value
            _err(path, model_ann, value)

        return _Codec(check_literal, check_literal)

    if model_ann is Any and wire_ann is Any:
        return _Codec(lambda v, p: v, lambda v, p: v)

    if (isinstance(model_ann, type) and model_ann is wire_ann
            and not is_typeddict(model_ann)):
        def check_scalar(value: object, path: str) -> object:
            if ((type(value) is model_ann) if model_ann in _EXACT_SCALARS
                    else isinstance(value, model_ann)):
                return value
            _err(path, model_ann.__name__, value)

        return _Codec(check_scalar, check_scalar)

    raise SchemaError(
        f"Unsupported or mismatched annotation: {model_ann!r} vs {wire_ann!r}")


def _build(model: type, shape: object,
           parents: frozenset[tuple[type, type]],
           extra: ExtraPolicy) -> _RecordPlan:
    if not isinstance(model, type) or not is_dataclass(model):
        raise SchemaError("Model must be a dataclass type")
    if not is_typeddict(shape):
        raise SchemaError("Payload schema must be a TypedDict definition")

    shape_type = cast(type, shape)
    pair = (model, shape_type)
    if pair in parents:
        raise SchemaError("Recursive model/schema pairs are not supported")
    parents = parents | {pair}
    model_fields: tuple[Field[Any], ...] = fields(model)
    if any(not f.init for f in model_fields):
        raise SchemaError("init=False dataclass fields require a separate policy")
    m_fields = {f.name: f for f in model_fields}
    m_hints = get_type_hints(model, include_extras=True)
    s_hints = get_type_hints(shape_type, include_extras=True)
    if set(m_fields) != set(s_hints):
        raise SchemaError(
            f"Field names differ: model={sorted(m_fields)}, "
            f"payload={sorted(s_hints)}")
    required = frozenset(shape_type.__required_keys__)
    optional = frozenset(shape_type.__optional_keys__)
    if (required & optional or required | optional != s_hints.keys()):
        raise SchemaError("TypedDict required/optional metadata is inconsistent")
    # Deferred annotations can make PEP 655 key metadata unreliable.
    for name, ann in s_hints.items():
        if get_origin(ann) is Required and name not in required:
            raise SchemaError(f"Unreliable TypedDict requiredness for {name!r}")
        if get_origin(ann) is NotRequired and name not in optional:
            raise SchemaError(f"Unreliable TypedDict optionality for {name!r}")

    descriptors = []
    for name, f in m_fields.items():
        has_default = f.default is not MISSING or f.default_factory is not MISSING
        if name in optional and not has_default:
            raise SchemaError(
                f"Optional payload key {name!r} has no dataclass default")
        descriptors.append(_FieldPlan(
            name, name in required,
            _codec(m_hints[name], s_hints[name], parents, extra)))
    return _RecordPlan(
        model, tuple(descriptors), frozenset(m_fields), required)


def _decode(plan: _RecordPlan, input_value: object, path: str,
            extra: ExtraPolicy) -> object:
    if not isinstance(input_value, Mapping):
        _err(path, "mapping", input_value)
    mapping = cast(Mapping[object, object], input_value)
    if not all(type(k) is str for k in mapping):
        raise ValidationError(f"{path}: mapping keys must be strings")
    given = set(mapping)
    missing = plan.required - given
    if missing:
        raise ValidationError(f"{path}: missing keys {sorted(missing)!r}")
    extras = given - plan.field_names
    if extra == "forbid" and extras:
        raise ValidationError(f"{path}: unexpected keys {sorted(extras)!r}")
    kwargs = {}
    for field_plan in plan.fields:
        if field_plan.name in mapping:
            name = field_plan.name
            kwargs[name] = field_plan.codec.decode(
                mapping[name], f"{path}.{name}")
    return plan.model(**kwargs)


def _encode(plan: _RecordPlan, value: object, path: str,
            extra: ExtraPolicy) -> dict[str, object]:
    if not isinstance(value, plan.model):
        _err(path, plan.model.__name__, value)
    return {
        field_plan.name: field_plan.codec.encode(
            getattr(value, field_plan.name), f"{path}.{field_plan.name}")
        for field_plan in plan.fields
    }


class SchemaBridge(Generic[ModelT]):
    """Strict mapping/model bridge with no implicit type coercion.

    TypedDict is metadata for validating untrusted mappings, not a runtime
    container distinct from dict. to_mapping returns dict[str, object].
    """

    def __init__(self, model: type[ModelT], payload_schema: object,
                 *, extra: ExtraPolicy = "forbid") -> None:
        if extra not in ("forbid", "ignore"):
            raise ValueError(f"Unknown extra-field policy: {extra!r}")
        self._plan = _build(model, payload_schema, frozenset(), extra)
        self._extra = extra

    def from_mapping(self, data: Mapping[str, object]) -> ModelT:
        return cast(ModelT, _decode(
            self._plan, data, self._plan.model.__name__, self._extra))

    def to_mapping(self, model: ModelT) -> dict[str, object]:
        return _encode(self._plan, model, self._plan.model.__name__,
                       self._extra)

    def from_json(self, raw: str | bytes | bytearray) -> ModelT:
        return self.from_mapping(json.loads(raw))

    def to_json(self, model: ModelT) -> str:
        return json.dumps(self.to_mapping(model), separators=(",", ":"))
