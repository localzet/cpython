"""Behavioral checks for the record prototype."""
from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError, field, fields, is_dataclass
from typing import Literal

from record import Record, RecordValidationError, record


@record
class User(Record):
    id: int
    name: str
    tags: list[str]
    active: bool = True


@record(frozen=True)
class FrozenUser(Record):
    id: int
    name: str


@record
class WithFactory(Record):
    id: int
    tags: list[str] = field(default_factory=list)


@record
class Policy(Record):
    scopes: dict[str, list[int | None]]
    status: Literal["open", "closed"] = "open"


class RecordTests(unittest.TestCase):
    def test_mapping_and_defaults(self):
        user = User.from_mapping({"id": 1, "name": "Ada", "tags": ["dev"]})
        self.assertTrue(is_dataclass(user))
        self.assertEqual([f.name for f in fields(user)],
                         ["id", "name", "tags", "active"])
        self.assertTrue(user.active)
        self.assertEqual(user.to_mapping(), {
            "id": 1, "name": "Ada", "tags": ["dev"], "active": True,
        })

    def test_identity_and_shallow_mapping(self):
        tags = ["dev"]
        user = User.from_mapping({"id": 1, "name": "Ada", "tags": tags})
        output = user.to_mapping()
        self.assertIs(output["tags"], tags)
        self.assertIsNot(output, user.to_mapping())

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

    def test_non_string_key(self):
        with self.assertRaisesRegex(RecordValidationError, "unknown fields"):
            User.from_mapping({
                "id": 1, "name": "Ada", "tags": [], 2: "unexpected",
            })

    def test_invalid_scalar(self):
        for value in ("1", True):
            with self.subTest(value=value):
                with self.assertRaisesRegex(RecordValidationError, "User.id"):
                    User.from_mapping({
                        "id": value, "name": "Ada", "tags": [],
                    })

    def test_invalid_collection_path(self):
        with self.assertRaisesRegex(
            RecordValidationError, r"User\.tags\[1\]",
        ):
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

    def test_default_factory_is_independent(self):
        one = WithFactory.from_mapping({"id": 1})
        two = WithFactory.from_mapping({"id": 2})
        one.tags.append("first")
        self.assertEqual(two.tags, [])

    def test_nested_generic_union(self):
        value = Policy.from_mapping({
            "scopes": {"member": [1, None]},
        })
        self.assertEqual(value.status, "open")
        with self.assertRaisesRegex(
            RecordValidationError, r"Policy\.scopes\['member'\]\[0\]",
        ):
            Policy.from_mapping({"scopes": {"member": [True]}})

    def test_literal(self):
        with self.assertRaisesRegex(RecordValidationError, "Policy.status"):
            Policy.from_mapping({
                "scopes": {}, "status": "missing",
            })

    def test_unknown_type_not_silently_accepted(self):
        @record
        class Weird(Record):
            identifier: list[set[str]]

        with self.assertRaisesRegex(TypeError, "Unsupported annotation"):
            Weird.from_mapping({"identifier": [{"a"}]})

    def test_tuple_validation(self):
        @record
        class Pair(Record):
            values: tuple[int, str]

        obj = Pair.from_mapping({"values": (1, "ok")})
        self.assertEqual(obj.values, (1, "ok"))
        with self.assertRaisesRegex(
            RecordValidationError, r"Pair\.values\[1\]",
        ):
            Pair.from_mapping({"values": (1, 5)})

    def test_inherited_fields(self):
        @record
        class Extended(User):
            level: int = 1

        obj = Extended.from_mapping({
            "id": 1, "name": "Ada", "tags": [],
        })
        self.assertEqual(obj.level, 1)
        self.assertFalse(hasattr(obj, "__dict__"))

    def test_requires_record_base(self):
        with self.assertRaisesRegex(TypeError, "must inherit Record"):
            @record
            class Invalid:
                id: int

    def test_reserved_fields(self):
        with self.assertRaisesRegex(TypeError, "Reserved"):
            @record
            class Invalid(Record):
                from_mapping: int

    def test_pattern_match(self):
        user = User(id=1, name="Ada", tags=[])
        match user:
            case User(id=1, name="Ada"):
                found = True
            case _:
                found = False
        self.assertTrue(found)


if __name__ == "__main__":
    unittest.main()
