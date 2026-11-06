# Structured data in Python: exploratory design note

Status: research. Not an upstream CPython feature proposal.

## Alternative matrix

| Tool | Representation | Closed shape | Validation |
|---|---|---|---|
| TypedDict | ordinary dict | static only | static only |
| plain class | object | no | no |
| dataclass(slots=True) | slotted object | yes* | no |
| NamedTuple | tuple | fixed | no |
| msgspec.Struct | specialized object | configurable | typed decoding |
| this prototype | slotted dataclass | yes* | explicit mapping conversion |

* Arbitrary subclasses can add instance dictionaries; no deep immutability.

Other existing choices: attrs and Pydantic. They already cover many
converter/validator workflows. Implicitly making an object also implement
Mapping would create field-name conflicts such as keys/items and ambiguous
hash/equality semantics. The prototype uses explicit conversion instead.

## Relevant previous work

- PEP 764 (Draft): Inline TypedDict, a typing feature.
- PEP 814 (Final, Python 3.15): immutable frozendict.
- PEP 841 (Draft): frozen mapping/set literals.
- Brett Cannon's record-type proof of concept lacked sufficient support.
- msgspec.Struct already provides efficient objects and typed decoding.
- dataclasses already handle slots, repr, equality and freezing.

Sources:

- https://peps.python.org/pep-0764/
- https://peps.python.org/pep-0814/
- https://peps.python.org/pep-0841/
- https://docs.python.org/3/library/dataclasses.html
- https://docs.python.org/3/library/typing.html#typing.TypedDict
- https://discuss.python.org/t/struct-in-python/62777
- https://github.com/brettcannon/record-type
- https://msgspec.dev/structs.html
- https://msgspec.dev/benchmarks.html

## Working hypothesis

A record is a nominal fixed-shape object with keyword-only construction,
optional frozen behavior, no implicit type checks for ordinary use, and a
strict and explicit mapping-validation boundary. It is *not* both a dict
and a class; these representations have different contracts.

The prototype intentionally delegates normal behavior to dataclasses. Only
the boundary validation API is new. That is not yet a justification for a
distinct builtin.

## Unresolved requirements

- Which real use cases cannot be handled by current dataclasses or libraries?
- Why would this belong in Python itself instead of a library?
- Should shape, values or both be immutable?
- Should annotation checks be explicit only at data boundaries?
- How should generics, default factories, inheritance, nested records,
  match statements, pickling and forward references behave?
- Could a C implementation be more useful than library support?
- What is required for free-threaded builds and subinterpreters?
- Does typing need improvement more urgently than runtime objects?

**Do not propose a keyword/AST/runtime change** before a functional gap,
precise semantics, representative tests and independently reproducible
performance evidence have been established.
