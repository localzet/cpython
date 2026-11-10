"""Compare clone loops for very sparse dictionaries."""

from statistics import median
from timeit import repeat


def sparse(total, live, kind):
    keys = [f"k{i}" for i in range(total)] if kind == "str" else list(range(total))
    d = dict.fromkeys(keys, 1)
    for k in keys[:total - live]:
        del d[k]
    return d


def main():
    cases = (
        (1000, 1), (1000, 15), (1000, 50), (1000, 300),
        (100000, 1), (100000, 10), (100000, 100),
        (100000, 1000), (100000, 1500), (100000, 1562),
        (100000, 1600), (100000, 3000), (100000, 30000),
        (500000, 1), (500000, 100), (500000, 1000),
    )
    for total, live in cases:
        for kind in ("str", "int"):
            source = sparse(total, live, kind)
            for operation, expression in (
                ("copy", "source.copy()"),
                ("ctor", "dict(source)"),
                ("unpack", "{**source}"),
            ):
                number = 100 if total <= 1000 else 15
                values = repeat(expression, globals={"source": source},
                                number=number, repeat=7)
                print(f"{kind:3} {live:>6}/{total:<6} {operation:6} "
                      f"{median(values) / number * 1e9:11.1f} ns/op",
                      flush=True)


if __name__ == "__main__":
    main()
