"""TypedDict is a transport shape; dataclass is an internal object."""
from dataclasses import dataclass
from typing import NotRequired, TypedDict

from bridge.schema_bridge import SchemaBridge


class UserPayload(TypedDict):
    id: int
    nickname: NotRequired[str]


@dataclass(slots=True)
class User:
    id: int
    nickname: str = ""


if __name__ == "__main__":
    bridge = SchemaBridge(User, UserPayload)
    user = bridge.from_mapping({"id": 42})
    assert isinstance(user, User)
    assert bridge.to_mapping(user) == {"id": 42, "nickname": ""}
    print(user)
    print(bridge.to_json(user))
