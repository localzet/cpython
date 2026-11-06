"""Declared value-set relationships (not runtime validator compatibility)."""
import unittest
from typing import Annotated, Any, Literal
from schema_compat.type_relations import TypeEvidence, assess_subset


class TypeRelationTests(unittest.TestCase):
    def test_same_scalar(self):
        self.assertEqual(assess_subset(str, str), TypeEvidence("included"))

    def test_nullable_widening(self):
        self.assertEqual(assess_subset(str, str | None).relation, "included")

    def test_nullable_narrowing(self):
        self.assertEqual(assess_subset(str | None, str).witness, "None")

    def test_fastapi_field_narrowing(self):
        t = Literal["array", "boolean", "integer", "null", "number", "object", "string"]
        self.assertEqual(assess_subset(str | None, t | list[t] | None).relation,
                         "excluded")
        self.assertEqual(assess_subset(t | list[t] | None, str | None).relation,
                         "excluded")

    def test_literal_widening(self):
        self.assertEqual(
            assess_subset(Literal["a"], Literal["a", "b"]).relation,
            "included")

    def test_literal_bool_int_distinct(self):
        self.assertEqual(assess_subset(Literal[1, True], Literal[1]).witness,
                         "True")

    def test_nonempty_list_witness(self):
        self.assertEqual(assess_subset(list[int], list[str]).relation,
                         "excluded")

    def test_nested_dict_narrowing(self):
        self.assertEqual(
            assess_subset(dict[str, int], dict[str, Literal[1]]).relation,
            "excluded")

    def test_nested_dict_widening(self):
        self.assertEqual(
            assess_subset(dict[str, Literal[1]], dict[str, int]).relation,
            "included")

    def test_list_literal_widening(self):
        self.assertEqual(
            assess_subset(list[Literal["a"]], list[str]).relation,
            "included")

    def test_homogeneous_tuple(self):
        self.assertEqual(
            assess_subset(tuple[int, ...], tuple[str, ...]).relation,
            "excluded")

    def test_none_exhaustive(self):
        self.assertEqual(
            assess_subset(type(None), str | None).relation, "included")

    def test_any_is_unknown(self):
        self.assertEqual(assess_subset(Any, int).relation, "unknown")

    def test_opaque_generic_is_unknown(self):
        self.assertEqual(assess_subset(set[int], set[str]).relation, "unknown")

    def test_annotated_is_unknown(self):
        self.assertEqual(
            assess_subset(Annotated[int, "x"], int).relation, "unknown")

    def test_supported_generic_in_union(self):
        self.assertEqual(
            assess_subset(list[int], list[int] | dict[str, int]).relation,
            "included")

    def test_unknown_class(self):
        class Old: pass
        class New: pass
        self.assertEqual(assess_subset(Old, New).relation, "unknown")

    def test_deterministic_synthetic_witness(self):
        a = assess_subset(dict[str, int], dict[str, Literal[1]])
        b = assess_subset(dict[str, int], dict[str, Literal[1]])
        self.assertEqual(a, b)
