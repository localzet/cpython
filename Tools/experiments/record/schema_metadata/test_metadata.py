"""Metadata extraction tests: distinguish known facts from unknown behavior."""
import unittest
from dataclasses import dataclass, field
from typing import Annotated, NotRequired, ReadOnly, Required, TypedDict

import attrs
import msgspec
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from schema_metadata.compare import compare_metadata
from schema_metadata.metadata import (
    FieldMeta, SchemaMeta, UnsupportedSchema, inspect_schema,
)


class Wire(TypedDict):
    id: int
    nickname: NotRequired[str]
    token: ReadOnly[str]
    levels: Annotated[NotRequired[list[int]], "example"]


@dataclass(slots=True)
class Model:
    id: int
    nickname: str = ""
    token: str = "abc"
    levels: list[int] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Frozen:
    id: int


@attrs.define
class AttrModel:
    id: int
    _secret: str = attrs.field(default="none")


@attrs.define
class Validated:
    amount: int = attrs.field(validator=attrs.validators.instance_of(int))


class PydModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    id: int
    display: str = Field(
        default="anonymous", validation_alias="displayIn",
        serialization_alias="displayOut")
    tags: list[str] = Field(default_factory=list)


class PydChoices(BaseModel):
    name: str = Field(validation_alias=AliasChoices("a", "b"))


class PydDefault(BaseModel):
    title: str = "default"


class Msg(msgspec.Struct, rename="camel", forbid_unknown_fields=True):
    id: int
    display_name: str = "anonymous"
    tags: list[int] = msgspec.field(default_factory=list)


class MsgArray(msgspec.Struct, array_like=True):
    x: int


class MsgTagged(msgspec.Struct, tag=True):
    x: int


class CustomProvider:
    def schema_metadata(self) -> SchemaMeta:
        return inspect_schema(Model)


