# Migration checker: verified experimental results

Code branch: [experimental/schema-compatibility-checker](https://github.com/localzet/cpython/tree/experimental/schema-compatibility-checker)

Research workflow:
[GitHub Actions #42307913453](https://github.com/localzet/cpython/actions/runs/42307913453)

[Machine-readable report artifacts](https://github.com/localzet/cpython/actions/runs/42307913453/artifacts/13546374965)

The workflow succeeded at commit 76f3f8ada50db45764fbb5bfa1f4f40e81419bd4:
- Python 3.13: 59 behavioral and CLI tests passed.
- Python 3.14: 59 behavioral and CLI tests passed.
- mypy and Pyright: public metadata typing fixtures plus migration/CLI
  implementation checks passed.
- CI artifacts: JSON reports for new required fields, output alias changes,
  and unknown runtime default changes, plus dependency snapshot.

The repository's **separate general Lint workflow failed** while loading
the external prek hook cache (missing hook executables); the project's
complete upstream lint suite therefore cannot be claimed as passed.

## Representative migration outcomes

| Comparison | Scope | Output |
|---|---|---|
| ApiV1 -> ApiV2Breaking | input | breaking_detected |
| ApiV1 -> ApiV2Relaxed | input | review_required (new optional field + runtime uncertainty) |
| AliasV1 -> AliasV2 | input | breaking_detected (input alias removed) |
| AliasV1 -> AliasV2 | output | breaking_detected (selected output name changed) |
| ObjectV1 -> ObjectV2 | both | review_required (default values opaque) |
| ApiV1 -> ApiV1 | both | no_known_breakage; NOT proof of runtime compatibility |

## Conclusion

A useful CI migration-reporting consumer can be implemented entirely with
the existing Python APIs, without adding a new object type or syntax.
The tool exposes where a migration *might* break clients and refuses to
infer full compatibility from field names alone.

This is one research consumer and synthetic API fixtures, not real-world
evidence across independent projects. The next useful validation is to
compare two actual production DTO revisions, reproduce detected breaking
cases against their real decoders, and record misses and false positives.

No upstream CPython changes or PEP submission are justified by this single
prototype alone. Full contract: [MIGRATION.md](MIGRATION.md).
