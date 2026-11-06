# Record type experiment

**Research branch only.** This directory does not modify CPython's parser,
runtime or standard library. It evaluates whether a fixed-shape data type
could add meaningful value beyond dataclasses, TypedDict and external libraries.

## Reproduce

From the repository root (Python 3.11+; no dependencies):

    cd Tools/experiments/record
    python -m unittest discover -s . -p 'test_*.py' -v
    python bench.py --number 30000 --repeat 5 --instances 10000

## Example

    from record import record

    @record
    class User:
        id: int
        name: str
        tags: list[str]
        active: bool = True

    user = User(id=1, name="Ada", tags=["dev"])
    checked = User.from_mapping({"id": 1, "name": "Ada", "tags": ["dev"]})
    assert checked.to_mapping()["id"] == 1

The decorator uses dataclass(slots=True, kw_only=True). Instances have
fixed fields, repr, equality, defaults and optional frozen=True behavior.
Direct construction and assignment do not validate annotations. Explicit
from_mapping() rejects missing/extra keys and checks a deliberately limited
subset of annotations. It does not coerce input. to_mapping() is shallow.

The prototype supports concrete classes, unions, Literal, and parameterized
list/dict/tuple. It does not decode nested record classes or support arbitrary
typing constructs. Static type-checker behavior of dynamically added methods
has not yet been assessed.

## Result so far

The pure-Python checked constructor was considerably slower than simple
handwritten validation for a tiny schema. Direct instances have the same
layout as slotted dataclasses. There is **no current performance argument
for a new builtin**. See DESIGN.md and BENCHMARKS.md.

Next: gather concrete usage gaps, establish benchmark fairness and discuss
semantics with maintainers before any syntax or builtin proposal.
