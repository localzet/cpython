"""Static typing checks expected to pass in both mypy and Pyright."""
from __future__ import annotations

from dataclasses import field
from typing import assert_type

from record import Record, record


@record
class User(Record):
    id: int
    name: str
    tags: list[str] = field(default_factory=list)


@record(frozen=True)
class FrozenUser(Record):
    id: int
    name: str


user: User = User(id=1, name="Ada")
assert_type(user.id, int)
assert_type(user.name, str)
assert_type(user.tags, list[str])
assert_type(User.from_mapping({"id": 1, "name": "Ada"}), User)
assert_type(user.to_mapping(), dict[str, object])
assert_type(FrozenUser.from_mapping({"id": 1, "name": "Ada"}), FrozenUser)
