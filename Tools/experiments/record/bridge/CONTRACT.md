# Contract and findings

## Three representations, not one

1. TypedDict: a structural specification for dict objects and static type checkers.
2. dataclass: a nominal runtime object with attributes, defaults and behavior.
3. wire payload: an actual mapping or JSON value, potentially untrusted.

SchemaBridge[Model] takes a dataclass class and a TypedDict schema at
construction, checks their compatibility and compiles a narrow conversion
plan. Conversion happens only through explicit from_mapping()/to_mapping(),
from_json()/to_json() methods.

## Counterexample to lossless two-way conversion

    class Wire(TypedDict):
        id: int
        label: NotRequired[str]

    @dataclass
    class Model:
        id: int
        label: str = ""

A wire object {"id": 1} is legal but the dataclass has label="". Encoding
it produces {"id": 1, "label": ""}. Once materialized, the model carries no
evidence whether the original key was absent or explicitly present.

The prototype **canonicalizes** mappings. Preserving absence would need
extra presence metadata and another design decision. Likewise, TypedDict
ReadOnly is a type-checker contract, not runtime freezing.

## Schema contract

| Feature | Chosen prototype behavior |
|---|---|
| Field names | Exact equality |
| Required keys | Checked before construction |
| Optional keys | Dataclass default/default_factory mandatory |
| Unknown keys | Reject; explicit ignore policy available |
| Scalar types | Strict, no coercion; int rejects bool |
| Nested data | list, dict[str,T], nullable T, Literal, nested records |
| Collections on output | Fresh dict/list containers |
| ReadOnly | Static only; no runtime freeze |
| InitVar, init=False, aliases | Unsupported; reject |
| General union, tuple, recursion | Unsupported; reject |
| Postponed annotation inconsistencies | Detect and reject where possible |
| TypedDict output annotation | dict[str,object]; no false static promise |

The shape is checked via get_type_hints(..., include_extras=True),
dataclasses.fields, is_typeddict, __required_keys__ and __optional_keys__.
Python documents that deferred annotations can make TypedDict's required
metadata incorrect: the prototype detects explicit qualifier contradictions,
but cannot guarantee recovery of all ambiguous cases.

Nested field paths such as User.friends[0].city are reported at validation
time. Direct mutation of a dataclass instance is not intercepted; to_mapping
validates the supported fields again.

## Why not a dataclass that is also a dict?

Mappings use keys, iteration and methods such as items() and keys(); data
objects use attributes that may have those same names. Implicit equivalence
would introduce collisions and confusing hash/equality/mutability behavior.
An explicit adapter gives an ordinary object for business logic and an
ordinary dictionary at serialization boundaries.

## Typing findings

SchemaBridge[User].from_mapping(...) has return type User in mypy and
Pyright. SchemaBridge[User].to_mapping(...) intentionally returns
dict[str, object]. The type checkers cannot prove that arbitrary runtime
TypedDict metadata and a dataclass schema are equivalent, nor can a generic
bridge safely promise a TypedDict return type without stronger primitives.
An explicit cast can be used by applications but is an unchecked assertion.

## Engineering recommendation

The experiment tests a library-level interoperability protocol. It does
**not** demonstrate the need for a new Python keyword, builtin type or C
implementation. A narrower future discussion could explore standardized
schema metadata, strict conversion interfaces or typing support, backed by
concrete use cases that current libraries cannot cover.

Further work: optional-field presence metadata, alias/name mapping,
recursive schemas, richer unions, nested DTO benchmarks and cold-start cost.

References:
- https://typing.python.org/en/latest/spec/typeddict.html
- https://peps.python.org/pep-0655/
- https://peps.python.org/pep-0705/
- https://docs.python.org/3/library/typing.html
- https://docs.python.org/3/library/dataclasses.html