class SchemaMetadataTests(unittest.TestCase):
    def test_typeddict_required_readonly_and_annotated(self):
        schema = inspect_schema(Wire)
        self.assertEqual(schema.provider, "typeddict")
        self.assertEqual(schema.representation, "mapping")
        self.assertEqual(schema.extra_policy, "open")
        fs = schema.by_name()
        self.assertTrue(fs["id"].input_required)
        self.assertFalse(fs["nickname"].input_required)
        self.assertFalse(fs["levels"].input_required)
        self.assertEqual(fs["levels"].annotation, list[int])
        self.assertTrue(fs["token"].static_readonly)
        self.assertFalse(fs["id"].static_readonly)
        self.assertEqual(fs["token"].default_kind, "missing")
        self.assertEqual(fs["nickname"].default_kind, "missing")

    def test_dataclass_required_defaults_factory(self):
        schema = inspect_schema(Model)
        self.assertEqual(schema.provider, "dataclass")
        self.assertEqual(schema.validation, "none")
        fs = schema.by_name()
        self.assertTrue(fs["id"].input_required)
        self.assertEqual(fs["nickname"].default_kind, "value")
        self.assertEqual(fs["levels"].default_kind, "factory")
        self.assertFalse(fs["levels"].input_required)
        self.assertEqual(fs["id"].input_names, ("id",))
        self.assertFalse(fs["id"].assignment_frozen)

    def test_frozen_not_readonly(self):
        schema = inspect_schema(Frozen)
        self.assertTrue(schema.frozen)
        self.assertTrue(schema.by_name()["id"].assignment_frozen)
        self.assertIsNone(schema.by_name()["id"].static_readonly)

    def test_init_false_dataclass_rejected(self):
        @dataclass
        class Invalid:
            id: int
            cached: int = field(default=0, init=False)
        with self.assertRaisesRegex(UnsupportedSchema, "init=False"):
            inspect_schema(Invalid)

    def test_attrs_aliases_are_constructor_names(self):
        schema = inspect_schema(AttrModel)
        self.assertEqual(schema.provider, "attrs")
        fs = schema.by_name()
        self.assertEqual(fs["_secret"].input_names, ("secret",))
        self.assertEqual(fs["_secret"].output_name, "_secret")
        self.assertEqual(fs["_secret"].default_kind, "value")

    def test_attrs_validation_not_encoded(self):
        schema = inspect_schema(Validated)
        self.assertEqual(schema.validation, "configurable")
        self.assertTrue(any("Validators" in note
                            for note in schema.notes))

    def test_attrs_init_false_rejected(self):
        @attrs.define
        class Invalid:
            id: int
            computed: int = attrs.field(init=False, default=0)
        with self.assertRaisesRegex(UnsupportedSchema, "init=False"):
            inspect_schema(Invalid)

    def test_pydantic_directional_aliases(self):
        schema = inspect_schema(PydModel)
        self.assertEqual(schema.provider, "pydantic")
        self.assertEqual(schema.extra_policy, "forbid")
        f = schema.by_name()["display"]
        self.assertEqual(f.input_names, ("displayIn", "display"))
        self.assertEqual(f.output_name, "displayOut")
        self.assertEqual(f.default_kind, "value")
        self.assertFalse(f.input_required)
        self.assertEqual(schema.by_name()["tags"].default_kind, "factory")

    def test_pydantic_default_config(self):
        schema = inspect_schema(PydDefault)
        self.assertEqual(schema.extra_policy, "ignore")

    def test_pydantic_compound_aliases_rejected(self):
        with self.assertRaisesRegex(
            UnsupportedSchema, "compound validation aliases",
        ):
            inspect_schema(PydChoices)

    def test_msgspec_rename_and_factory(self):
        schema = inspect_schema(Msg)
        self.assertEqual(schema.provider, "msgspec")
        self.assertEqual(schema.extra_policy, "forbid")
        self.assertFalse(schema.frozen)
        self.assertEqual(schema.validation, "decode")
        field_info = schema.by_name()["display_name"]
        self.assertEqual(field_info.input_names, ("displayName",))
        self.assertEqual(field_info.output_name, "displayName")
        self.assertEqual(schema.by_name()["tags"].default_kind, "factory")

    def test_msgspec_array_like_rejected(self):
        with self.assertRaisesRegex(UnsupportedSchema, "Array-like"):
            inspect_schema(MsgArray)

    def test_msgspec_tagged_rejected(self):
        with self.assertRaisesRegex(UnsupportedSchema, "tagged"):
            inspect_schema(MsgTagged)

    def test_custom_provider(self):
        self.assertEqual(
            inspect_schema(CustomProvider()).provider, "dataclass")

    def test_provider_must_return_metadata(self):
        class Broken:
            def schema_metadata(self):
                return 42
        with self.assertRaisesRegex(TypeError, "return SchemaMeta"):
            inspect_schema(Broken())

    def test_unknown_provider_rejected(self):
        class Empty:
            pass
        with self.assertRaisesRegex(UnsupportedSchema, "Unknown"):
            inspect_schema(Empty)

    def test_typeddict_postponed_annotations_rejected(self):
        scope = {"TypedDict": TypedDict, "NotRequired": NotRequired}
        exec(
            "from __future__ import annotations\n"
            "class Deferred(TypedDict):\n"
            "    x: int\n"
            "    y: NotRequired[int]\n", scope)
        with self.assertRaisesRegex(UnsupportedSchema, "Deferred"):
            inspect_schema(scope["Deferred"])

    def test_compare_identical_metadata(self):
        left = inspect_schema(Model)
        result = compare_metadata(left, left)
        self.assertEqual(result.verdict, "metadata_match")
        self.assertFalse(result.findings)

    def test_compare_typeddict_dataclass_not_equivalent(self):
        result = compare_metadata(
            inspect_schema(Wire), inspect_schema(Model))
        self.assertEqual(result.verdict, "different")
        codes = {f.code for f in result.findings}
        self.assertIn("requiredness", codes)
        self.assertIn("defaults", codes)
        self.assertIn("representation", codes)
        self.assertIn("extras", codes)

    def test_compare_aliases_inconclusive(self):
        @dataclass
        class AsObject:
            display: str = "anonymous"
        result = compare_metadata(
            inspect_schema(AsObject), inspect_schema(PydModel))
        self.assertEqual(result.verdict, "different")
        self.assertTrue(any(f.code == "input_names"
                            for f in result.findings))

    def test_compare_annotation_mismatch(self):
        @dataclass
        class A:
            x: int
        @dataclass
        class B:
            x: str
        result = compare_metadata(inspect_schema(A), inspect_schema(B))
        self.assertEqual(result.verdict, "different")
        self.assertEqual(result.findings[0].code, "annotation")

    def test_compare_readonly_is_not_frozen(self):
        class ReadOnlyPayload(TypedDict):
            id: ReadOnly[int]
        result = compare_metadata(
            inspect_schema(ReadOnlyPayload), inspect_schema(Frozen))
        self.assertEqual(result.verdict, "inconclusive")
        self.assertTrue(any(f.code == "representation"
                            for f in result.findings))

    def test_no_default_values_or_factories_executed(self):
        calls: list[str] = []
        def factory() -> list[int]:
            calls.append("called")
            return []
        @dataclass
        class ModelFactory:
            data: list[int] = field(default_factory=factory)
        meta = inspect_schema(ModelFactory)
        self.assertEqual(meta.by_name()["data"].default_kind, "factory")
        self.assertFalse(calls)

    def test_field_metadata_is_not_json_schema(self):
        schema = inspect_schema(Model)
        self.assertIs(schema.model, Model)
        self.assertEqual(schema.by_name()["levels"].annotation, list[int])

    def test_duplicate_provider_fields_rejected(self):
        class Broken:
            def schema_metadata(self):
                field = FieldMeta("same", int, ("same",), "same", True,
                                  "missing")
                return SchemaMeta(
                    "custom", Model, "object", (field, field), "unknown",
                    None, "unknown")
        with self.assertRaisesRegex(UnsupportedSchema, "Duplicate"):
            inspect_schema(Broken())


if __name__ == "__main__":
    unittest.main()
