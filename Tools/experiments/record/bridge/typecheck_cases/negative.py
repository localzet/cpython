"""Each # E line must be reported independently by mypy and Pyright."""
from dataclasses import dataclass
from typing import TypedDict

from bridge.schema_bridge import SchemaBridge


class Wire(TypedDict):
    id: int


@dataclass
class User:
    id: int


bridge = SchemaBridge(User, Wire)
bridge.from_mapping([1, 2])  # E: nonmapping input
bridge.to_mapping("not user")  # E: model type mismatch
bridge.from_json(42)  # E: bad JSON input type
payload: Wire = bridge.to_mapping(User(1))  # E: cannot promise TypedDict output
