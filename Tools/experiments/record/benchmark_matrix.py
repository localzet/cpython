"""Microbenchmarks for fixed-shape Python data models.

The operations are grouped by semantics; direct constructors are NOT
interchangeable with strict mapping validation or JSON decoding.
"""
from __future__ import annotations

import argparse
import gc
import importlib.metadata
import json
import platform
import statistics
import sys
import timeit
import tracemalloc
from dataclasses import asdict, make_dataclass
from pathlib import Path
from typing import NamedTuple, TypedDict

from record import Record, record


def build_cases(size: int):
    import attrs
    import msgspec
    from pydantic import ConfigDict, create_model

    names = [f"f{i}" for i in range(size)]
    types = {name: int for name in names}
    payload = {name: i for i, name in enumerate(names)}
    data_json = json.dumps(payload, separators=(",", ":")).encode()
    annotations = [(name, int) for name in names]

    dict_type = TypedDict(f"TD{size}", types)
    named_type = NamedTuple(f"Named{size}", annotations)
    dc = make_dataclass(f"DC{size}", annotations, slots=True, kw_only=True)
    ordinary_dc = make_dataclass(f"OrdinaryDC{size}", annotations, kw_only=True)
    rec = record(type(f"Record{size}", (Record,), {
        "__annotations__": types, "__module__": __name__,
    }))

    def strict_int(_instance, attribute, value):
        if type(value) is not int:
            raise TypeError(f"{attribute.name} expected exact int")

    attrs_type = attrs.make_class(
        f"Attrs{size}",
        {name: attrs.field(type=int, validator=strict_int) for name in names},
        slots=True, kw_only=True,
    )
    msg_type = msgspec.defstruct(
        f"Msgspec{size}", annotations, kw_only=True,
        forbid_unknown_fields=True,
    )
    pyd_type = create_model(
        f"Pydantic{size}", __config__=ConfigDict(
            strict=True, extra="forbid",
        ),
        **{name: (int, ...) for name in names},
    )

    def checked_dataclass(data):
        if set(data) != set(types):
            raise TypeError("missing or unexpected fields")
        for value in data.values():
            if type(value) is not int:
                raise TypeError("expected exact int")
        return dc(**data)

    def checked_attrs(data):
        # Constructor-side validators; no coercion or extra fields.
        return attrs_type(**data)

    # Check the normal and invalid paths BEFORE timing.
    validated = {
        "manual/dataclass": checked_dataclass,
        "record": rec.from_mapping,
        "attrs": checked_attrs,
        "msgspec": lambda d: msgspec.convert(d, msg_type, strict=True),
        "pydantic": lambda d: pyd_type.model_validate(d, strict=True),
    }
    for label, construct in validated.items():
        obj = construct(payload)
        if getattr(obj, "f0") != 0:
            raise AssertionError(f"{label} produced the wrong value")
        for bad in ({**payload, "f0": "0"}, {**payload, "extra": 1}):
            try:
                construct(bad)
            except (TypeError, ValueError, msgspec.ValidationError):
                pass
            else:
                raise AssertionError(f"{label} accepted invalid input {bad!r}")

    constructors = {
        "dict": lambda: dict(payload),
        "TypedDict": lambda: dict_type(**payload),
        "NamedTuple": lambda: named_type(**payload),
        "dataclass": lambda: ordinary_dc(**payload),
        "dataclass(slots)": lambda: dc(**payload),
        "record": lambda: rec(**payload),
        "attrs": lambda: attrs_type(**payload),
        "msgspec": lambda: msg_type(**payload),
        "pydantic": lambda: pyd_type(**payload),
    }
    decoders = {
        "dict/parse-only": lambda: json.loads(data_json),
        "manual/dataclass": lambda: checked_dataclass(
            json.loads(data_json)),
        "record": lambda: rec.from_mapping(json.loads(data_json)),
        "attrs": lambda: attrs_type(**json.loads(data_json)),
        "msgspec": lambda: msgspec.json.decode(data_json, type=msg_type),
        "pydantic": lambda: pyd_type.model_validate_json(
            data_json, strict=True),
    }
    objects = {label: make() for label, make in constructors.items()}
    peers = {label: make() for label, make in constructors.items()}
    # All serializers return UTF-8 JSON bytes. Object-to-bytes is measured.
    serializers = {
        "dict": lambda: json.dumps(
            objects["dict"], separators=(",", ":")).encode(),
        "TypedDict": lambda: json.dumps(
            objects["TypedDict"], separators=(",", ":")).encode(),
        "NamedTuple": lambda: json.dumps(
            objects["NamedTuple"]._asdict(), separators=(",", ":")).encode(),
        "dataclass": lambda: json.dumps(
            asdict(objects["dataclass"]), separators=(",", ":")).encode(),
        "dataclass(slots)": lambda: json.dumps(
            asdict(objects["dataclass(slots)"]),
            separators=(",", ":")).encode(),
        "record": lambda: json.dumps(
            objects["record"].to_mapping(),
            separators=(",", ":")).encode(),
        "attrs": lambda: json.dumps(
            attrs.asdict(objects["attrs"]), separators=(",", ":")).encode(),
        "msgspec": lambda: msgspec.json.encode(objects["msgspec"]),
        "pydantic": lambda: objects["pydantic"].model_dump_json().encode(),
    }

    for label, serialize in serializers.items():
        if json.loads(serialize()) != payload:
            raise AssertionError(f"{label}: bad serialized output")
    return {
        "construct": constructors,
        "read_field": {
            label: (lambda obj=obj, label=label:
                    obj["f0"] if label in ("dict", "TypedDict")
                    else obj.f0)
            for label, obj in objects.items()
        },
        "equality": {
            label: (lambda obj=obj, peer=peers[label]: obj == peer)
            for label, obj in objects.items()
        },
        "validated_mapping": {
            label: (lambda make=make: make(payload))
            for label, make in validated.items()
        },
        "json_decode": decoders,
        "json_encode": serializers,
    }, constructors


