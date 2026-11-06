# Changelog

## 0.1.0a1 — candidate; not yet published to PyPI

- Standalone distributable source tree and CLI, independent of CPython.
- Directional input/output migration reports and JSON for CI.
- Declared annotation narrowing with synthetic counterexamples (selected
  Literal, Union, Optional, list, dict and tuple forms).
- Field-level checks derived from public FastAPI and openai-python commits.
- Behavior tests on Python 3.13/3.14, mypy, Pyright and wheel/sdist build.
- Prepared PyPI Trusted Publishing workflow, disabled until a real release.

No claim of full schema compatibility or production readiness.
