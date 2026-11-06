"""Behavioral contract: conversions are explicit, strict, and canonical."""
import unittest
from dataclasses import dataclass, field
from typing import Any, Literal, NotRequired, ReadOnly, Required, TypedDict

from bridge.schema_bridge import SchemaBridge, SchemaError, ValidationError


class AddressData(TypedDict):
    city: str
    postcode: NotRequired[str]


@dataclass(slots=True)
class Address:
    city: str
    postcode: str = ""


class UserData(TypedDict):
    id: int
    name: str
    address: AddressData
    friends: list[AddressData]
    labels: dict[str, AddressData]
    status: NotRequired[Literal["active", "inactive"]]
    parent: NotRequired[AddressData | None]


@dataclass(slots=True)
class User:
    id: int
    name: str
    address: Address
    friends: list[Address]
    labels: dict[str, Address]
    status: Literal["active", "inactive"] = "active"
    parent: Address | None = None


class Basic(TypedDict):
    id: int
    tags: NotRequired[list[int]]


@dataclass(slots=True)
class BasicModel:
    id: int
    tags: list[int] = field(default_factory=list)


class FrozenData(TypedDict):
    id: ReadOnly[int]


@dataclass(frozen=True, slots=True)
class FrozenModel:
    id: int


class InheritedBase(TypedDict, total=False):
    nickname: str


class Inherited(InheritedBase):
    id: Required[int]


@dataclass(slots=True)
class InheritedModel:
    id: int
    nickname: str = ""


class AnyData(TypedDict):
    payload: Any


@dataclass
class AnyModel:
    payload: Any


class NodeData(TypedDict):
    id: int
    child: NotRequired["NodeData | None"]


@dataclass(slots=True)
class NodeModel:
    id: int
    child: "NodeModel | None" = None


