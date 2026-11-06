"""Run mypy/Pyright against positive and intentionally-invalid code."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POS = ROOT / "tests/typing_cases/positive.py"
NEG = ROOT / "tests/typing_cases/negative.py"
EXPECTED = {
    i for i, line in enumerate(NEG.read_text().splitlines(), 1)
    if "# E:" in line
}


def run(argv: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        argv, cwd=ROOT, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout + result.stderr


def mypy() -> dict[str, object]:
    base = [sys.executable, "-m", "mypy", "--no-incremental", "--strict"]
    code, output = run([*base, str(POS)])
    if code:
        raise AssertionError(f"mypy positive failed:\n{output}")
    code, output = run([*base, str(NEG)])
    positions = {
        int(m.group(1)) for m in re.finditer(
            r"negative\.py:(\d+)(?::\d+)?: error:", output)
    }
    if code != 1 or not EXPECTED <= positions:
        raise AssertionError(f"mypy missed {EXPECTED - positions}:\n{output}")
    return {"checker": "mypy", "diagnosed": sorted(positions)}


def pyright() -> dict[str, object]:
    base = ["pyright", "--pythonversion", "3.13", "--outputjson"]
    code, output = run([*base, str(POS)])
    result = json.loads(output)
    if code or result["summary"]["errorCount"]:
        raise AssertionError(f"Pyright positive failed:\n{output}")
    code, output = run([*base, str(NEG)])
    result = json.loads(output)
    diagnosed = {
        d["range"]["start"]["line"] + 1
        for d in result["generalDiagnostics"]
        if d["severity"] == "error" and Path(d["file"]).name == "negative.py"
    }
    if code != 1 or not EXPECTED <= diagnosed:
        raise AssertionError(
            f"Pyright missed {EXPECTED - diagnosed}:\n{output}")
    return {"checker": "pyright", "diagnosed": sorted(diagnosed)}


if __name__ == "__main__":
    print(json.dumps({"expected": sorted(EXPECTED),
                      "results": [mypy(), pyright()]}, indent=2))
