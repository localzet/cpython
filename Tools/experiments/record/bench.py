"""Reproducible comparison, not a global performance claim."""
from __future__ import annotations

import argparse
import gc
import json
import platform
import statistics
import sys
import timeit
import tracemalloc
from dataclasses import dataclass
from typing import NamedTuple, TypedDict

from record import record


class UserDict(TypedDict):
    id: int
    name: str
    active: bool


class Plain:
    def __init__(self, id: int, name: str, active: bool = True):
        self.id = id
        self.name = name
        self.active = active


class Slots:
    __slots__ = ("id", "name", "active")

    def __init__(self, id: int, name: str, active: bool = True):
        self.id = id
        self.name = name
        self.active = active


@dataclass
class NormalDC:
    id: int
    name: str
    active: bool = True


@dataclass(slots=True)
class SlotsDC:
    id: int
    name: str
    active: bool = True


class NamedUser(NamedTuple):
    id: int
    name: str
    active: bool = True


@record
class RecordUser:
    id: int
    name: str
    active: bool = True


def checked_manual(data: dict[str, object]) -> SlotsDC:
    if set(data) - {"id", "name", "active"}:
        raise TypeError("unknown fields")
    if "id" not in data or "name" not in data:
        raise TypeError("missing fields")
    if type(data["id"]) is not int or type(data["name"]) is not str:
        raise TypeError("wrong type")
    if "active" in data and type(data["active"]) is not bool:
        raise TypeError("wrong type")
    return SlotsDC(**data)


def bench(label, make, read, number: int, repeats: int, instances: int):
    timeit.Timer(make).timeit(number=2000)
    creation = [
        t / number * 1e9
        for t in timeit.repeat(make, number=number, repeat=repeats)
    ]
    instance = make()
    accesses = [
        t / number * 1e9
        for t in timeit.repeat(
            lambda: read(instance), number=number, repeat=repeats)
    ]
    gc.collect()
    tracemalloc.start()
    baseline = tracemalloc.get_traced_memory()[0]
    objects = [make() for _ in range(instances)]
    used = tracemalloc.get_traced_memory()[0] - baseline
    tracemalloc.stop()
    assert len(objects) == instances
    return {
        "name": label,
        "create_ns_median": round(statistics.median(creation), 1),
        "read_ns_median": round(statistics.median(accesses), 1),
        "instances_traced_bytes_each_approx": round(
            used / instances, 1),
        "shallow_getsizeof": sys.getsizeof(instance),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--number", type=int, default=30000)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--instances", type=int, default=10000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data = {"id": 1, "name": "Ada", "active": True}
    cases = [
        ("dict", lambda: dict(id=1, name="Ada", active=True),
         lambda obj: obj["name"]),
        ("TypedDict (dict runtime)",
         lambda: UserDict(id=1, name="Ada", active=True),
         lambda obj: obj["name"]),
        ("plain class", lambda: Plain(id=1, name="Ada", active=True),
         lambda obj: obj.name),
        ("slotted class", lambda: Slots(id=1, name="Ada", active=True),
         lambda obj: obj.name),
        ("dataclass", lambda: NormalDC(id=1, name="Ada", active=True),
         lambda obj: obj.name),
        ("dataclass(slots=True)",
         lambda: SlotsDC(id=1, name="Ada", active=True),
         lambda obj: obj.name),
        ("NamedTuple", lambda: NamedUser(id=1, name="Ada", active=True),
         lambda obj: obj.name),
        ("record direct", lambda: RecordUser(id=1, name="Ada", active=True),
         lambda obj: obj.name),
        ("record.from_mapping", lambda: RecordUser.from_mapping(data),
         lambda obj: obj.name),
        ("manual validated mapping", lambda: checked_manual(data),
         lambda obj: obj.name),
    ]
    results = [
        bench(label, make, read, args.number, args.repeat, args.instances)
        for label, make, read in cases
    ]
    output = {
        "python": sys.version.split(" (", 1)[0],
        "platform": platform.platform(),
        "number": args.number,
        "repeat": args.repeat,
        "instances": args.instances,
        "results": results,
    }
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"Python {output['python']} on {output['platform']}")
        print("Medians: ns/op. Memory: approximate traced bytes per instance.")
        print(f"{'type':<27} {'create ns':>11} {'read ns':>10} "
              f"{'bytes/obj':>12} {'getsizeof':>11}")
        for r in results:
            print(f"{r['name']:<27} {r['create_ns_median']:>11.1f} "
                  f"{r['read_ns_median']:>10.1f} "
                  f"{r['instances_traced_bytes_each_approx']:>12.1f} "
                  f"{r['shallow_getsizeof']:>11}")


if __name__ == "__main__":
    main()
