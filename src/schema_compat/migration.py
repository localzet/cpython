"""Directional, conservative migration analysis for schema metadata.

A migration report is a *risk assessment*, not validation of Python runtime
behavior or proof of typing assignability. Compare trusted model definitions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from collections.abc import Callable
from typing import Literal, get_args, get_origin

from .metadata import FieldMeta, SchemaMeta
from .type_relations import assess_subset

Direction = Literal["input", "output", "both"]
Severity = Literal["breaking", "review", "info"]
Verdict = Literal["breaking_detected", "review_required", "no_known_breakage"]

_DISCLAIMER = (
    "Metadata-only findings do not establish runtime compatibility; "
    "validators, converters, custom serializers, defaults and nested types "
    "may differ. Input refers to old clients sending to a new schema. "
    "Output refers to old readers consuming new emitted payloads."
)


@dataclass(frozen=True, slots=True)
class MigrationIssue:
    direction: Literal["input", "output", "general"]
    severity: Severity
    code: str
    path: str
    explanation: str


@dataclass(frozen=True, slots=True)
class MigrationReport:
    old: SchemaMeta
    new: SchemaMeta
    direction: Direction
    issues: tuple[MigrationIssue, ...]
    verdict: Verdict

    def to_dict(self) -> dict[str, object]:
        """JSON-safe, stable schema for CI artifacts and tooling."""
        return {
            "format_version": 1,
            "direction": self.direction,
            "old": {
                "provider": self.old.provider,
                "model": _model_id(self.old.model),
            },
            "new": {
                "provider": self.new.provider,
                "model": _model_id(self.new.model),
            },
            "verdict": self.verdict,
            "counts": {
                "breaking": sum(i.severity == "breaking" for i in self.issues),
                "review": sum(i.severity == "review" for i in self.issues),
                "info": sum(i.severity == "info" for i in self.issues),
            },
            "issues": [asdict(issue) for issue in self.issues],
            "disclaimer": _DISCLAIMER,
        }


def _model_id(model: type) -> str:
    return f"{model.__module__}:{model.__qualname__}"


def _literal_values(annotation: object) -> tuple[object, ...] | None:
    if get_origin(annotation) is Literal:
        return get_args(annotation)
    return None


def _includes(left: tuple[object, ...], right: tuple[object, ...]) -> bool:
    """Does left contain every member of right, with exact types?"""
    return all(any(
        type(candidate) is type(value) and candidate == value
        for candidate in left
    ) for value in right)


def _analyze_annotations(old: FieldMeta, new: FieldMeta,
                         direction: Literal["input", "output"],
                         add: _Add) -> None:
    if old.annotation == new.annotation:
        return

    before = _literal_values(old.annotation)
    after = _literal_values(new.annotation)
    older, newer = (
        (old.annotation, new.annotation) if direction == "input"
        else (new.annotation, old.annotation)
    )
    inclusion = assess_subset(older, newer)
    reverse = assess_subset(newer, older)
    if inclusion.relation == "excluded":
        code = ("literal_set_contract" if before is not None
                and after is not None else "declared_type_narrowed")
        add(direction, "breaking", code, old.name,
            f"A synthetic value allowed by the previous declared contract "
            f"is excluded by the newer contract: {inclusion.witness}. "
            "This concerns annotations, not actual provider-specific "
            "coercion, validators or serialization settings.")
        return
    if inclusion.relation == "included" and reverse.relation == "excluded":
        code = ("literal_set_relaxed" if before is not None
                and after is not None else "declared_type_relaxed")
        add(direction, "info", code, old.name,
            "The newer declared value set is broader in this direction. "
            "Custom runtime behavior has not been established.")
        return
    if inclusion.relation == "included" and reverse.relation == "included":
        add(direction, "review", "type_equivalent_metadata", old.name,
            "The supported annotation subset appears equivalent, "
            "but provider-specific runtime behavior remains unknown.")
        return
    add(direction, "review", "annotation_changed", old.name,
        f"The annotated type changed from {old.annotation!r} to "
        f"{new.annotation!r}. The analyzer could not prove the relationship "
        "within its supported grammar; coercion and runtime rules are unknown.")

_Add = Callable[[Literal["input", "output", "general"], Severity, str, str, str], None]


def _input_migration(old: SchemaMeta, new: SchemaMeta, add: _Add) -> None:
    old_fields = old.by_name()
    new_fields = new.by_name()
    for name in sorted(set(old_fields) | set(new_fields)):
        a = old_fields.get(name)
        b = new_fields.get(name)
        if a is None and b is not None:
            if b.input_required:
                add("input", "breaking", "new_required_field", name,
                    "Existing clients may omit this newly required input field.")
            else:
                add("input", "info", "new_optional_field", name,
                    "New optional input field; existing clients can omit it.")
            continue
        if b is None and a is not None:
            if new.extra_policy == "forbid":
                add("input", "breaking", "removed_input_field", name,
                    "Old payloads may contain a field now rejected as unknown.")
            else:
                add("input", "review", "removed_input_field", name,
                    "Old payloads may contain a removed field; it may be "
                    "ignored, rejected, or handled as an extension.")
            continue
        if a is None or b is None:
            continue

        if not a.input_required and b.input_required:
            add("input", "breaking", "field_now_required", name,
                "Old clients could omit this field; the new contract requires it.")
        elif a.input_required and not b.input_required:
            add("input", "info", "field_now_optional", name,
                "The new contract permits omitting this field.")

        lost_names = sorted(set(a.input_names) - set(b.input_names))
        if lost_names:
            add("input", "breaking", "input_name_removed", name,
                f"Old clients could use input names {lost_names!r}, "
                "which the new declared contract no longer recognizes.")
        added_names = sorted(set(b.input_names) - set(a.input_names))
        if added_names:
            add("input", "info", "input_name_added", name,
                f"New accepted input names: {added_names!r}.")

        _analyze_annotations(a, b, "input", add)
        if a.default_kind != b.default_kind:
            add("input", "review", "default_kind_changed", name,
                f"Default kind changed from {a.default_kind!r} to "
                f"{b.default_kind!r}; resulting object behavior may differ.")
        elif a.default_kind != "missing" and old.model is not new.model:
            add("input", "review", "default_value_opaque", name,
                "The adapter exposes default kind, not actual values or "
                "factories. Equality of defaults cannot be established.")

    if old.extra_policy != new.extra_policy:
        if old.extra_policy in ("allow", "open") and new.extra_policy == "forbid":
            add("input", "review", "extra_inputs_restricted", "$",
                "The new schema forbids unknown fields while the old schema "
                "described a more open input contract. Provider semantics vary.")
        else:
            add("input", "review", "extra_inputs_policy_changed", "$",
                f"Unknown-field policy changed from {old.extra_policy!r} "
                f"to {new.extra_policy!r}; behavior must be verified.")


def _output_migration(old: SchemaMeta, new: SchemaMeta, add: _Add) -> None:
    old_fields = old.by_name()
    new_fields = new.by_name()
    for name in sorted(set(old_fields) | set(new_fields)):
        a = old_fields.get(name)
        b = new_fields.get(name)
        if a is None and b is not None:
            add("output", "review", "new_output_field", name,
                "New output may contain a field that strict old readers reject. "
                "Whether it is emitted depends on serializer settings.")
            continue
        if b is None and a is not None:
            add("output", "review", "output_field_removed", name,
                "An output field disappeared; old readers may rely on it. "
                "Emission/requiredness cannot be inferred from input metadata.")
            continue
        if a is None or b is None:
            continue

        if a.output_name != b.output_name:
            add("output", "breaking", "output_name_changed", name,
                f"Selected output key changed from {a.output_name!r} "
                f"to {b.output_name!r}; existing readers may use the old key.")
        _analyze_annotations(a, b, "output", add)
        if a.default_kind != b.default_kind:
            add("output", "review", "output_default_kind_changed", name,
                "Default configuration changed; output omission and values "
                "depend on runtime serializer settings.")
        elif a.default_kind != "missing" and old.model is not new.model:
            add("output", "review", "output_default_value_opaque", name,
                "Default values/factories are not represented in metadata.")


def analyze_migration(old: SchemaMeta, new: SchemaMeta,
                      *, direction: Direction = "both") -> MigrationReport:
    """Risk analysis, deliberately NOT a compatibility verifier.

    - input: payloads allowed by old schema arriving at a new endpoint;
    - output: newly emitted payloads arriving at an old reader.
    """
    if direction not in ("input", "output", "both"):
        raise ValueError(f"Unsupported direction {direction!r}")

    issues: list[MigrationIssue] = []

    def add(scope: Literal["input", "output", "general"], severity: Severity,
            code: str, path: str, explanation: str) -> None:
        issues.append(MigrationIssue(scope, severity, code, path, explanation))

    if old.provider != new.provider:
        add("general", "review", "provider_changed", "$",
            f"Provider changed from {old.provider!r} to {new.provider!r}; "
            "input/output operations may not be equivalent.")
    if old.representation != new.representation:
        add("general", "review", "representation_changed", "$",
            "A mapping and an attribute object have different runtime contracts.")
    if old.validation != new.validation:
        add("general", "review", "validation_mode_changed", "$",
            "The validator/decoder implementation is not captured by metadata.")
    if old.frozen != new.frozen:
        add("general", "review", "frozen_policy_changed", "$",
            "Instance mutation semantics differ or cannot be determined.")

    if direction in ("input", "both"):
        _input_migration(old, new, add)
    if direction in ("output", "both"):
        _output_migration(old, new, add)

    if old.model is not new.model:
        add("general", "review", "runtime_behavior_unverified", "$",
            "Even identical visible fields do not prove equivalence of "
            "validators, converters, custom serializers or default values.")

    # An older schema provider may have compiled/unknown behavior that is not
    # observable through FieldMeta. Do not claim a proof of compatibility.
    order = {"breaking": 0, "review": 1, "info": 2}
    issues.sort(key=lambda x: (order[x.severity], x.direction, x.path, x.code))
    verdict: Verdict = (
        "breaking_detected" if any(i.severity == "breaking" for i in issues)
        else "review_required" if any(i.severity == "review" for i in issues)
        else "no_known_breakage"
    )
    return MigrationReport(old, new, direction, tuple(issues), verdict)
