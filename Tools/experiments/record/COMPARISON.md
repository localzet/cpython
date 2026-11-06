# Structured data types: capability and semantics comparison

Research snapshot: November 2026. This is a comparison of *different runtime
contracts*, not a proposal to treat all classes as dictionaries.

## Core distinctions

- A **mapping** is accessed by key and defines a dictionary-like protocol.
- An **object** is accessed by attribute, may have behavior, and may use slots.
- A **static schema** informs mypy/Pyright, but does not necessarily validate
  runtime values.
- **Boundary validation** is a runtime operation: given untrusted input, either
  produce a conforming value or reject it. Some libraries also coerce values.

| Implementation | Runtime representation | Fixed declared fields | Runtime validation | Main trade-off |
|---|---|---|---|---|
| plain class | Python instance | only manually | manual | flexible, boilerplate |
| TypedDict | dict | type-checker rules | none | mapping API, zero new runtime object kind |
| dataclass | Python instance | only with slots=True | none built in | convenient data object |
| dataclass(slots=True) | slotted instance | yes, for direct instances | none built in | compact standard baseline |
| NamedTuple | tuple subclass | yes | not automatic | positional tuple semantics can be surprising |
| attrs.define | typically slotted instance | yes, configurable | opt-in validators/converters | more configuration, external dependency |
| Pydantic BaseModel | validated model instance | configurable extra policy | yes, configurable strict mode | rich validation and schema ecosystem, higher setup cost |
| msgspec.Struct | specialized record instance | configurable | on typed conversion/decode | fast structured decode, external C extension |
| experimental Record | slotted dataclass subclass | yes, for direct instances | explicit from_mapping | only a restricted type subset, pure-Python conversion |

No guarantee extends to arbitrary subclasses: subclassing a slotted class
without slots may introduce a __dict__. Frozen instances do not imply deep
immutability. TypedDict remains a dict at runtime.

## What already works today?

**Internal domain objects:** dataclass(slots=True) usually provides the main
benefit: named fields, defaults, equality, repr, and compact storage. NamedTuple
can be convenient when positional tuple behavior is intentional.

**API boundary DTOs:** Pydantic can validate a mapping or JSON with explicit
strictness and forbid extra fields. msgspec supports typed conversion and JSON
decoding (including strict mode and unknown-field rejection). attrs supports
validators and converter hooks.

**Static JSON-shaped data:** TypedDict is a structural type description for
plain mappings. It intentionally is not a new runtime container.

**Mixed object/mapping access:** using both obj.field and obj["field"] under
the same name causes ambiguity (e.g. record field named "items"). This prototype
uses explicit from_mapping()/to_mapping() to avoid the collision.

## Current prototype's actual contract

- Keyword-only, nominal, slotted dataclass objects inheriting Record.
- Normal construction is *not* validated, even though annotations exist.
- from_mapping validates required and extra keys, then checks a small
  annotation subset without coercion (int rejects bool).
- Supported: Any, object, classes, None, Union, Literal, list[T], dict[K,V],
  and finite / variadic tuple types.
- Unsupported: full typing syntax, recursive record decoding, TypedDict
  parsing, containers such as set[T], custom field adapters.
- No deep copy by to_mapping; no JSON API; no C speed benefit.
- Base class declares mapping helpers so static analyzers see methods and
  Self return types; dataclass_transform models the generated constructor.

For instance, from_mapping() is deliberately more strict about bool vs int
than isinstance(value, int) but is *not* equivalent to every strict mode of
Pydantic/msgspec. Benchmark coverage is limited to simple int fields.

## Candidate gaps (not yet demonstrated)

1. A stdlib-friendly, explicit mapping-validation protocol for slotted
   dataclasses without requiring a large schema library.
2. Better typing for generated constructors/mapping adapters.
3. Consistent diagnostics, e.g. locating a nested invalid field.
4. Common schema metadata across dataclasses, TypedDict and external codecs.

None yet justifies a new keyword or builtin. The first gap is a small library
API; the second may belong in the typing specification, and the others can
be piloted outside the interpreter.

## Decision framework

Before discussing a new builtin with CPython maintainers, require:

1. At least three real-world cases that cannot reasonably use existing
   structures or small library helpers.
2. Explicit semantics covering errors, mutability, equality, inheritance,
   serialization, name collisions and static typing.
3. Cross-version checker tests and runtime regression tests.
4. Benchmarks for equivalent workloads, with raw data and limitations.
5. A maintenance and compatibility argument, including free-threaded Python.

**Current recommendation:** keep this experimental; improve the stdlib
interoperability story first. Do not start a C implementation solely to
outperform a pure-Python wrapper that delegates to dataclasses.

## References

- Python dataclasses: https://docs.python.org/3/library/dataclasses.html
- TypedDict: https://docs.python.org/3/library/typing.html#typing.TypedDict
- Dataclass transform specification: https://typing.python.org/en/latest/spec/dataclasses.html
- attrs documentation: https://www.attrs.org/en/stable/
- Pydantic strict validation: https://docs.pydantic.dev/latest/concepts/strict_mode/
- msgspec Struct API: https://msgspec.dev/api
- msgspec benchmarking caveats: https://msgspec.dev/benchmarks
- Brett Cannon's record experiment: https://github.com/brettcannon/record-type
- PEP 764 (inline TypedDict): https://peps.python.org/pep-0764/
