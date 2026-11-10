"""Summarize research-only dict-copy instrumentation logs.

Counters are per instrumented Python process. They cover copies reaching
copy_lock_held_untracked(), not every possible way to construct a dictionary.
"""
import re
import sys
from pathlib import Path

FIELDS = ("total", "empty", "split", "compact", "light_deletions",
          "sparse", "sparse_large", "very_sparse")
MERGE_FIELDS = ("merge_candidates", "merge_sparse", "merge_sparse_large")


def summarize(path):
    counts = {name: 0 for name in (*FIELDS, *MERGE_FIELDS)}
    processes = 0
    if not path.exists():
        print(f"{path}: no instrumentation output")
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("DICT_COPY_PROFILE "):
            continue
        values = dict((name, int(value))
                      for name, value in re.findall(r"(\w+)=(\d+)", line))
        if not all(name in values for name in FIELDS):
            raise ValueError(f"Incomplete dict-copy profile: {line}")
        processes += 1
        for name in FIELDS:
            counts[name] += values[name]
        for name in MERGE_FIELDS:
            counts[name] += values.get(name, 0)
    total = counts["total"]
    percent = counts["sparse"] * 100 / total if total else 0
    print(f"{path}: processes={processes}, total={total}, "
          f"sparse={counts['sparse']} ({percent:.5f}%), "
          f"sparse_large={counts['sparse_large']}, "
          f"very_sparse={counts['very_sparse']}, "
          f"compact={counts['compact']}, "
          f"light_deletions={counts['light_deletions']}, "
          f"empty={counts['empty']}, split={counts['split']}, "
          f"merge_candidates={counts['merge_candidates']}, "
          f"merge_sparse={counts['merge_sparse']}, "
          f"merge_sparse_large={counts['merge_sparse_large']}")


if __name__ == "__main__":
    for filename in sys.argv[1:]:
        summarize(Path(filename))
