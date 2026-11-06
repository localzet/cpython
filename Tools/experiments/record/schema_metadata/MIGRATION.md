# Migration checker contract (research v0)

This document specifies the **limited declared-contract analysis** in
migration.py. It is not a full schema compatibility standard.

## Directions and quantifiers

- input: Could a payload valid for Old fail or behave differently when
  submitted to the New input contract?
- output: Could a payload emitted by New violate assumptions made by old
  consumers of the previously described output contract?

These directions cannot be swapped. The code never treats a Python class
as an automatically serializable dict or assumes a static TypedDict is a
runtime validator.

## Decisions

| Transition | Input | Output | Reason |
|---|---|---|---|
| New required field | Breaking | Review | Old clients may omit new field |
| New optional field | Info | Review | Output emission is configurable |
| Removed field | Breaking if New forbids extras; else review | Review | Data may be ignored or old reader may expect it |
| Optional -> required | Breaking | Not inferred | Old valid payload could omit it |
| Required -> optional | Info | Not inferred | More permissive input |
| Accepted input alias removed | Breaking | Not relevant | Clients could use old name |
| Input alias added | Info | Not relevant | New input names are accepted |
| Selected output alias renamed | Not relevant | Breaking | Old reader could reference previous output name |
| Literal set narrowed | Breaking | Info | Old input values no longer accepted |
| Literal set expanded | Info | Breaking | New output could surprise old reader |
| Arbitrary annotation change | Review | Review | Subtyping/coercion/validation not known |
| Default/factory change | Review | Review | Concrete default not captured |
| Provider/representation change | Review | Review | Runtime model changes |
| Unknown field policy change | Review | Not inferred | Provider behavior differs |
| No detected change | No known breakage | No known breakage | NOT a guarantee |

The Literal rule uses exact Python type+value equality. It is a declared
value-set rule, not an assertion about Pydantic coercion or custom validators.

For the same field name, the first-stage comparison is by Python-side name,
not a universal field identity. If a field is renamed but its external alias
remains, this MVP may report a removal+addition. Consumers must review such
results and cannot rely on semantic rename detection.

## False certainty is forbidden

Even two classes with identical public field metadata might have changed
validators, conversion hooks, mutable default behavior, serialization,
model_post_init or other code not available to the analyzer. Comparing two
distinct Python classes therefore includes a general
runtime_behavior_unverified finding. The verdict normally requires review
even if all observed fields match.

No indication of "compatible" appears in the machine format. Code gates can
choose which risks cause a failure, but a zero exit code means only that the
selected policy did not match detected findings.

## CI use

Pin the provider library versions; run the tool with the same operation
settings for Old and New; store the JSON artifact; manually examine review
findings. The default gate is --fail-on breaking.

If an automated flow needs reliable guarantees, it must run representative
old payloads against New's actual decoder/validator and test New outputs
against real old readers, including negative cases.

## Next validation

- Use old and new DTO definitions from a real independent project.
- Compare observed breaking changes with consumer unit tests.
- Support alias-preserving Python field renames and explicit output-emission
  policies only with reliable metadata.
- Handle nested recursively documented schemas without executing untrusted
  code or conflating runtime validation and static typing.
- Ask maintainers of at least two independent libraries for input on which
  narrow metadata facts can be documented as stable runtime interfaces.

Only after such experiments should an upstream typing discussion be opened.
