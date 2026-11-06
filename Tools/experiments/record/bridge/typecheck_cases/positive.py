"""Both type checkers must accept the statically expressible boundary API."""
from dataclasses import dataclass
from typing import NotRequired, TypedDict, assert_type

from bridge.schema_bridge import SchemaBridge


class UserWire(TypedDict):
    id: int
    nickname: NotRequired[str]


@dataclass(slots=True)
class User:
    id: int
    nickname: str = ""


bridge: SchemaBridge[User] = SchemaBridge(User, UserWire)
wire: UserWire = {"id": 1}
value = bridge.from_mapping(wire)
assert_type(value, User)
assert_type(bridge.to_mapping(value), dict[str, object])
assert_type(bridge.from_json('{"id":1}'), User)
assert_type(bridge.to_json(value), str)
