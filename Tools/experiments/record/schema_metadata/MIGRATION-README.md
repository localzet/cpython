# Schema migration checker — experimental consumer

An independent **consumer of the previous schema-metadata research**.
It finds *metadata-level migration risks* when an API's schema changes, but
does not prove Python runtime compatibility or replace application tests.

## Quick start

Python 3.13 or newer. From the CPython fork checkout:

    cd Tools/experiments/record
    python -m pip install -r requirements-research.txt
    python -m unittest discover -s schema_metadata -p 'test_*.py' -v

Compare two **trusted** schema classes:

    python -m schema_metadata.cli \
      schema_metadata.fixtures:ApiV1 \
      schema_metadata.fixtures:ApiV2Breaking \
      --direction input --json

Try an output alias rename:

    python -m schema_metadata.cli \
      schema_metadata.fixtures:AliasV1 \
      schema_metadata.fixtures:AliasV2 --direction output

And a subtle, unknown change in runtime defaults:

    python -m schema_metadata.cli \
      schema_metadata.fixtures:ObjectV1 \
      schema_metadata.fixtures:ObjectV2 --fail-on review

The CLI imports the given modules and uses get_type_hints(). This executes
trusted Python code; **never load arbitrary untrusted user modules**.

## Why input and output are separate

The two changes are directionally different:

**Input migration:** A server upgraded from Old to New. Old clients continue
to send payloads that were valid under Old. If New requires an extra field
or stops accepting an old alias, some previous clients may fail.

**Output migration:** The server upgraded from Old to New, but old readers
still expect the previous output keys and value set. If the selected
serializer's name changes, old readers may break. Added/removed output
fields are classified as **review required**, not automatically safe/unsafe,
because the metadata cannot guarantee actual emission or old consumer rules.

## What the results mean

- **breaking_detected:** a declared contract was narrowed in a way that
  breaks at least one previously permitted use, *assuming the specified
  provider operation and input/output interpretation*.
- **review_required:** a potentially relevant change or missing evidence.
  Do not auto-approve as compatible.
- **no_known_breakage:** the selected limited metadata rules found no risk.
  It does not mean complete, runtime or semantic compatibility.

Issues have severities breaking, review and info. Machine-readable JSON has
format_version=1, deterministic issue ordering, source model references and
a disclaimer. The default CLI exit policy fails on breaking findings; opt in
to --fail-on review for a stricter CI gate, or --fail-on never for reporting.

Exit codes: 0 = policy passes, 1 = configured risk gate fails,
2 = import/schema/argument error. Argument parse errors also exit 2.

## Supported and unknown behavior

The checker recognizes:
- New required/optional fields and removed input fields.
- Optional field becoming required.
- Input aliases lost/added; output alias renamed.
- Literal value-set contractions/expansions in each direction.
- Changes in declared unknown-key policy.
- Possible default changes and incompatible object representations.

It **does not** infer arbitrary type variance, validation rules,
serialization hooks, dynamic defaults, recursive schemas, version-specific
config overrides or actual old-reader behavior. These are explicitly
marked for review rather than reported as compatible.

The static metadata inherited from the previous study describes provider
specific operations. For example, a Pydantic output alias describes
model_dump(by_alias=True), whereas an attrs alias describes a constructor
parameter. The same field name does not imply equivalent APIs.

## Files

- migration.py: analysis API, versioned JSON output.
- cli.py: CLI for CI gates or manual use.
- fixtures.py: deliberately versioned API schemas.
- test_migration.py: regression and end-to-end CLI tests.
- MIGRATION.md: precise decision rules, caveats, examples.

The generalized field metadata, original adapter comparison, and reports
remain in metadata.py, compare.py, SPEC.md, GAPS.md and RESULTS.md.

**Upstream decision:** This is a self-contained research tool, not a
proposal for a new Python builtin or keyword. It should be tested against
actual application schema migrations before proposing any common protocol.
