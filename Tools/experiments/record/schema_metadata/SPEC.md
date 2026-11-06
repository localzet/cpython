# Field metadata protocol: exploratory design

Status: v0 **experiment**, not an accepted standard or a PEP.

## Existing solutions and the precise gap

- PEP 681 / dataclass_transform informs static type checkers about generated
  constructors. Its runtime metadata does not describe serialization.
- PEP 589, 655, 705, 728 specify TypedDict requiredness, readonly and
  openness. These are static mapping semantics, not runtime validation.
- dataclasses.fields, attrs.fields, Pydantic.model_fields and
  msgspec.structs.fields are established provider-specific inspection APIs.
- JSON Schema specifies interoperable wire validation. It does not describe
  all Python constructor, attribute and type-checker semantics.

The unexplored gap is **discovery of a deliberately limited subset of field
facts**, with explicit warning when a richer feature cannot be represented.

## Current prototype

FieldMeta captures:

| Property | Meaning |
|---|---|
| name | Python-side logical field name |
| annotation | Live Python type expression, not a JSON Schema |
| input_names | Names used by a selected provider-specific input operation |
| output_name | Primary name for a selected provider-specific output |
| input_required | Required for that provider-specific input operation |
| default_kind | missing / value / factory, never the concrete value |
| static_readonly | Static field restriction if known, otherwise unknown |
| assignment_frozen | Runtime field assignment restriction if known |
| init | Field included in input/constructor (limited MVP) |

SchemaMeta adds provider, source class, mapping/object representation,
extra policy, broad validation category and explanatory caveats.

The *same string* in different providers is NOT the same operation. An attrs
alias is an initializer argument. A msgspec encode_name is a wire name.
Pydantic has independent validation and serialization aliases. All names
are provider-scoped and cannot silently be treated as equivalent wire keys.

## Future opt-in runtime interface

    class MetadataProvider(Protocol):
        def schema_metadata(self) -> SchemaMeta: ...

A consumer obtains an immutable descriptive snapshot, checks version and
capability markers, and rejects unsupported features. It must not instantiate
models, run default factories or mutate the source types. The runtime
validation and codec remain the responsibility of the provider.

Before a real public standard, we need:
1. Versioning, capability negotiation and extension namespaces.
2. Explicit input/output operation kinds and namespacing.
3. Separate optional-key presence, constructor default, field mutability
   and object freezing semantics.
4. Recursive types, unions, generic aliases and nested type constraints.
5. Unsupported-feature reporting without silently losing information.
6. A clear trust model for evaluating forward references.
7. At least two independent tools consuming the same provider metadata.

## Upstream strategy

Do not add a parser keyword, builtin or C implementation. Do not draft a
PEP yet. Demonstrate uses in schema migration checks, API contract diff,
typed tooling or validation-boundary generation. Gather library maintainer
feedback first; if a small library adapter suffices, keep it outside CPython.

References:
- https://typing.python.org/en/latest/spec/dataclasses.html
- https://typing.python.org/en/latest/spec/typeddict.html
- https://docs.python.org/3/library/dataclasses.html
- https://www.attrs.org/en/stable/
- https://docs.pydantic.dev/latest/concepts/fields/
- https://msgspec.dev/api
