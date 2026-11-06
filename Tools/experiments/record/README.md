# CPython structured-record research

This is an isolated **research prototype**. It changes neither CPython's
parser nor a built-in type. It is **not** an upstream feature proposal.

## Quick start

Use Python 3.13+ (CI also runs on 3.14):

    cd Tools/experiments/record
    python -m pip install -r requirements-research.txt
    python -m unittest discover -s . -p 'test_*.py' -v
    python check_typing.py
    python benchmark_matrix.py --sizes 3 10 30 --number 2000 \
      --repeat 5 --instances 1500 --output results.json

Behavioral tests use only stdlib modules. External dependencies are needed
for the comparison and static-checker tests. Pinned direct dependencies are
listed in requirements-research.txt; save the full environment for a stricter
reproduction.

## Example

    from record import Record, record

    @record
    class User(Record):
        id: int
        name: str
        tags: list[str]

    user = User(id=1, name="Ada", tags=["dev"])
    validated = User.from_mapping({
        "id": 1, "name": "Ada", "tags": ["dev"]
    })
    assert validated.to_mapping()["id"] == 1

Plain construction deliberately does **not** enforce types. Only
from_mapping() validates. Instances use dataclass(slots=True, kw_only=True).
Frozen records use @record(frozen=True). Inherit Record to expose mapping
methods to both runtime and static analyzers.

The supported annotation subset is small and intentionally non-coercing.
Nested error paths are diagnostic; they are not evidence of complete
JSON Schema, attrs, Pydantic or msgspec compatibility.

## Files

- record.py — slotted baseline with explicit mapping validation
- test_record.py — behavior, inheritance, frozen, unknown field and errors
- check_typing.py + typecheck_cases/ — positive and expected-negative
  mypy and Pyright checks, including constructor and frozen semantics
- benchmark_matrix.py — 3/10/30-field structured comparison, JSON output
- bench.py — historical introductory 3-field microbenchmark
- COMPARISON.md — capability matrix, semantic gaps and decision criteria
- METHODOLOGY.md — methodology, comparability limits and reproduction
- BENCHMARKS.md — initial baseline, historical only
- DESIGN.md — original design assumptions; COMPARISON.md supersedes it
- example.py — runnable example

## Current conclusion

The object layout is a slotted dataclass. There is no demonstrated advantage
for a new CPython builtin or a new keyword. A standardized boundary-validation
API, stronger static typing and useful error locations are plausible smaller
investigations. A C rewrite is explicitly **out of scope** until a measurable
and compelling gap has been established.

## Links

- https://docs.python.org/3/library/dataclasses.html
- https://typing.python.org/en/latest/spec/dataclasses.html
- https://msgspec.dev/structs
- https://www.attrs.org/en/stable/
- https://docs.pydantic.dev/latest/
