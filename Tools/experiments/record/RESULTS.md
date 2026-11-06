# Record type study v2: first CI results

Snapshot: 2026-11-06 UTC (GitHub Actions runner, CPython 3.13.18,
ubuntu-24.04). This is a **single-run microbenchmark**, not a performance
claim or a recommended implementation.

- Workflow: https://github.com/localzet/cpython/actions/runs/42299039412
- Complete raw JSON, readable summary and dependency freeze:
  https://github.com/localzet/cpython/actions/runs/42299039412/artifacts/13541924737
- All four jobs passed: behavior (3.13, 3.14), mypy/Pyright, benchmark.
- Commands and limitations: METHODOLOGY.md
- Versions pinned by requirements-research.txt.

## Strict mapping input: microseconds per operation

| Implementation | 3 int fields | 10 int fields | 30 int fields |
|---|---:|---:|---:|
| Manual field check + slotted dataclass | 1.02 | 1.69 | 4.25 |
| Experimental Record.from_mapping | 5.02 | 13.11 | 37.51 |
| attrs constructor with validators | 0.69 | 1.14 | 3.48 |
| msgspec.convert(strict=True) | 0.56 | 0.65 | 0.95 |
| Pydantic.model_validate(strict=True) | 1.44 | 2.14 | 4.10 |

All implementations here reject a string in an int field and unexpected
extra keys. Each system may have different behavior for other annotations,
nested data, defaults, custom types, error paths and coercion.

## JSON bytes to validated object (microseconds)

| Implementation | 3 | 10 | 30 |
|---|---:|---:|---:|
| Manual validation after stdlib JSON parse | 3.56 | 6.23 | 17.00 |
| Record after stdlib JSON parse | 7.87 | 18.82 | 52.02 |
| attrs after stdlib JSON parse | 3.18 | 5.63 | 15.62 |
| msgspec.json.decode(type=...) | 0.28 | 0.43 | 0.88 |
| Pydantic.model_validate_json | 1.32 | 2.14 | 4.33 |

The msgspec and Pydantic APIs parse and validate with specialized
implementations. Record, manual and attrs cases parse first with json.loads.
These results should not be extrapolated to all JSON shapes.

## Slotted layout: plain creation and approximate memory

| Implementation | 3-field construction (µs) | 30-field construction (µs) | 30-field traced bytes/object |
|---|---:|---:|---:|
| dict | 0.13 | 0.19 | 840.5 |
| dataclass(slots=True) | 0.47 | 2.17 | 280.6 |
| Record (direct, unchecked) | 0.48 | 2.20 | 280.6 |
| msgspec.Struct | 0.25 | 0.94 | 280.6 |

The experimental record shares slotted dataclass storage, so parity is
expected. This memory metric is based on tracemalloc and a list of 1,500
live objects; it includes test-harness overhead and does not capture all
native allocations. It is not resident memory usage.

## What this means

1. A pure-Python boundary validator is not competitive with optimized
   libraries in this narrow workload.
2. Record's convenience currently consists of explicit conversion and
   improved nested error messages, *not* an advantage in object layout.
3. The explicit Record mixin improves typing. Both mypy 2.4.1 and Pyright
   1.1.414 accepted the positive fixture and rejected the four negative
   cases (wrong field type, positional invocation, undefined attribute,
   write to frozen field).
4. More convincing evidence would require representative DTO workloads,
   class-definition costs, nested models, complex annotations, real memory
   profiling, free-threaded Python and multiple machines.

**Recommendation:** do not propose a keyword, builtin or interpreter-level
C type on the current evidence. Investigate smaller stdlib/typing
interoperability changes first.
