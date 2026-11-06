# TypedDict ↔ dataclass boundary experiment

Research prototype only: no parser, builtin or standard-library change.

TypedDict is a static description of a dictionary, whereas dataclass
creates a runtime object. These are deliberately **not** the same type.

    from dataclasses import dataclass
    from typing import NotRequired, TypedDict
    from bridge.schema_bridge import SchemaBridge

    class Wire(TypedDict):
        id: int
        label: NotRequired[str]

    @dataclass(slots=True)
    class User:
        id: int
        label: str = ""

    bridge = SchemaBridge(User, Wire)
    user = bridge.from_mapping({"id": 42})
    assert bridge.to_mapping(user) == {"id": 42, "label": ""}

The missing optional key is intentionally materialized as a dataclass default.
Therefore, this adapter is canonicalizing, **not lossless**. No implicit
attribute/key equivalence, coercion or magic object-to-mapping protocol.

## Reproduce

Run from Tools/experiments/record with Python 3.13+:

    python -m unittest discover -s bridge -p 'test_*.py' -v
    python bridge/check_typing.py
    python -m bridge.benchmark_bridge --sizes 3 10 30 \
      --output bridge-results.json

The behavior tests need only the stdlib. The checker and benchmark
dependencies are pinned in ../requirements-research.txt (relative to this
directory: requirements-research.txt). CI runs behavior on 3.13/3.14,
checks mypy/Pyright and uploads raw benchmark JSON.

## Supported semantics

- Require matching dataclass and TypedDict field names.
- Require dataclass defaults for optional TypedDict keys.
- Reject unknown keys by default; opt in to extra="ignore".
- Strict checking of bool, int, float, str, bytes, nullable T, Literal,
  list[T], dict[str,T], nested dataclass/TypedDict pairs, and Any.
- Missing required keys and invalid values have path-aware errors.
- All fields are emitted during encoding, including defaulted optionals.
- Dict/list structures are newly allocated during conversion.
- ReadOnly on TypedDict does not make runtime objects immutable.
- Unhandled schema shapes, recursive records, init=False fields and
  incompatible field types fail at adapter construction.

The return type of to_mapping() is deliberately dict[str, object]. Statically
pretending it is an arbitrary TypedDict would be unsound without a separate
typing specification.

Read CONTRACT.md, METHODOLOGY.md, and RESULTS.md before interpreting
this API or its benchmark observations.