def measure(callable_, number: int, repeat: int):
    for _ in range(100):
        callable_()
    times = timeit.repeat(
        callable_, number=number, repeat=repeat,
    )
    samples = sorted(t / number * 1_000_000_000 for t in times)
    return {
        "median_ns": round(statistics.median(samples), 1),
        "minimum_ns": round(samples[0], 1),
        "maximum_ns": round(samples[-1], 1),
    }


def memory(factory, instances: int):
    gc.collect()
    tracemalloc.start()
    baseline = tracemalloc.get_traced_memory()[0]
    objects = [factory() for _ in range(instances)]
    allocated = tracemalloc.get_traced_memory()[0] - baseline
    tracemalloc.stop()
    shallow = sys.getsizeof(objects[0])
    count = len(objects)
    del objects
    return {
        "traced_bytes_per_object_approx": round(allocated / count, 1),
        "shallow_getsizeof": shallow,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int,
                        choices=(3, 10, 30), default=[3, 10, 30])
    parser.add_argument("--number", type=int, default=2000)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--instances", type=int, default=1500)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if min(args.number, args.repeat, args.instances) <= 0:
        parser.error("number, repeat and instances must be positive")
    results = []
    memory_results = []
    for size in args.sizes:
        operations, constructors = build_cases(size)
        for group, implementations in operations.items():
            for label, func in implementations.items():
                stats = measure(func, args.number, args.repeat)
                results.append({
                    "size": size, "operation": group,
                    "implementation": label, **stats,
                })
        for label, factory in constructors.items():
            memory_results.append({
                "size": size, "implementation": label,
                **memory(factory, args.instances),
            })

    environment = {
        "python": sys.version, "platform": platform.platform(),
        "implementation": platform.python_implementation(),
        "versions": {},
    }
    for name in ("attrs", "msgspec", "pydantic"):
        environment["versions"][name] = importlib.metadata.version(name)
    output = {
        "environment": environment,
        "parameters": {
            "sizes": args.sizes, "number": args.number,
            "repeat": args.repeat, "instances": args.instances,
        },
        "results": results, "memory": memory_results,
    }
    data = json.dumps(output, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data)
        print(f"Saved {len(results)} measurements to {args.output}")
    else:
        print(data)


if __name__ == "__main__":
    main()
