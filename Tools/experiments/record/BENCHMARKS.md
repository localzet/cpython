# Historical initial measurements (not the v2 benchmark)

Earlier local microbenchmark on Python 3.13.5/Linux x86_64. The original
experiment did not equate constructor and validator work. These numbers are
**historical** only; do not use them as a performance ranking.

| Case | Construction, ns/op | Approx. traced bytes/object |
|---|---:|---:|
| dict | 120.5 | 192.5 |
| TypedDict runtime | 253.1 | 192.5 |
| plain class | 251.4 | 104.5 |
| slotted class | 287.9 | 64.5 |
| dataclass | 307.9 | 104.5 |
| dataclass(slots=True) | 287.7 | 64.5 |
| NamedTuple | 475.4 | 80.6 |
| record direct | 264.4 | 64.5 |
| record.from_mapping | 4159.0 | 65.5 |
| handwritten validation | 654.4 | 65.5 |

For the *new* 3/10/30-field experiment, see benchmark_matrix.py,
METHODOLOGY.md and CI artifacts. The newer benchmark records each operation
separately, including strict mapping validation and JSON conversion.

Important caveats: sys.getsizeof excludes referenced objects, tracemalloc
contains a list of retained instances, and CPU scheduling/caches affect
nanoseconds. Direct constructor, mapping validation and JSON decode are not
equivalent tasks.
