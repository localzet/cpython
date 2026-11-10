"""Compare sparse dict copying after deletions in different positions."""

import random
from statistics import median
from timeit import repeat


def make_sparse(total, live, kind, pattern):
    keys = [f"k{i}" for i in range(total)] if kind == "str" else list(range(total))
    source = dict.fromkeys(keys, 1)
    removed = total - live
    if pattern == "front":
        deletion_order = keys[:removed]
    elif pattern == "back":
        deletion_order = keys[live:]
    elif pattern == "middle":
        start = (total - removed) // 2
        deletion_order = keys[start:start + removed]
    elif pattern == "random":
        deletion_order = keys.copy()
        random.Random(161524).shuffle(deletion_order)
        deletion_order = deletion_order[:removed]
    else:
        raise ValueError(pattern)
    for key in deletion_order:
        del source[key]
    assert len(source) == live
    return source


def check_copies():
    for total, live in ((1000, 1), (1000, 15), (1000, 50),
                        (10000, 10), (10000, 500)):
        for kind in ("str", "int"):
            for pattern in ("front", "back", "middle", "random"):
                source = make_sparse(total, live, kind, pattern)
                expected = list(source.items())
                for result in (source.copy(), dict(source), {**source}):
                    assert len(result) == live
                    assert list(result.items()) == expected
                    assert all(k is ek and v is ev for
                               (k, v), (ek, ev) in zip(result.items(), expected))
                    result.clear()
                    assert list(source.items()) == expected
    print("patterned copy checks passed", flush=True)


def main():
    check_copies()
    for total, live in ((1000, 1), (1000, 15), (1000, 300),
                        (100000, 1), (100000, 100),
                        (100000, 1500), (100000, 3000)):
        for kind in ("str", "int"):
            for pattern in ("front", "back", "middle", "random"):
                source = make_sparse(total, live, kind, pattern)
                number = 100 if total <= 1000 else 15
                timings = repeat("source.copy()", globals={"source": source},
                                 number=number, repeat=7)
                print(f"{kind:3} {pattern:6} {live:>6}/{total:<6} copy "
                      f"{median(timings) / number * 1e9:10.1f} ns/op", flush=True)


if __name__ == "__main__":
    main()
