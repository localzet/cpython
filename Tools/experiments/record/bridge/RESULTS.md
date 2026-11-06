# TypedDict/dataclass adapter: first CI measurements

Measured on GitHub Actions, Python 3.13.18, ubuntu-24.04, Linux x86_64.
This is **one run**, so these numbers are illustrative microbenchmarks, not
general performance or suitability rankings.

- [Passing CI run](https://github.com/localzet/cpython/actions/runs/42303518646)
- [Raw timeit samples, summary and dependency freeze](https://github.com/localzet/cpython/actions/runs/42303518646/artifacts/13545700575)
- Versions: msgspec 0.22.0, Pydantic 2.14.3.
- CI result: behavior tests on 3.13 and 3.14, mypy/Pyright checks,
  and the benchmark all succeeded.

## Strict mapping validation, microseconds per call

| Implementation | 3 fields | 10 fields | 30 fields |
|---|---:|---:|---:|
| Handwritten check + slotted dataclass | 0.97 | 2.03 | 7.87 |
| SchemaBridge + slotted dataclass | 2.41 | 4.78 | 14.33 |
| msgspec.convert(strict=True) | 0.36 | 0.43 | 0.66 |
| Pydantic.model_validate(strict=True) | 1.08 | 1.63 | 3.19 |

Each system rejects an unexpected field and a string where an int is
required in this workload, but their complete semantics remain different.

## JSON decoding with validation, microseconds per call

| Implementation | 3 fields | 10 fields | 30 fields |
|---|---:|---:|---:|
| Handwritten + json.loads | 2.45 | 4.39 | 12.55 |
| SchemaBridge + json.loads | 4.01 | 7.20 | 19.34 |
| msgspec.json.decode | 0.17 | 0.28 | 0.59 |
| Pydantic.model_validate_json | 1.03 | 1.65 | 3.13 |

msgspec and Pydantic use optimized decoding implementations while the
prototype uses the standard-library json parser followed by Python checks.

## Adapter compilation, microseconds per schema

| Number of fields | Compile SchemaBridge |
|---|---:|
| 3 | 29.19 |
| 10 | 66.94 |
| 30 | 170.17 |

Construction of the dataclass and TypedDict class objects is **excluded**.
Compilation resolves type hints and builds the field-specific plan.
The adapter is meant to be reused, not rebuilt on every request.

## Interpretation

- The adapter is not competitive with optimized dedicated libraries in
  this narrow speed test. It does, however, provide an explicit prototype
  for a potential common interoperability contract.
- TypedDict and dataclass are not interchangeable runtime objects.
  Missing optional keys are materialized as dataclass defaults, so
  conversion is canonicalizing rather than lossless.
- The static type checkers understand the model return value, but there is
  no sound implicit TypedDict return type for an arbitrary generic adapter.
- Evidence for a CPython change remains insufficient. A small adapter
  protocol or schema metadata improvement is a more plausible research
  direction than a new keyword or builtin.

See CONTRACT.md and METHODOLOGY.md. Wider or nested schemas, cold-start
realistic workloads, error paths and multiple hardware environments are
necessary before drawing any upstream performance conclusions.