PAYLOAD = {
    "id": 7,
    "name": "Ada",
    "address": {"city": "London"},
    "friends": [{"city": "Paris", "postcode": "75001"}],
    "labels": {"home": {"city": "Berlin"}},
}


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.bridge = SchemaBridge(User, UserData)

    def test_dataclass_and_payload_roundtrip(self):
        model = self.bridge.from_mapping(PAYLOAD)
        self.assertIsInstance(model, User)
        self.assertIsInstance(model.address, Address)
        self.assertIsInstance(model.friends[0], Address)
        self.assertIsInstance(model.labels["home"], Address)
        self.assertEqual(model.status, "active")
        self.assertIsNone(model.parent)
        out = self.bridge.to_mapping(model)
        self.assertEqual(out["address"], {"city": "London", "postcode": ""})
        self.assertEqual(out["status"], "active")
        self.assertIn("parent", out)
        # Optional key presence is lost when the default is materialized.
        self.assertNotEqual(out, PAYLOAD)
        self.assertEqual(self.bridge.from_mapping(out), model)

    def test_json_roundtrip(self):
        model = self.bridge.from_json(
            '{"id":7,"name":"Ada","address":{"city":"London"},'
            '"friends":[],"labels":{}}')
        self.assertEqual(model.address.city, "London")
        self.assertEqual(self.bridge.from_json(self.bridge.to_json(model)), model)

    def test_missing_required(self):
        with self.assertRaisesRegex(ValidationError, "missing keys .*name"):
            self.bridge.from_mapping({"id": 1})

    def test_missing_nested_required(self):
        with self.assertRaisesRegex(
            ValidationError, r"User\.address: missing keys .*city",
        ):
            self.bridge.from_mapping({**PAYLOAD, "address": {}})

    def test_unknown_root_rejected(self):
        with self.assertRaisesRegex(ValidationError, "unexpected keys .*extra"):
            self.bridge.from_mapping({**PAYLOAD, "extra": "ok"})

    def test_unknown_nested_rejected(self):
        with self.assertRaisesRegex(
            ValidationError, r"User\.address: unexpected keys",
        ):
            self.bridge.from_mapping({
                **PAYLOAD, "address": {"city": "London", "extra": 4},
            })

    def test_ignore_extras_explicitly(self):
        bridge = SchemaBridge(User, UserData, extra="ignore")
        obj = bridge.from_mapping({
            **PAYLOAD, "extra": "ok",
            "address": {"city": "London", "extra": 4},
        })
        self.assertEqual(obj.address.city, "London")
        self.assertNotIn("extra", bridge.to_mapping(obj))

    def test_unknown_policy(self):
        with self.assertRaisesRegex(ValueError, "Unknown extra-field"):
            SchemaBridge(User, UserData, extra="coerce")

    def test_int_rejects_bool(self):
        with self.assertRaisesRegex(ValidationError, "User.id"):
            self.bridge.from_mapping({**PAYLOAD, "id": True})

    def test_int_rejects_string(self):
        with self.assertRaisesRegex(ValidationError, "User.id"):
            self.bridge.from_mapping({**PAYLOAD, "id": "7"})

    def test_nested_list_path(self):
        with self.assertRaisesRegex(
            ValidationError, r"User\.friends\[0\]\.city",
        ):
            self.bridge.from_mapping({
                **PAYLOAD, "friends": [{"city": 42}],
            })

    def test_nested_mapping_path(self):
        with self.assertRaisesRegex(
            ValidationError, r"User\.labels\['home'\]\.city",
        ):
            self.bridge.from_mapping({
                **PAYLOAD, "labels": {"home": {"city": 42}},
            })

    def test_non_string_mapping_key(self):
        with self.assertRaisesRegex(
            ValidationError, "mapping keys must be strings",
        ):
            self.bridge.from_mapping({**PAYLOAD, 42: "wrong"})

    def test_non_string_nested_key(self):
        with self.assertRaisesRegex(ValidationError, "<key>"):
            self.bridge.from_mapping({
                **PAYLOAD, "labels": {42: {"city": "London"}},
            })

    def test_wrong_literal(self):
        with self.assertRaisesRegex(ValidationError, "User.status"):
            self.bridge.from_mapping({**PAYLOAD, "status": "offline"})

    def test_nullable_nested(self):
        self.assertIsNone(
            self.bridge.from_mapping({**PAYLOAD, "parent": None}).parent)
        model = self.bridge.from_mapping({
            **PAYLOAD, "parent": {"city": "Rome"},
        })
        self.assertEqual(model.parent.city, "Rome")

    def test_nullable_not_an_integer(self):
        with self.assertRaisesRegex(ValidationError, "User.parent"):
            self.bridge.from_mapping({**PAYLOAD, "parent": 6})

    def test_output_validation(self):
        obj = self.bridge.from_mapping(PAYLOAD)
        obj.id = "unvalidated assignment"
        with self.assertRaisesRegex(ValidationError, "User.id"):
            self.bridge.to_mapping(obj)

    def test_output_wrong_instance(self):
        with self.assertRaisesRegex(ValidationError, "User"):
            self.bridge.to_mapping("not a model")

    def test_output_does_not_alias_mutable_list(self):
        model = self.bridge.from_mapping(PAYLOAD)
        raw = self.bridge.to_mapping(model)
        self.assertIsNot(raw["friends"], model.friends)
        self.assertIsNot(raw["friends"][0], model.friends[0])

    def test_default_factory_is_independent(self):
        bridge = SchemaBridge(BasicModel, Basic)
        first = bridge.from_mapping({"id": 1})
        second = bridge.from_mapping({"id": 2})
        first.tags.append(4)
        self.assertEqual(second.tags, [])

    def test_inherited_typeddict_total(self):
        bridge = SchemaBridge(InheritedModel, Inherited)
        self.assertEqual(bridge.from_mapping({"id": 1}).nickname, "")

    def test_readonly_is_not_runtime_frozen(self):
        bridge = SchemaBridge(FrozenModel, FrozenData)
        self.assertEqual(
            bridge.to_mapping(bridge.from_mapping({"id": 1})), {"id": 1})

    def test_any_is_pass_through(self):
        thing = object()
        bridge = SchemaBridge(AnyModel, AnyData)
        self.assertIs(bridge.from_mapping({"payload": thing}).payload, thing)
        self.assertIs(bridge.to_mapping(AnyModel(thing))["payload"], thing)

    def test_does_not_accept_non_dataclass(self):
        with self.assertRaisesRegex(SchemaError, "dataclass"):
            SchemaBridge(dict, Basic)

    def test_does_not_accept_non_typeddict(self):
        with self.assertRaisesRegex(SchemaError, "TypedDict"):
            SchemaBridge(BasicModel, dict)

    def test_missing_default_on_optional_field_rejected(self):
        @dataclass
        class Bad:
            id: int
            tags: list[int]
        with self.assertRaisesRegex(SchemaError, "no dataclass default"):
            SchemaBridge(Bad, Basic)

    def test_field_name_mismatch_rejected(self):
        @dataclass
        class Bad:
            id: int
        with self.assertRaisesRegex(SchemaError, "Field names differ"):
            SchemaBridge(Bad, Basic)

    def test_field_type_mismatch_rejected(self):
        @dataclass
        class Bad:
            id: str
            tags: list[int] = field(default_factory=list)
        with self.assertRaisesRegex(SchemaError, "mismatched annotation"):
            SchemaBridge(Bad, Basic)

    def test_init_false_fields_rejected(self):
        @dataclass
        class Bad:
            id: int
            tags: list[int] = field(init=False, default_factory=list)
        with self.assertRaisesRegex(SchemaError, "init=False"):
            SchemaBridge(Bad, Basic)

    def test_unsupported_tuple_rejected(self):
        class PairPayload(TypedDict):
            pair: tuple[int, str]
        @dataclass
        class PairModel:
            pair: tuple[int, str]
        with self.assertRaisesRegex(SchemaError, "Unsupported"):
            SchemaBridge(PairModel, PairPayload)

    def test_postponed_requiredness_is_rejected(self):
        exec(
            "from __future__ import annotations\n"
            "class DeferredPayload(TypedDict):\n"
            "    id: int\n"
            "    tags: NotRequired[list[int]]\n",
            globals(),
        )
        with self.assertRaisesRegex(SchemaError, "Unreliable TypedDict"):
            SchemaBridge(BasicModel, globals()["DeferredPayload"])

    def test_recursive_model_is_rejected_explicitly(self):
        with self.assertRaisesRegex(SchemaError, "Recursive model"):
            SchemaBridge(NodeModel, NodeData)

    def test_invalid_top_level_json(self):
        with self.assertRaisesRegex(ValidationError, "expected 'mapping'"):
            self.bridge.from_json("[1,2,3]")


if __name__ == "__main__":
    unittest.main()
