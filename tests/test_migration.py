"""Regression tests for directional schema migration risk assessment."""
import json
import subprocess
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from tests.sample_models import (
    AliasV1, AliasV2, ApiV1, ApiV2Breaking, ApiV2Relaxed,
    ObjectV1, ObjectV2,
)
from schema_compat.metadata import inspect_schema
from schema_compat.migration import analyze_migration

ROOT = Path(__file__).resolve().parents[1]


class OldLiteral(TypedDict):
    status: Literal["queued", "running", "done"]


class NewLiteralNarrow(TypedDict):
    status: Literal["queued", "done"]


class NewLiteralWide(TypedDict):
    status: Literal["queued", "running", "done", "failed"]


class OldId(TypedDict):
    id: int


class NewIdString(TypedDict):
    id: str


class OldOptional(TypedDict):
    id: int
    extra: NotRequired[str]


@dataclass
class NewWithoutExtra:
    id: int


@dataclass
class OldOutput:
    id: int
    extra: str


@dataclass
class NewOutput:
    id: int


class Model1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    title: str = Field(validation_alias="titleIn",
                       serialization_alias="titleOut")


class Model2(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    title: str = Field(validation_alias="titleIn",
                       serialization_alias="titleOut")


def report(old: type, new: type, direction: str = "both"):
    return analyze_migration(
        inspect_schema(old), inspect_schema(new), direction=direction)


def codes(result) -> set[str]:
    return {i.code for i in result.issues}


class MigrationTests(unittest.TestCase):
    def test_identical_definition_does_not_claim_proven_compatibility(self):
        r = report(ApiV1, ApiV1)
        self.assertEqual(r.verdict, "no_known_breakage")
        self.assertEqual(len(r.issues), 0)
        self.assertIn("not establish runtime compatibility",
                      r.to_dict()["disclaimer"])

    def test_new_required_field_breaks_existing_input(self):
        r = report(ApiV1, ApiV2Breaking, "input")
        self.assertEqual(r.verdict, "breaking_detected")
        self.assertIn("new_required_field", codes(r))
        self.assertIn("field_now_required", codes(r))

    def test_optional_field_added_is_informational(self):
        r = report(ApiV1, ApiV2Relaxed, "input")
        self.assertIn("new_optional_field", codes(r))
        self.assertNotIn("new_required_field", codes(r))
        self.assertEqual(r.verdict, "review_required")  # opaque runtime

    def test_old_optional_becomes_required(self):
        r = report(ApiV1, ApiV2Breaking, "input")
        self.assertTrue(any(i.code == "field_now_required" and
                            i.path == "display" for i in r.issues))

    def test_reverse_direction_is_not_symmetric(self):
        r = report(ApiV2Breaking, ApiV1, "input")
        self.assertNotIn("new_required_field", codes(r))
        self.assertIn("field_now_optional", codes(r))

    def test_optional_field_removal_with_forbid_extras(self):
        r = report(OldOptional, NewWithoutExtra, "input")
        self.assertIn("removed_input_field", codes(r))
        self.assertEqual(r.verdict, "breaking_detected")

    def test_old_output_field_removed_requires_review(self):
        r = report(OldOutput, NewOutput, "output")
        self.assertIn("output_field_removed", codes(r))
        self.assertNotIn("removed_input_field", codes(r))
        self.assertEqual(r.verdict, "review_required")

    def test_new_output_field_requires_review(self):
        r = report(NewOutput, OldOutput, "output")
        self.assertIn("new_output_field", codes(r))
        self.assertEqual(r.verdict, "review_required")

    def test_alias_input_removed_is_breaking(self):
        r = report(AliasV1, AliasV2, "input")
        self.assertIn("input_name_removed", codes(r))
        self.assertEqual(r.verdict, "breaking_detected")
        self.assertNotIn("output_name_changed", codes(r))

    def test_output_alias_change_breaks_selected_contract(self):
        r = report(AliasV1, AliasV2, "output")
        self.assertIn("output_name_changed", codes(r))
        self.assertNotIn("input_name_removed", codes(r))

    def test_literal_narrower_input_breaks(self):
        r = report(OldLiteral, NewLiteralNarrow, "input")
        self.assertIn("literal_set_contract", codes(r))
        self.assertEqual(r.verdict, "breaking_detected")

    def test_literal_wider_input_is_informational(self):
        r = report(OldLiteral, NewLiteralWide, "input")
        self.assertIn("literal_set_relaxed", codes(r))
        self.assertNotIn("literal_set_contract", codes(r))

    def test_literal_wider_output_is_breaking_for_old_readers(self):
        r = report(OldLiteral, NewLiteralWide, "output")
        self.assertIn("literal_set_contract", codes(r))
        self.assertEqual(r.verdict, "breaking_detected")

    def test_literal_narrower_output_is_informational(self):
        r = report(OldLiteral, NewLiteralNarrow, "output")
        self.assertIn("literal_set_relaxed", codes(r))

    def test_unproven_type_subtyping_not_assumed(self):
        r = report(OldId, NewIdString, "input")
        self.assertIn("annotation_changed", codes(r))
        self.assertNotIn("literal_set_contract", codes(r))
        self.assertEqual(r.verdict, "review_required")

    def test_extra_policy_change_requires_review(self):
        r = report(Model1, Model2, "input")
        self.assertIn("extra_inputs_policy_changed", codes(r))

    def test_default_values_are_opaque(self):
        r = report(ObjectV1, ObjectV2, "input")
        self.assertIn("default_value_opaque", codes(r))
        self.assertEqual(r.verdict, "review_required")

    def test_output_defaults_are_opaque(self):
        r = report(ObjectV1, ObjectV2, "output")
        self.assertIn("output_default_value_opaque", codes(r))

    def test_different_providers_review_not_claiming_equivalence(self):
        r = report(OldId, NewWithoutExtra, "input")
        self.assertIn("provider_changed", codes(r))
        self.assertIn("representation_changed", codes(r))

    def test_direction_filter_only_includes_relevant_findings(self):
        input_r = report(AliasV1, AliasV2, "input")
        out_r = report(AliasV1, AliasV2, "output")
        self.assertNotIn("output_name_changed", codes(input_r))
        self.assertNotIn("input_name_removed", codes(out_r))

    def test_invalid_direction_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported direction"):
            report(ApiV1, ApiV2Breaking, "sideways")

    def test_deterministic_issue_order(self):
        r1 = report(ApiV1, ApiV2Breaking)
        r2 = report(ApiV1, ApiV2Breaking)
        self.assertEqual(r1.issues, r2.issues)
        severities = [i.severity for i in r1.issues]
        self.assertEqual(severities, sorted(
            severities, key={"breaking": 0, "review": 1, "info": 2}.get))

    def test_json_safe_and_versioned(self):
        r = report(ApiV1, ApiV2Breaking)
        data = json.loads(json.dumps(r.to_dict()))
        self.assertEqual(data["format_version"], 1)
        self.assertEqual(data["verdict"], "breaking_detected")
        self.assertGreater(data["counts"]["breaking"], 0)

    def test_class_identifiers_are_stable(self):
        data = report(ApiV1, ApiV2Breaking).to_dict()
        self.assertEqual(data["old"]["model"],
                         "tests.sample_models:ApiV1")
        self.assertEqual(data["new"]["model"],
                         "tests.sample_models:ApiV2Breaking")


class CLITests(unittest.TestCase):
    def cli(self, *arguments: str):
        return subprocess.run(
            [sys.executable, "-m", "schema_compat.cli", *arguments],
            cwd=ROOT, capture_output=True, text=True, check=False)

    def test_json_ci_exit_on_breaking(self):
        r = self.cli("tests.sample_models:ApiV1",
                     "tests.sample_models:ApiV2Breaking",
                     "--direction", "input", "--json", "--fail-on", "breaking")
        self.assertEqual(r.returncode, 1, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data["verdict"], "breaking_detected")

    def test_never_fail_mode(self):
        r = self.cli("tests.sample_models:ApiV1",
                     "tests.sample_models:ApiV2Breaking",
                     "--fail-on", "never")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("breaking_detected", r.stdout)

    def test_review_mode_detects_unknown_runtime(self):
        r = self.cli("tests.sample_models:ObjectV1",
                     "tests.sample_models:ObjectV2",
                     "--fail-on", "review", "--json")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(json.loads(r.stdout)["verdict"], "review_required")

    def test_breaking_only_mode_ignores_review(self):
        r = self.cli("tests.sample_models:ObjectV1",
                     "tests.sample_models:ObjectV2",
                     "--fail-on", "breaking", "--json")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)["verdict"], "review_required")

    def test_same_schema_exits_success(self):
        r = self.cli("tests.sample_models:ApiV1",
                     "tests.sample_models:ApiV1",
                     "--json", "--fail-on", "review")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)["counts"]["breaking"], 0)

    def test_bad_reference_is_not_success(self):
        r = self.cli("not-valid", "tests.sample_models:ApiV1")
        self.assertEqual(r.returncode, 2)
        self.assertIn("Expected import path", r.stderr)

    def test_unknown_class_is_error(self):
        r = self.cli("tests.sample_models:Missing",
                     "tests.sample_models:ApiV1")
        self.assertEqual(r.returncode, 2)
        self.assertIn("Schema loading failed", r.stderr)

    def test_missing_module_is_error(self):
        r = self.cli("no_such_module_xyz:Fake",
                     "tests.sample_models:ApiV1")
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
