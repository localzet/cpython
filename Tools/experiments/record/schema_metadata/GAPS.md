# Interoperability loss matrix

Descriptive metadata does not imply automatic conversion or compatibility.

| Feature | TypedDict | dataclass | attrs | Pydantic | msgspec |
|---|---|---|---|---|---|
| Field discovery | annotations | fields() | attrs.fields() | model_fields | structs.fields() |
| Input requiredness | required keys | missing default | missing default | is_required() | NODEFAULT |
| Default values | absent key | value/factory | value/factory | value/factory | value/factory |
| ReadOnly | static per key | n/a | n/a | n/a | n/a |
| Frozen | n/a | instance flag | varies | model/field | instance flag |
| Input names | mapping keys | constructor args | constructor aliases | validation aliases | wire encode_name |
| Output names | mapping keys | attributes | attributes | dump(by_alias=True) | wire encode_name |
| Runtime validation | no | no | configurable | configurable | typed decode |
| Unknown keys | static open/closed | constructor fails | constructor fails | config | decoder config |

Examples of loss:
- Missing TypedDict optional key vs materialized dataclass default.
- TypedDict ReadOnly is static; frozen dataclass protects assignment at
  runtime but neither implies deep immutability.
- attrs.field(alias="foo") changes constructor arguments, not JSON names.
- Pydantic validation_alias vs serialization_alias may be distinct.
- msgspec rename="camel" changes wire keys but not Python attribute names.
- Runtime coercion, validators, serialization hooks, Pydantic AliasChoices,
  tagged/array-like msgspec structs cannot be captured by this snapshot.

Safety:
- Unknown does not mean False.
- Unsupported richer features raise UnsupportedSchema where detected.
- compare_metadata distinguishes differences from uncertainty.
- "metadata_match" is limited to selected fields, not type assignability,
  runtime equivalence, validation equivalence or compatible JSON payloads.
- get_type_hints may execute code; only inspect trusted definitions.
- Snapshot carries live Python type objects and is NOT portable JSON.
- Nested schemas, typed extra items and type variables are not normalized.

No upstream change is justified until consumer use cases and loss boundaries
can be demonstrated independently.
