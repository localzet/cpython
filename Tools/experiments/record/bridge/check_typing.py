"""Verify positive and expected-negative mypy/Pyright samples."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSITIVES = ROOT / "bridge" / "typecheck_cases" / "positive.py"
NEGATIVES = ROOT / "bridge" / "typecheck_cases" / "negative.py"
EXPECTED = {
    i for i, line in enumerate(NEGATIVES.read_text().splitlines(), start=1)
    if "# E:" in line
}


def invoke(args: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        args, capture_output=True, text=True, cwd=ROOT, check=False)
    return result.returncode, result.stdout + result.stderr


def check_mypy() -> dict[str, object]:
    base = [sys.executable, "-m", "mypy", "--no-incremental", "--strict"]
    status, output = invoke([*base, str(POSITIVES)])
    if status:
        raise AssertionError(f"mypy positive failed:\n{output}")
    status, output = invoke([*base, str(NEGATIVES)])
    diagnosed = {int(m.group(1)) for m in re.finditer(
        r"negative\.py:(\d+)(?::\d+)?: error:", output)}
    if status != 1 or not EXPECTED <= diagnosed:
        raise AssertionError(f"mypy missed {EXPECTED - diagnosed}:\n{output}")
    return {"tool": "mypy", "diagnosed": sorted(diagnosed)}


def check_pyright() -> dict[str, object]:
    base = ["pyright", "--pythonversion", "3.13", "--outputjson"]
    status, output = invoke([*base, str(POSITIVES)])
    data = json.loads(output)
    if status or data["summary"]["errorCount"]:
        raise AssertionError(f"Pyright positive failed:\n{output}")
    status, output = invoke([*base, str(NEGATIVES)])
    data = json.loads(output)
    diagnosed = {
        item["range"]["start"]["line"] + 1
        for item in data["generalDiagnostics"]
        if item["severity"] == "error"
        and Path(item["file"]).name == "negative.py"
    }
    if status != 1 or not EXPECTED <= diagnosed:
        raise AssertionError(
            f"Pyright missed {EXPECTED - diagnosed}:\n{output}")
    return {"tool": "pyright", "diagnosed": sorted(diagnosed)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", choices=("mypy", "pyright", "both"),
                        default="both")
    args = parser.parse_args()
    results = []
    if args.tool in ("mypy", "both"):
        results.append(check_mypy())
    if args.tool in ("pyright", "both"):
        results.append(check_pyright())
    print(json.dumps({"expected_negative_lines": sorted(EXPECTED),
                      "results": results}, indent=2))


if __name__ == "__main__":
    main()
