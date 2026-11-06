"""Behavioral checks for the experimental record decorator."""
from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError, fields, is_dataclass
from record import RecordValidationError, record


@record
class User:
    id: int
    name: str
    tags: list[str]
    active: bool = True


@record(frozen=True)
class FrozenUser:
    id: int
    name: str


class RecordTests(unittest.TestCase):
    def test_from_mapping_and_defaults(self):
        user = User.from_mapping({"id": 1, "name": "Ada", "tags": ["dev"]})
        self.assertTrue(is_dataclass(user))
        self.assertEqual([f.name for f in fields(user)],
                         ["id", "name", "tags", "active"])
        self.assertEqual(user.active, True)
        self.assertEqual(user.to_mapping(), {
            "id": 1, "name": "Ada", "tags": ["dev"], "active": True,
        })

    def test_closed_shape(self):
        user = User(id=1, name="Ada", tags=[])
        self.assertFalse(hasattr(user, "__dict__"))
        with self.assertRaises(AttributeError):
            user.other = 12

    def test_frozen(self):
        user = FrozenUser.from_mapping({"id": 1, "name": "Ada"})
        with self.assertRaises(FrozenInstanceError):
            user.name = "Grace"

    def test_keyword_only(self):
        with self.assertRaises(TypeError):
            User(1, "Ada", [])

    def test_missing(self):
        with self.assertRaisesRegex(RecordValidationError, "missing fields"):
            User.from_mapping({"id": 1, "name": "Ada"})

    def test_unknown(self):
        with self.assertRaisesRegex(RecordValidationError, "unknown fields"):
            User.from_mapping({
                "id": 1, "name": "Ada", "tags": [], "age": 20,
            })

    def test_unknown_non_string_key(self):
        with self.assertRaisesRegex(RecordValidationError, "unknown fields"):
            User.from_mapping({
                "id": 1, "name": "Ada", "tags": [], 2: "unexpected",
            })

    def test_invalid_scalar(self):
        for value in ("1", True):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    RecordValidationError, "User.id",
                ):
                    User.from_mapping({
                        "id": value, "name": "Ada", "tags": [],
                    })

    def test_invalid_collection(self):
        with self.assertRaisesRegex(RecordValidationError, "User.tags"):
            User.from_mapping({
                "id": 1, "name": "Ada", "tags": ["dev", 2],
            })

    def test_invalid_mapping_arg(self):
        with self.assertRaisesRegex(
            RecordValidationError, "expected a mapping",
        ):
            User.from_mapping([])

    def test_constructor_is_not_checked(self):
        user = User(id="wrong", name=123, tags=[])
        self.assertEqual(user.id, "wrong")

    def test_reserved_field(self):
        with self.assertRaisesRegex(TypeError, "Reserved"):
            @record
            class Invalid:
                from_mapping: int

    def test_nested_generic_union(self):
        @record
        class Config:
            scopes: dict[str, list[int | None]]
            status: str | None = None
        self.assertIsNone(
            Config.from_mapping({"scopes": {"a": [1, None]}}).status)
        with self.assertRaisesRegex(RecordValidationError, "Config.scopes"):
            Config.from_mapping({"scopes": {"a": [True]}})

    def test_unsupported_annotations_are_not_silently_accepted(self):
        @record
        class Weird:
            identifier: complex | list[set[str]]
        with self.assertRaisesRegex(TypeError, "Unsupported annotation"):
            Weird.from_mapping({"identifier": [{"a"}]})


if __name__ == "__main__":
    unittest.main()
