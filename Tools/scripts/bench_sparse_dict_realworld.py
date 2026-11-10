"""Compare sparse dict copies with standard-library usage patterns.

Run with a newly built interpreter:
    ./python Tools/scripts/bench_sparse_dict_realworld.py
"""
import gc
import linecache
import platform
import statistics
import sys
import timeit
import weakref

REPEAT = 5


def report(label, func, number=300):
    samples = timeit.repeat(func, repeat=REPEAT, number=number)
    print(f"{label:43} {statistics.median(samples) / number * 1e9:11.0f} ns/op")


def sparse_dict(total, live):
    d = {str(i): i for i in range(total)}
    for i in range(total - live):
        del d[str(i)]
    return d


def benchmark_dict():
    print("\n--- dict.copy(): varying density ---")
    for total, live in ((100, 100), (100, 10), (1000, 1),
                        (1000, 100), (10000, 100), (10000, 1000)):
        d = sparse_dict(total, live)
        dense = dict(d)
        assert d == dense
        print(f"created={total}, live={live}, "
              f"sparse={d.__sizeof__()}B, compact={dense.__sizeof__()}B")
        report("sparse.copy()", d.copy)
        report("compact.copy()", dense.copy)


class Value:
    pass


def benchmark_weakref():
    print("\n--- weakref.WeakValueDictionary ---")
    for total, live in ((1000, 100), (10000, 100)):
        values = [Value() for _ in range(total)]
        w = weakref.WeakValueDictionary(
            {str(i): obj for i, obj in enumerate(values)}
        )
        survivors = values[-live:]
        del values
        gc.collect()
        assert len(w) == live
        assert len(survivors) == live
        print(f"created={total}, live={live}, data={w.data.__sizeof__()}B")
        report("w.data.copy()", w.data.copy, number=200)
        report("WeakValueDictionary.copy()", w.copy, number=100)


def benchmark_linecache():
    print("\n--- linecache.checkcache() ---")
    for total, live in ((1000, 100), (10000, 100)):
        linecache.clearcache()
        # Lazy cache entries need no filesystem access during checkcache().
        for i in range(total):
            linecache.cache[f"/virtual/module{i}.py"] = (lambda: [],)
        for i in range(total - live):
            del linecache.cache[f"/virtual/module{i}.py"]
        assert len(linecache.cache) == live
        print(f"created={total}, live={live}, cache={linecache.cache.__sizeof__()}B")
        report("linecache.cache.copy()", linecache.cache.copy, number=200)
        report("linecache.checkcache()", linecache.checkcache, number=100)
        assert len(linecache.cache) == live
    linecache.clearcache()


if __name__ == "__main__":
    print(platform.python_implementation(), sys.version.replace("\n", " "))
    print(platform.platform())
    benchmark_dict()
    benchmark_weakref()
    benchmark_linecache()
