"""Render a compact, human-readable summary of bridge benchmark JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def summarize(data: dict) -> str:
    observations = {
        (r["width"], r["operation"], r["implementation"]):
            r["median_ns"] / 1000
        for r in data["results"]
    }
    lines = [
        "# TypedDict/dataclass bridge benchmark",
        "",
        f"Python: {data['python'].splitlines()[0]}",
        f"Runner: {data['platform']}",
        f"Libraries: {data['libraries']}",
        "",
        "Microseconds per operation (median); smaller is better.",
    ]
    cases = [
        ("manual/dataclass", "Handwritten check + dataclass"),
        ("bridge/dataclass", "SchemaBridge + dataclass"),
        ("msgspec/struct", "msgspec.Struct"),
        ("pydantic/model", "Pydantic model"),
    ]
    for width in data["parameters"]["sizes"]:
        lines.extend([
            "",
            f"## {width} required integer fields",
            "",
            "| Implementation | Validate mapping | Decode JSON "
            "| Encode mapping | Encode JSON |",
            "|---|---:|---:|---:|---:|",
        ])
        for impl, title in cases:
            cells = []
            for operation in (
                "validate_mapping", "decode_json",
                "encode_mapping", "encode_json"
            ):
                value = observations.get((width, operation, impl))
                cells.append(f"{value:.2f}" if value is not None else "—")
            lines.append(f"| {title} | {' | '.join(cells)} |")
        compiled = observations[(width, "compile_adapter", "bridge/dataclass")]
        lines.extend([
            "",
            f"Bridge schema compilation: **{compiled:.2f} µs** per adapter.",
        ])
    lines.extend([
        "",
        "Source: recorded timeit samples in bridge-results.json.",
        "A flat integer schema does not establish equivalence of all "
        "validation and serialization semantics.",
        "See METHODOLOGY.md and CONTRACT.md for the limitations.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = summarize(json.loads(args.source.read_text()))
    if args.output:
        args.output.write_text(result)
    print(result)


if __name__ == "__main__":
    main()
