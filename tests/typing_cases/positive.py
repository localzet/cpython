"""Static contract: metadata is descriptive, not a typed dict value."""
from dataclasses import dataclass
from typing import TypedDict, assert_type

from schema_compat.compare import Comparison, compare_metadata
from schema_compat.metadata import (
    MetadataProvider, SchemaMeta, inspect_schema,
)


class Wire(TypedDict):
    id: int


@dataclass
class Model:
    id: int


class Vendor:
    def schema_metadata(self) -> SchemaMeta:
        return inspect_schema(Model)


provider: MetadataProvider = Vendor()
model_schema = inspect_schema(Model)
wire_schema = inspect_schema(Wire)
assert_type(model_schema, SchemaMeta)
assert_type(inspect_schema(provider), SchemaMeta)
assert_type(compare_metadata(model_schema, wire_schema), Comparison)
