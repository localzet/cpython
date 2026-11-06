"""Conservative comparison of descriptive metadata, not type assignability.

Even matching metadata is not evidence of equivalent runtime behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .metadata import SchemaMeta

Severity = Literal["difference", "uncertain"]


@dataclass(frozen=True, slots=True)
class Finding:
    code: str
    path: str
    severity: Severity
    explanation: str


@dataclass(frozen=True, slots=True)
class Comparison:
    findings: tuple[Finding, ...]
    verdict: Literal["different", "inconclusive", "metadata_match"]


def compare_metadata(left: SchemaMeta, right: SchemaMeta) -> Comparison:
    """Compare exactly known metadata without assuming type subtyping.

    This does not compare validators, serializer functions, converters,
    nested semantics, or dynamic type checker assignability.
    """
    findings: list[Finding] = []

    def add(code: str, path: str, severity: Severity,
            explanation: str) -> None:
        findings.append(Finding(code, path, severity, explanation))

    left_fields = left.by_name()
    right_fields = right.by_name()
    for name in sorted(set(left_fields) | set(right_fields)):
        if name not in left_fields or name not in right_fields:
            add("field_missing", name, "difference",
                "Field is not present in both schemas")
            continue
        a = left_fields[name]
        b = right_fields[name]
        if a.annotation != b.annotation:
            add("annotation", name, "difference",
                "Different type expressions; no subtype inference attempted")
        if a.input_required != b.input_required:
            add("requiredness", name, "difference",
                "Different requirements for the documented input operation")
        if a.input_names != b.input_names:
            add("input_names", name, "uncertain",
                "Input names belong to provider-specific operations")
        if a.output_name != b.output_name:
            add("output_name", name, "uncertain",
                "Output naming behavior is different or provider-specific")
        if a.default_kind != b.default_kind:
            add("defaults", name, "uncertain",
                "Omitted TypedDict keys are not model defaults")
        elif (left.model is not right.model
              and a.default_kind in ("value", "factory")):
            add("opaque_default", name, "uncertain",
                "Metadata records the default kind, not its actual value")
        if a.static_readonly != b.static_readonly:
            add("static_readonly", name, "uncertain",
                "A readonly guarantee differs or is unknown to one provider")
        if a.assignment_frozen != b.assignment_frozen:
            add("assignment_frozen", name, "uncertain",
                "Runtime assignment constraints differ or are unknown")
        if a.init != b.init:
            add("init", name, "uncertain",
                "Field participation in initialization differs")

    if left.extra_policy != right.extra_policy:
        add("extras", "$", "uncertain",
            "Unknown-key policies differ or are not runtime-equivalent")
    if left.representation != right.representation:
        add("representation", "$", "uncertain",
            "Mapping and object semantics are not interchangeable")
    if left.validation != right.validation:
        add("validation", "$", "uncertain",
            "Annotation metadata does not encode runtime validation rules")
    if (left.frozen is not None and right.frozen is not None
            and left.frozen != right.frozen):
        add("frozen", "$", "uncertain",
            "Runtime freezing differs; it is not TypedDict ReadOnly")

    verdict: Literal["different", "inconclusive", "metadata_match"] = (
        "different" if any(f.severity == "difference" for f in findings)
        else "inconclusive" if findings else "metadata_match")
    return Comparison(tuple(findings), verdict)
