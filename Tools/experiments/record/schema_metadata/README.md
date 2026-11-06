# Schema metadata interchange (research)

This directory explores a common **descriptive** field model across TypedDict,
dataclasses, attrs, Pydantic v2 and msgspec.Struct. It does **not** add a Python
builtin, keyword, validator or standard-library API. It is not a PEP.

## Reproduce

Run from Tools/experiments/record (Python 3.13+):

    python -m pip install -r requirements-research.txt
    python -m unittest discover -s schema_metadata -p 'test_*.py' -v

## API

    from dataclasses import dataclass, field
    from typing import NotRequired, TypedDict
    from schema_metadata.metadata import inspect_schema
    from schema_metadata.compare import compare_metadata

    class Wire(TypedDict):
        id: int
        tags: NotRequired[list[str]]

    @dataclass(slots=True)
    class Model:
        id: int
        tags: list[str] = field(default_factory=list)

    wire = inspect_schema(Wire)
    model = inspect_schema(Model)
    assert wire.by_name()["tags"].input_required is False
    assert model.by_name()["tags"].default_kind == "factory"
    print(compare_metadata(wire, model).verdict)

FieldMeta stores field name, Python annotation, accepted input names, selected
output name, requiredness, default kind, and independent readonly/frozen
indicators. SchemaMeta stores the provider, mapping/object representation,
extra-field policy, validation category and explicit limitations.

MetadataProvider.schema_metadata() allows an opt-in provider. The API does
not monkeypatch input classes. compare_metadata reports differences and
uncertainties: no runtime equivalence or type assignability is claimed.

The output is in-memory Python metadata, *not JSON Schema*. Type objects,
arbitrary validators, codecs, callable defaults, nested references and
Annotated metadata cannot be serialized by this API. Nothing executes
default factories. get_type_hints may execute annotation expressions, so
introspect **trusted code only**.

Read SPEC.md and GAPS.md before interpreting any comparison as a contract.


## Independent migration checker consumer

An experimental *consumer* of SchemaMeta is available in
[MIGRATION-README.md](MIGRATION-README.md): it generates directional
input/output migration risk reports, deterministic versioned JSON and
CI-friendly exit codes. See [MIGRATION.md](MIGRATION.md) for exact rules and
[MIGRATION-RESULTS.md](MIGRATION-RESULTS.md) for verified CI evidence.
It does not claim complete compatibility or propose a CPython builtin.
