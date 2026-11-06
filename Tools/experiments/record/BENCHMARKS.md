# Baseline microbenchmark observations

Local exploratory run: Python 3.13.5 on Linux x86_64, median of five timeit
repetitions, 10,000 live objects for tracemalloc.

| Case | Construction, ns/op | Approx. traced bytes/object |
|---|---:|---:|
| dict | 120.5 | 192.5 |
| TypedDict runtime | 253.1 | 192.5 |
| plain class | 251.4 | 104.5 |
| slotted class | 287.9 | 64.5 |
| dataclass | 307.9 | 104.5 |
| dataclass(slots=True) | 287.7 | 64.5 |
| NamedTuple | 475.4 | 80.6 |
| record (direct) | 264.4 | 64.5 |
| record.from_mapping | 4159.0 | 65.5 |
| handwritten checked mapping | 654.4 | 65.5 |

This is one run, not a performance claim. Checked mapping construction
performs more work than direct instantiation, and the handwritten validator
covers fewer cases. sys.getsizeof excludes referred objects (such as an
instance dictionary); tracemalloc includes allocation overhead and the list
of live objects. CPU frequency, test order, GC, input shape and interpreter
version affect numbers. Do not cite these figures without re-running and
checking equivalent workloads.

The current prototype demonstrates a cost, not a speedup. Future work should
include class creation, complex schemas, serialization, GC, pattern matching,
and multiple interpreter versions/machines.
