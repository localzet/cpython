"""Minimal real-history field reconstructions with runtime witnesses."""
import unittest
from pydantic import ValidationError
from schema_compat import analyze_migration, inspect_schema
from tests.realworld_models import (
    ChatCompletionNew, ChatCompletionOld, FastAPISchemaNew, FastAPISchemaOld,
    StrictNew, StrictOld,
)

def report(old, new, direction):
    return analyze_migration(inspect_schema(old), inspect_schema(new),
                             direction=direction)

class RealWorldChangeTests(unittest.TestCase):
    def test_fastapi_annotation_change_requires_review(self):
        result = report(FastAPISchemaOld, FastAPISchemaNew, "input")
        self.assertEqual(result.verdict, "review_required")
        self.assertIn("annotation_changed", {i.code for i in result.issues})

    def test_fastapi_narrowing_witness_not_detected_as_definite(self):
        sample = {"type": "custom-extension"}
        self.assertEqual(FastAPISchemaOld.model_validate(sample).type,
                         "custom-extension")
        with self.assertRaises(ValidationError):
            FastAPISchemaNew.model_validate(sample)
        new_only = {"type": ["string", "null"]}
        self.assertEqual(FastAPISchemaNew.model_validate(new_only).type,
                         ["string", "null"])
        with self.assertRaises(ValidationError):
            FastAPISchemaOld.model_validate(new_only)
        self.assertNotEqual(
            report(FastAPISchemaOld, FastAPISchemaNew, "input").verdict,
            "breaking_detected")

    def test_openai_optional_response_field_requires_review(self):
        result = report(ChatCompletionOld, ChatCompletionNew, "output")
        self.assertEqual(result.verdict, "review_required")
        self.assertIn("new_output_field", {i.code for i in result.issues})

    def test_openai_minimal_default_pydantic_reader_accepts_output(self):
        new_obj = ChatCompletionNew(
            id="chatcmpl-example", object="chat.completion",
            metadata={"request_id": "example"})
        parsed = ChatCompletionOld.model_validate(new_obj.model_dump())
        self.assertEqual(parsed.id, new_obj.id)
        self.assertFalse(hasattr(parsed, "metadata"))

    def test_synthetic_required_field_control_is_detected(self):
        result = report(StrictOld, StrictNew, "input")
        self.assertEqual(result.verdict, "breaking_detected")
        self.assertIn("new_required_field", {i.code for i in result.issues})
        sample = {"id": 1}
        self.assertEqual(StrictOld.model_validate(sample).id, 1)
        with self.assertRaises(ValidationError):
            StrictNew.model_validate(sample)
