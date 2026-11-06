"""Research-only schema metadata interchange for Python data models.

The result is descriptive metadata, NOT a validator, a typing rule, or JSON
Schema. Only introspect trusted classes: get_type_hints evaluates annotations.
"""
from __future__ import annotations

from dataclasses import MISSING, dataclass, fields, is_dataclass
from typing import (
    Annotated, Any, Literal, Protocol, ReadOnly, Required, NotRequired,
    get_args, get_origin, get_type_hints, is_typeddict,
)

DefaultKind = Literal["missing", "value", "factory"]
Openness = Literal["open", "forbid", "ignore", "allow", "unknown"]


class UnsupportedSchema(TypeError):
    """An important schema feature cannot be represented without data loss."""


@dataclass(frozen=True, slots=True)
class FieldMeta:
    name: str
    annotation: object
    input_names: tuple[str, ...]
    output_name: str
    input_required: bool
    default_kind: DefaultKind
    static_readonly: bool | None = None
    assignment_frozen: bool | None = None
    init: bool = True


@dataclass(frozen=True, slots=True)
class SchemaMeta:
    provider: str
    model: type
    representation: Literal["mapping", "object"]
    fields: tuple[FieldMeta, ...]
    extra_policy: Openness
    frozen: bool | None
    validation: Literal["none", "constructor", "decode", "configurable", "unknown"]
    notes: tuple[str, ...] = ()

    def by_name(self) -> dict[str, FieldMeta]:
        return {field.name: field for field in self.fields}


class MetadataProvider(Protocol):
    """Possible opt-in interface; deliberately NOT a registered standard."""

    def schema_metadata(self) -> SchemaMeta: ...


def _require_unique(schema: SchemaMeta) -> SchemaMeta:
    names: set[str] = set()
    for field in schema.fields:
        if not field.input_names:
            raise UnsupportedSchema(f"{field.name}: input name is missing")
        if field.name in names:
            raise UnsupportedSchema(f"Duplicate field {field.name!r}")
        names.add(field.name)
    return schema


def _typing_field(annotation: object) -> tuple[object, bool | None, bool]:
    """Remove qualifiers while retaining TypedDict ReadOnly and requiredness."""
    required: bool | None = None
    readonly = False
    while True:
        origin = get_origin(annotation)
        if origin is Annotated:
            annotation = get_args(annotation)[0]
        elif origin is Required:
            if required is False:
                raise UnsupportedSchema("Contradictory Required/NotRequired")
            required = True
            annotation = get_args(annotation)[0]
        elif origin is NotRequired:
            if required is True:
                raise UnsupportedSchema("Contradictory Required/NotRequired")
            required = False
            annotation = get_args(annotation)[0]
        elif origin is ReadOnly:
            readonly = True
            annotation = get_args(annotation)[0]
        else:
            return annotation, required, readonly


def _typeddict(cls: type) -> SchemaMeta:
    raw = cls.__annotations__
    # Deferred annotations can invalidate __required_keys__ metadata.
    if any(isinstance(t, str) or type(t).__name__ == "ForwardRef"
           for t in raw.values()):
        raise UnsupportedSchema(
            "Deferred TypedDict annotations can invalidate requiredness")
    hints = get_type_hints(cls, include_extras=True)
    required_keys = set(cls.__required_keys__)
    optional_keys = set(cls.__optional_keys__)
    if required_keys & optional_keys or required_keys | optional_keys != set(hints):
        raise UnsupportedSchema("TypedDict requiredness metadata is inconsistent")

    data = []
    for name, hint in hints.items():
        annotation, qualified_required, readonly = _typing_field(hint)
        required = name in required_keys
        if qualified_required is not None and qualified_required != required:
            raise UnsupportedSchema(f"Incorrect requiredness for {name!r}")
        data.append(FieldMeta(
            name, annotation, (name,), name, required, "missing",
            static_readonly=readonly))

    if getattr(cls, "__closed__", False):
        extras: Openness = "forbid"
    elif hasattr(cls, "__extra_items__"):
        # A schema can allow typed extra items, not expressible as only
        # allow/ignore/forbid without retaining their type.
        raise UnsupportedSchema("TypedDict typed extra items are unsupported")
    else:
        extras = "open"
    return SchemaMeta(
        "typeddict", cls, "mapping", tuple(data), extras, None, "none",
        ("ReadOnly is a static constraint, not runtime freezing.",
         "Optional keys are not constructor defaults.",
         "The open TypedDict typing rule is not runtime validation."))


def _dataclass(cls: type) -> SchemaMeta:
    hints = get_type_hints(cls, include_extras=True)
    field_list = []
    frozen = bool(cls.__dataclass_params__.frozen)
    for f in fields(cls):
        if f.name not in hints:
            raise UnsupportedSchema(f"Missing dataclass type for {f.name!r}")
        if not f.init:
            raise UnsupportedSchema(f"{f.name}: init=False cannot be mapped")
        kind: DefaultKind = (
            "factory" if f.default_factory is not MISSING
            else "value" if f.default is not MISSING else "missing")
        field_list.append(FieldMeta(
            f.name, hints[f.name], (f.name,), f.name, kind == "missing",
            kind, assignment_frozen=frozen))
    return SchemaMeta(
        "dataclass", cls, "object", tuple(field_list), "forbid",
        frozen, "none",
        ("Constructor-required fields are not a wire format contract.",
         "Frozen is shallow and does not imply ReadOnly TypedDict."))


