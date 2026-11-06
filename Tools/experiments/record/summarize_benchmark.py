"""Produce a concise Markdown snapshot from benchmark_matrix.py JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def summarize(data: dict) -> str:
    rows = {(r["size"], r["operation"], r["implementation"]): r
            for r in data["results"]}
    memory = {(r["size"], r["implementation"]): r
              for r in data["memory"]}
    text = [
        "# Structured-record benchmark snapshot",
        "",
        f"Python: {data['environment']['python'].splitlines()[0]}",
        f"Platform: {data['environment']['platform']}",
        f"Packages: {data['environment']['versions']}",
        "",
        "Medians in microseconds per operation; smaller is better.",
        "Do not compare validated mapping or JSON decode to unchecked creation.",
    ]
    for size in data["parameters"]["sizes"]:
        text += [
            "",
            f"## {size} required integer fields",
            "",
            "| Implementation | Construct (µs) | Mapping validation (µs) "
            "| JSON decode (µs) | Approx. bytes/object |",
            "|---|---:|---:|---:|---:|",
        ]
        choices = [
            "dict", "TypedDict", "NamedTuple", "dataclass",
            "dataclass(slots)", "manual/dataclass", "record",
            "attrs", "msgspec", "pydantic",
        ]
        for impl in choices:
            def measurement(operation: str) -> str:
                found = rows.get((size, operation, impl))
                return (f"{found['median_ns'] / 1000:.2f}"
                        if found else "—")
            mem = memory.get((size, impl))
            memval = (str(mem["traced_bytes_per_object_approx"])
                      if mem else "—")
            text.append(
                f"| {impl} | {measurement('construct')} | "
                f"{measurement('validated_mapping')} | "
                f"{measurement('json_decode')} | {memval} |"
            )
    text += [
        "",
        "Details and caveats: METHODOLOGY.md. The figures are runner-specific "
        "exploratory observations, not benchmark claims.",
        "",
    ]
    return "\n".join(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = summarize(json.loads(args.source.read_text()))
    if args.output:
        args.output.write_text(report)
    print(report)


if __name__ == "__main__":
    main()
