"""Simple executable example."""
from record import Record, record


@record
class User(Record):
    id: int
    name: str
    active: bool = True


if __name__ == "__main__":
    user = User.from_mapping({"id": 7, "name": "Ada"})
    print(user)
    print(user.to_mapping())