def _attrs(cls: type) -> SchemaMeta:
    import attrs

    hints = get_type_hints(cls, include_extras=True)
    field_list = []
    for a in attrs.fields(cls):
        if not a.init:
            raise UnsupportedSchema(f"{a.name}: init=False unsupported")
        kind: DefaultKind = (
            "missing" if a.default is attrs.NOTHING
            else "factory" if isinstance(a.default, attrs.Factory) else "value")
        # attrs aliases name constructor parameters, not serialization keys.
        name = a.alias if a.alias is not None else a.name
        field_list.append(FieldMeta(
            a.name, hints.get(a.name, a.type or Any), (name,), a.name,
            kind == "missing", kind, assignment_frozen=None))
    return SchemaMeta(
        "attrs", cls, "object", tuple(field_list), "forbid",
        None, "configurable",
        ("attrs field aliases refer to __init__ arguments, not wire keys.",
         "Validators and converters are not represented.",
         "Class/field immutability is not inferred from implementation details."))


def _pydantic(cls: type) -> SchemaMeta:
    from pydantic import AliasChoices, AliasPath

    config = cls.model_config
    names_allowed = bool(
        config.get("validate_by_name", config.get("populate_by_name", False)))
    field_list = []
    for name, f in cls.model_fields.items():
        if isinstance(f.validation_alias, (AliasChoices, AliasPath)):
            raise UnsupportedSchema(
                f"{name}: compound validation aliases are unsupported")
        primary = f.validation_alias or f.alias or name
        if not isinstance(primary, str):
            raise UnsupportedSchema(f"{name}: unsupported validation alias")
        accepted = (primary, name) if names_allowed and primary != name else (primary,)
        output = f.serialization_alias or f.alias or name
        if not isinstance(output, str):
            raise UnsupportedSchema(f"{name}: unsupported serialization alias")
        kind: DefaultKind = (
            "missing" if f.is_required()
            else "factory" if f.default_factory is not None else "value")
        field_list.append(FieldMeta(
            name, f.annotation, accepted, output, f.is_required(), kind,
            assignment_frozen=bool(f.frozen) if f.frozen is not None else None))
    extra = config.get("extra") or "ignore"
    if extra not in ("allow", "ignore", "forbid"):
        raise UnsupportedSchema(f"Unknown Pydantic extra policy: {extra!r}")
    return SchemaMeta(
        "pydantic", cls, "object", tuple(field_list), extra,
        config.get("frozen", False), "configurable",
        ("Output keys describe model_dump(by_alias=True), not the default dump.",
         "Validation/serialization hooks, coercion and strictness are not captured.",
         "Field requiredness can differ from nullable annotations."))


def _msgspec(cls: type) -> SchemaMeta:
    import msgspec

    cfg = cls.__struct_config__
    if cfg.array_like or cfg.tag is not None:
        raise UnsupportedSchema(
            "Array-like or tagged msgspec.Struct wire formats unsupported")
    field_list = []
    for f in msgspec.structs.fields(cls):
        kind: DefaultKind = (
            "factory" if f.default_factory is not msgspec.NODEFAULT
            else "value" if f.default is not msgspec.NODEFAULT else "missing")
        field_list.append(FieldMeta(
            f.name, f.type, (f.encode_name,), f.encode_name,
            kind == "missing", kind,
            assignment_frozen=bool(cfg.frozen)))
    return SchemaMeta(
        "msgspec", cls, "object", tuple(field_list),
        "forbid" if cfg.forbid_unknown_fields else "ignore",
        bool(cfg.frozen), "decode",
        ("Wire names are taken from public msgspec.structs.fields().",
         "omit_defaults and custom encoding are not represented.",
         "Struct construction and strict typed decoding have different guarantees."))


def inspect_schema(source: type | MetadataProvider) -> SchemaMeta:
    """Read a trusted class using documented inspection APIs.

    A SchemaMeta is an in-process object, not a JSON-serializable schema.
    No arbitrary annotation evaluation safety is provided.
    """
    if not isinstance(source, type):
        result = source.schema_metadata()
        if not isinstance(result, SchemaMeta):
            raise TypeError("schema_metadata() must return SchemaMeta")
        return _require_unique(result)

    if is_typeddict(source):
        return _require_unique(_typeddict(source))

    try:
        from pydantic import BaseModel
    except ImportError:
        pass
    else:
        if issubclass(source, BaseModel):
            return _require_unique(_pydantic(source))

    try:
        import attrs
    except ImportError:
        pass
    else:
        if attrs.has(source):
            return _require_unique(_attrs(source))

    try:
        import msgspec
    except ImportError:
        pass
    else:
        if issubclass(source, msgspec.Struct):
            return _require_unique(_msgspec(source))

    if is_dataclass(source):
        return _require_unique(_dataclass(source))
    raise UnsupportedSchema(f"Unknown schema provider for {source!r}")
