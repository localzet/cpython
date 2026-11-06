# Benchmark methodology and reproduction

This suite studies **different operations separately**. A plain dict
constructor is not equivalent to parsing JSON, nor is constructing a slotted
dataclass equivalent to validating an untrusted mapping.

## Environment

- CPython 3.13 and 3.14 for behavior; Python 3.13 for the benchmark job.
- GitHub-hosted ubuntu-24.04 runner, one job per benchmark.
- Direct versions pinned in requirements-research.txt:
  attrs 26.1.0, msgspec 0.22.0, Pydantic 2.14.3,
  mypy 2.4.1, Pyright 1.1.414.
- OS image, CPU microarchitecture, clock scaling and transitive dependency
  resolution may vary: run metadata and the environment should be preserved.

## Exact workload

Schema widths: **3, 10, 30** fields. Each is required and annotated int.
Values are deterministic ints, with f0 = 0. All codec implementations are
configured with strict validation and extra-field rejection where supported.
The test harness asserts rejection of a string at f0 and one extra field.

Operations recorded in raw JSON as separate groups:

1. construct — instantiate from keyword arguments. Some implementations
   validate on ordinary construction and others do not. **Not** the main
   cross-library comparison.
2. read_field — access the f0 attribute or dict key on an existing object.
3. equality — compare an existing object with a newly created same-type
   instance; the cost of constructing the RHS is therefore INCLUDED and
   this group must not be interpreted as pure equality performance.
4. validated_mapping — check an existing Python mapping and construct the
   declared type (manual checks + slotted dataclass, Record.from_mapping,
   validated attrs constructor, msgspec.convert, Pydantic.model_validate).
5. json_decode — JSON bytes to result with validation, plus a separate
   clearly labeled **parse-only dict** baseline that is not equivalent.
6. json_encode — object to UTF-8 JSON bytes. All outputs are checked to
   decode back to the original mapping; serialization internals differ.

The current equality operation is a **combined construct-and-compare** test
and should be revised to pure equality before being used for absolute
equality-performance claims. This is deliberately documented.

For each operation, timeit performs 100 warm-up calls and repeated
number=2000 timings; the median/min/max per operation are recorded in ns.
Samples are microbenchmarks, not real request throughput.

Memory: tracemalloc measures a batch of 1500 live objects independently for
each implementation; shallow sys.getsizeof is also recorded. Traced bytes per
instance include the holding list and allocation overhead, and exclude some
native allocator memory. They are approximate, not resident-set measurements.

## Reproduce

    cd Tools/experiments/record
    python -m pip install -r requirements-research.txt
    python -m unittest discover -s . -p 'test_*.py' -v
    python check_typing.py
    python benchmark_matrix.py --sizes 3 10 30 --number 2000 \
      --repeat 5 --instances 1500 --output results.json

Raw JSON includes library versions, interpreter version and parameters.
GitHub CI uploads its JSON as an artifact; the artifact is a result snapshot,
not a machine-independent performance specification.

## Interpretation checklist

- Compare validated_mapping to validated_mapping, not to unchecked construct.
- Read differences within the same runner/size; do not aggregate sizes.
- Pay attention to coercion and unknown-field policies.
- Use several independent machines and reruns before drawing conclusions.
- Preserve raw samples and stronger end-to-end workloads before proposing
  runtime implementation changes.
- Never infer C-level optimization potential from a slow Python validator.

## Follow-up experiments

- Deeply nested DTOs with a fixed depth and representative invalid inputs.
- Recursive structures and richer type annotations.
- Class-definition/import cost (important in cold-start deployments).
- Memory by peak RSS and GC pauses with equal object graphs.
- Pure comparison cost (pre-create two instances).
- Free-threaded builds, inheritance, pickling and match statements.
