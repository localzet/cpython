# Schema metadata interchange: experimental findings

Status: research only. This is not a CPython patch, accepted Python typing
specification, public PEP, runtime validator or portable JSON Schema.

## What works

The same read-only SchemaMeta API extracts a defined metadata subset from
five independently implemented model systems:
- stdlib TypedDict
- stdlib dataclasses
- attrs classes
- Pydantic v2 models
- msgspec.Struct

27 runtime regression cases cover optional and readonly fields, default
factories, frozen instances, field aliases, unknown input policies,
unsupported richer structures, and intentionally conservative comparisons.
mypy and Pyright check the public Protocol/SchemaMeta API with both positive
and deliberately-invalid code. Python 3.13/3.14 behavior checks passed.

CI: https://github.com/localzet/cpython/actions/runs/42306676239
Branch: https://github.com/localzet/cpython/tree/experimental/schema-metadata-interchange

## Main findings

1. **Discovery is feasible without changes to CPython.** All five providers
   offer documented inspection points that an adapter can normalize.
2. **Static typing and runtime validation cannot be unified by annotation
   inspection alone.** PEP 681 dataclass_transform is for synthesized static
   signatures; TypedDict is a structural mapping description.
3. **Input and output names are not one interchangeable namespace.**
   attrs constructor aliases, Pydantic directional aliases and msgspec wire
   rename options describe different operations.
4. **An optional key is not a default.** A missing TypedDict key may be
   materialized when converted to an object. Presence is lost without
   separate presence metadata.
5. **ReadOnly is not frozen.** TypedDict readonly is a type-checking property;
   frozen objects constrain runtime assignment but not deep mutation.
6. **A metadata-only comparison must be conservative.** Even when all visible
   field names and types match, custom converters, validators, default values,
   serialization and mutable state can differ.

## Candidate interface

For exploratory libraries, use an explicit opt-in method:

    class MetadataProvider(Protocol):
        def schema_metadata(self) -> SchemaMeta: ...

The SchemaMeta snapshot is a live Python object and must be inspected only
from trusted classes. It does not evaluate default factories, but
get_type_hints can evaluate annotation expressions.

Capabilities, versioning, loss reporting, field aliases, recursive and
parameterized schemas, input/output operation distinctions and trust
boundaries need a more complete design before a public interoperability
contract could be specified.

## Where to contribute next

A narrowly scoped **library-level metadata adapter and compatibility
reporter** is the most defensible next step. A consumer proof of concept that
checks schema migration compatibility would establish demand without
prematurely adding a sixth type-system construct.

After at least two independent consumers demonstrate useful cases that
cannot reasonably use current APIs, discuss a common protocol in the Python
typing community with maintainers of attrs, Pydantic and msgspec. Avoid
opening a PEP or an upstream CPython PR until that evidence exists.

## CI caveat

The experimental workflow passes. The repository's separate general Lint
workflow can fail while initializing the external prek hook environment
(missing hook executables under the runner cache). That failure is distinct
from the behavior and static-contract checks; it should not be reported as
the experiment's code passing the general CPython pre-commit suite.
