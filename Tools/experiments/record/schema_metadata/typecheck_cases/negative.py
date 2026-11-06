"""The following expressions must be rejected by both analyzers."""
from dataclasses import dataclass
from typing import TypedDict

from schema_metadata.metadata import SchemaMeta, inspect_schema


class Wire(TypedDict):
    id: int


@dataclass
class Model:
    id: int


meta: SchemaMeta = inspect_schema(Model)
not_a_mapping: dict[str, object] = meta  # E: metadata is not mapping
not_a_typed_dict: Wire = inspect_schema(Wire)  # E: metadata is not instance
inspect_schema(42)  # E: unrecognized provider
