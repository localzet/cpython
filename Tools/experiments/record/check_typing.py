"""Run positive and deliberately-invalid samples in mypy and Pyright."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POSITIVE = ROOT / "typecheck_cases" / "positive.py"
NEGATIVE = ROOT / "typecheck_cases" / "negative.py"
EXPECTED = {
    i: line.strip().split("# E:", 1)[1].strip()
    for i, line in enumerate(NEGATIVE.read_text().splitlines(), start=1)
    if "# E:" in line
}


def execute(command: list[str]):
    result = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, check=False,
    )
    return result.returncode, result.stdout + "\n" + result.stderr


def verify_mypy():
    base = [sys.executable, "-m", "mypy", "--no-incremental", "--strict"]
    ok, output = execute([*base, str(POSITIVE)])
    if ok:
        raise AssertionError(f"mypy positive fixture failed:\n{output}")
    bad, output = execute([*base, str(NEGATIVE)])
    if bad != 1:
        raise AssertionError(f"mypy negative exit code {bad}:\n{output}")
    diagnosed = {
        int(match.group(1))
        for match in re.finditer(r"negative\.py:(\d+)(?::\d+)?: error:", output)
    }
    missing = set(EXPECTED) - diagnosed
    if missing:
        raise AssertionError(
            f"mypy missed required negative cases {missing}:\n{output}")
    return {"tool": "mypy", "negative_lines": sorted(diagnosed)}


def verify_pyright():
    base = ["pyright", "--pythonversion", "3.13", "--outputjson"]
    code, output = execute([*base, str(POSITIVE)])
    data = json.loads(output)
    if code or data["summary"]["errorCount"]:
        raise AssertionError(f"Pyright positive fixture failed:\n{output}")
    code, output = execute([*base, str(NEGATIVE)])
    data = json.loads(output)
    if code != 1:
        raise AssertionError(f"Pyright negative exit code {code}:\n{output}")
    diagnosed = {
        item["range"]["start"]["line"] + 1
        for item in data["generalDiagnostics"]
        if item["severity"] == "error"
        and Path(item["file"]).name == "negative.py"
    }
    missing = set(EXPECTED) - diagnosed
    if missing:
        raise AssertionError(
            f"Pyright missed required negative cases {missing}:\n{output}")
    return {"tool": "pyright", "negative_lines": sorted(diagnosed)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", choices=("mypy", "pyright", "both"),
                        default="both")
    args = parser.parse_args()
    results = []
    if args.tool in ("mypy", "both"):
        results.append(verify_mypy())
    if args.tool in ("pyright", "both"):
        results.append(verify_pyright())
    print(json.dumps({"expected_negative_lines": EXPECTED,
                      "results": results}, indent=2))


if __name__ == "__main__":
    main()
