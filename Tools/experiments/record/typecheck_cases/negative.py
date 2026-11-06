"""Every marked operation must be rejected by both type checkers."""
from record import Record, record


@record
class User(Record):
    id: int
    name: str


@record(frozen=True)
class FrozenUser(Record):
    id: int
    name: str


u = User(id=1, name="Ada")
User(id="not an int", name="Ada")  # E: invalid field type
User(1, "Ada")  # E: positional arguments
u.missing = 5  # E: unknown attribute
f = FrozenUser(id=1, name="Ada")
f.name = "Grace"  # E: frozen field
