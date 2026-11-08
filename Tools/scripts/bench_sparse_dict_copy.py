"""Compare dictionary copy paths for gh-161524."""

import platform
from statistics import median
from timeit import repeat


def sparse_dict(total, live, kind):
    keys = [f"k{i}" for i in range(total)] if kind == "str" else list(range(total))
    result = dict.fromkeys(keys, 1)
    for key in keys[:total - live]:
        del result[key]
    return result


def main():
    print(platform.python_version(), platform.python_build(), flush=True)
    for total, live in ((10, 4), (1000, 50), (1000, 300), (1000, 1000),
                        (100000, 30000), (100000, 5000), (100000, 3000),
                        (100000, 1000), (100000, 100), (100000, 10),
                        (100000, 1)):
        for kind in ("str", "int"):
            source = sparse_dict(total, live, kind)
            for name, expr in (
                ("copy", "source.copy()"),
                ("ctor", "dict(source)"),
                ("unpack", "{**source}"),
            ):
                number = 500 if total <= 1000 else 20
                seconds = median(repeat(expr, globals={"source": source},
                                        number=number, repeat=7))
                print(f"{kind:3} {live:>6}/{total:<6} {name:6} "
                      f"{seconds / number * 1e9:10.1f} ns/op", flush=True)


if __name__ == "__main__":
    main()
