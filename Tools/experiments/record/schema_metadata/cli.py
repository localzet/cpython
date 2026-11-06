"""Run trusted schema version comparisons without changing CPython.

Usage from Tools/experiments/record:
  python -m schema_metadata.cli \
      schema_metadata.fixtures:ApiV1 \
      schema_metadata.fixtures:ApiV2Breaking --direction input --json
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections.abc import Sequence
from typing import Literal

from .metadata import UnsupportedSchema, inspect_schema
from .migration import MigrationReport, analyze_migration

ExitPolicy = Literal["breaking", "review", "never"]


def _load_class(identifier: str) -> type:
    if ":" not in identifier:
        raise ValueError("Expected import path module:ClassName")
    module_path, qualname = identifier.split(":", 1)
    if not module_path or not qualname:
        raise ValueError("Expected import path module:ClassName")
    obj: object = importlib.import_module(module_path)
    for component in qualname.split("."):
        if not component.isidentifier() or component.startswith("_"):
            raise ValueError(f"Invalid public class path component {component!r}")
        obj = getattr(obj, component)
    if not isinstance(obj, type):
        raise TypeError(f"{identifier!r} does not resolve to a class")
    return obj


def _format_text(report: MigrationReport) -> str:
    out = [
        f"Schema migration: {report.direction} — {report.verdict}",
        f"  old: {report.old.provider} / "
        f"{report.old.model.__module__}:{report.old.model.__qualname__}",
        f"  new: {report.new.provider} / "
        f"{report.new.model.__module__}:{report.new.model.__qualname__}",
    ]
    for issue in report.issues:
        out.append(
            f"  {issue.severity.upper():8s} [{issue.direction}] "
            f"{issue.path}: {issue.code}"
        )
        out.append(f"    {issue.explanation}")
    out.append("")
    out.append(str(report.to_dict()["disclaimer"]))
    return "\n".join(out)


def _policy_fails(report: MigrationReport, policy: ExitPolicy) -> bool:
    if policy == "never":
        return False
    if policy == "review":
        return report.verdict in ("breaking_detected", "review_required")
    return report.verdict == "breaking_detected"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Conservative metadata-level API migration risk report.")
    parser.add_argument("old", help="Trusted import path: module:ClassName")
    parser.add_argument("new", help="Trusted import path: module:ClassName")
    parser.add_argument("--direction", choices=("input", "output", "both"),
                        default="both")
    parser.add_argument("--json", action="store_true",
                        help="Produce versioned JSON instead of text.")
    parser.add_argument("--fail-on", choices=("breaking", "review", "never"),
                        default="breaking",
                        help="Exit 1 when a matching risk is reported.")
    args = parser.parse_args(argv)
    try:
        old = inspect_schema(_load_class(args.old))
        new = inspect_schema(_load_class(args.new))
        report = analyze_migration(old, new, direction=args.direction)
    except (ImportError, AttributeError, ValueError, TypeError,
            UnsupportedSchema) as exc:
        print(f"Schema loading failed: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(_format_text(report))
    return int(_policy_fails(report, args.fail_on))


if __name__ == "__main__":
    raise SystemExit(main())
