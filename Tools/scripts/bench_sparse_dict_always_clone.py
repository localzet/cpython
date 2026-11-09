"""Compare sparse dict copy behavior with the threshold enabled or removed."""

import platform
from statistics import median
from timeit import repeat


def make_dict(total, live, kind):
    keys = [f"k{i}" for i in range(total)] if kind == "str" else list(range(total))
    source = dict.fromkeys(keys, 1)
    for key in keys[:total - live]:
        del source[key]
    return source


def main():
    print(platform.python_version(), platform.python_build(), flush=True)
    cases = (
        (10, 4), (1000, 300), (1000, 50), (1000, 1),
        (100000, 30000), (100000, 5000), (100000, 1600),
        (100000, 1562), (100000, 1500), (100000, 1000),
        (100000, 100), (100000, 10), (100000, 1),
        (500000, 1000), (500000, 100), (500000, 10), (500000, 1),
    )
    for total, live in cases:
        for kind in ("str", "int"):
            source = make_dict(total, live, kind)
            for operation, expression in (
                ("copy", "source.copy()"),
                ("ctor", "dict(source)"),
                ("unpack", "{**source}"),
            ):
                number = 200 if total <= 1000 else 15
                readings = repeat(
                    expression, globals={"source": source}, number=number,
                    repeat=9,
                )
                ns_per_op = median(readings) * 1e9 / number
                print(
                    f"{kind:3} {live:>6}/{total:<6} {operation:6}"
                    f" {ns_per_op:10.1f} ns/op",
                    flush=True,
                )


if __name__ == "__main__":
    main()
