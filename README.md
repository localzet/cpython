# localzet-schema-compat (experimental)

Independent, installable Python 3.13+ library for conservative, directional
API schema migration risk analysis. Based on TypedDict, dataclasses, attrs,
Pydantic v2 and msgspec.Struct inspection interfaces.

**Not a CPython change, PEP, runtime validator, or compatibility proof.**

## Install and run

    python -m pip install -e '.[all,dev]'
    python -m unittest discover -s tests -p 'test_*.py' -v
    python tools/check_typing.py

Base installation has no required runtime dependencies; the provider modules
are optional extras: attrs, pydantic, msgspec, all. The package is not
published to PyPI.

## CLI

The project includes source-derived sample fixtures:

    schema-compat tests.sample_models:ApiV1 tests.sample_models:ApiV2Breaking --direction input --json

    schema-compat tests.sample_models:AliasV1 tests.sample_models:AliasV2 --direction output

    schema-compat tests.sample_models:ObjectV1 tests.sample_models:ObjectV2 --fail-on review

Options: --direction input|output|both; --fail-on breaking|review|never;
--json for stable versioned machine output.

Exit 0 means the selected policy did not flag a matching risk, not that the
schemas are compatible. Exit 1 means risk threshold met; exit 2 means
invalid schema or import argument. Input asks if existing clients might
fail against new input requirements; output asks if old readers might
fail on newly emitted values.

## Python API

    from dataclasses import dataclass
    from schema_compat import inspect_schema, analyze_migration

    @dataclass
    class Old:
        id: int

    @dataclass
    class New:
        id: int
        email: str

    report = analyze_migration(inspect_schema(Old), inspect_schema(New),
                               direction="input")
    print(report.verdict, report.to_dict())

The analyzers report concrete changes where possible and require review
for unknown provider semantics, values, validators and serializers.

## Evidence and safety

See docs/CASE_STUDIES.md for two field-level reconstructions sourced from
upstream FastAPI and openai-python commits. These do NOT run the original
applications or establish full runtime compatibility. See docs/CONTRACT.md.

The CLI imports modules and get_type_hints evaluates annotations. Only
compare code you trust. This is not a service for running untrusted schemas.

## Repository status

GitHub connector does not support creating a new repository. The complete
standalone source tree is staged in a dedicated branch of localzet/cpython,
with no CPython source files on that branch. Download the source ZIP from
its GitHub Actions build, then push to a fresh repository when created.

Choose a license before external publication or distribution.
