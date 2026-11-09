"""Measure dictresize after deleting almost every entry in a full table."""

from statistics import median
from time import perf_counter_ns


def make_sparse_dict(total, live, key_type):
    keys = range(total) if key_type == "int" else [f"k{i}" for i in range(total)]
    source = dict.fromkeys(keys)
    for key in keys[:total - live]:
        del source[key]
    return source


def run_case(total, live, key_type):
    measurements = []
    for _ in range(9):
        source = make_sparse_dict(total, live, key_type)
        size_before = source.__sizeof__()
        start = perf_counter_ns()
        source[-1] = None
        elapsed = perf_counter_ns() - start
        size_after = source.__sizeof__()
        if size_before == size_after:
            raise AssertionError(
                f"resize was not triggered: {key_type=} {total=} {live=}"
            )
        measurements.append(elapsed)
    return median(measurements) / 1e3


def main():
    # These are 2/3 of the respective power-of-two table sizes.
    for total in (5461, 43690, 87381, 174762):
        for live in (1, 10, 100):
            for key_type in ("str", "int"):
                micros = run_case(total, live, key_type)
                print(
                    f"{key_type:3} {live:>5}/{total:<6} "
                    f"first insertion after deletions: {micros:9.1f} us",
                    flush=True,
                )


if __name__ == "__main__":
    main()
