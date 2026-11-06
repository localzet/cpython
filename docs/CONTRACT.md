# Contract and limitations

## Directionality

Input compares old-valid payloads against a newer input schema.
Output compares new-produced payloads against previous reader expectations.

Breaking findings:
- Declared annotation narrowed with a concrete synthetic counterexample
  (bounded union/Optional/Literal and selected container grammar).
- New required input field, or optional field made mandatory.
- Previously accepted input name removed.
- Removed input field when newer provider forbids unknown keys.
- Declared Literal input set narrowed.
- Selected output key changed.
- Declared Literal output set expanded.

Review-required findings:
- New/removed output fields.
- Annotation changes outside the supported and provable grammar.
- Change in unknown-field policy, defaults, source library or object model.
- Different model class, because custom validators, converters and
  serializers are not fully described by metadata.

No known breakage is not a guarantee of compatible runtime behavior.

## Provider differences

TypedDict expresses static mapping rules; ReadOnly is not runtime frozen.
Dataclass defaults and omitted mapping keys are not interchangeable.
attrs aliases describe constructor arguments, while Pydantic separates
validation and serialization aliases. msgspec's typed decoding and direct
object construction use different guarantees.

The metadata excludes full nested/recursive schemes and arbitrary
subtyping, custom runtime validators, coercion, serialization settings,
default values and factories. Compare only trusted classes. Type-hint
evaluation and module imports can execute Python code.

## Evidence before language standardization

The two case studies are minimal field-level reconstructions from actual
public source commits, not complete application integration tests.
No PEP, builtin or CPython patch is warranted by this evidence alone.
