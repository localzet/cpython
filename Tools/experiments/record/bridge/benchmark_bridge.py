"""Benchmark a TypedDict/dataclass boundary using comparable operations.

All variants are run on required integer fields. The result captures raw
measurements and environment versions; it is not a global performance claim.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import statistics
import sys
import timeit
from dataclasses import asdict, make_dataclass
from pathlib import Path
from typing import TypedDict

from bridge.schema_bridge import SchemaBridge


def cases(width: int):
    import msgspec
    from pydantic import ConfigDict, create_model

    annotations = {f"f{i}": int for i in range(width)}
    payload_type = TypedDict(f"Payload{width}", annotations)
    model_type = make_dataclass(
        f"Model{width}", [(k, v) for k, v in annotations.items()],
        slots=True, kw_only=True)
    bridge = SchemaBridge(model_type, payload_type)
    payload = {name: index for index, name in enumerate(annotations)}
    encoded = json.dumps(payload, separators=(",", ":"))
    msg_type = msgspec.defstruct(
        f"Msg{width}", [(k, int) for k in annotations],
        kw_only=True, forbid_unknown_fields=True)
    pyd_type = create_model(
        f"Pyd{width}", __config__=ConfigDict(strict=True, extra="forbid"),
        **{name: (int, ...) for name in annotations})
    keys = frozenset(annotations)

    def manual_decode(data):
        if set(data) != keys or any(type(v) is not int for v in data.values()):
            raise TypeError("invalid mapping")
        return model_type(**data)

    def manual_encode(obj):
        return {name: getattr(obj, name) for name in annotations}

    decoders = {
        "manual/dataclass": lambda: manual_decode(payload),
        "bridge/dataclass": lambda: bridge.from_mapping(payload),
        "msgspec/struct": lambda: msgspec.convert(
            payload, msg_type, strict=True),
        "pydantic/model": lambda: pyd_type.model_validate(
            payload, strict=True),
    }
    for name, fun in decoders.items():
        obj = fun()
        if getattr(obj, "f0") != 0:
            raise AssertionError(f"{name}: unexpected decoded value")

    # Verify common rejection behavior before comparing timings.
    bad = {**payload, "f0": "not-an-int"}
    bad_extra = {**payload, "unexpected": 1}
    validations = {
        "manual/dataclass": manual_decode,
        "bridge/dataclass": bridge.from_mapping,
        "msgspec/struct": lambda d: msgspec.convert(
            d, msg_type, strict=True),
        "pydantic/model": lambda d: pyd_type.model_validate(
            d, strict=True),
    }
    for name, validation in validations.items():
        for value in (bad, bad_extra):
            try:
                validation(value)
            except (TypeError, ValueError, msgspec.ValidationError):
                continue
            raise AssertionError(f"{name}: invalid data accepted")

    model = model_type(**payload)
    msg_obj = msg_type(**payload)
    pyd_obj = pyd_type(**payload)
    mappings = {
        "manual/dataclass": lambda: manual_encode(model),
        "bridge/dataclass": lambda: bridge.to_mapping(model),
        "dataclasses.asdict": lambda: asdict(model),
        "msgspec/struct": lambda: msgspec.to_builtins(msg_obj),
        "pydantic/model": lambda: pyd_obj.model_dump(),
    }
    for name, fun in mappings.items():
        if fun() != payload:
            raise AssertionError(f"{name}: mapping differs")

    from_json = {
        "manual/dataclass": lambda: manual_decode(json.loads(encoded)),
        "bridge/dataclass": lambda: bridge.from_json(encoded),
        "msgspec/struct": lambda: msgspec.json.decode(
            encoded, type=msg_type),
        "pydantic/model": lambda: pyd_type.model_validate_json(
            encoded, strict=True),
    }
    to_json = {
        "manual/dataclass": lambda: json.dumps(manual_encode(model)),
        "bridge/dataclass": lambda: bridge.to_json(model),
        "msgspec/struct": lambda: msgspec.json.encode(msg_obj),
        "pydantic/model": lambda: pyd_obj.model_dump_json(),
    }
    for name, fun in to_json.items():
        if json.loads(fun()) != payload:
            raise AssertionError(f"{name}: JSON differs")

    return {
        "validate_mapping": decoders,
        "encode_mapping": mappings,
        "decode_json": from_json,
        "encode_json": to_json,
        "compile_adapter": {
            "bridge/dataclass": lambda: SchemaBridge(
                model_type, payload_type),
        },
    }


def measure(func, *, number: int, repeat: int) -> dict[str, object]:
    for _ in range(150):
        func()
    samples = timeit.repeat(func, number=number, repeat=repeat)
    ns = [round(sample * 1e9 / number, 2) for sample in samples]
    return {"median_ns": statistics.median(ns), "samples_ns": ns}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", type=int, nargs="+",
                        choices=(3, 10, 30), default=[3, 10, 30])
    parser.add_argument("--number", type=int, default=3000)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.number < 1 or args.repeat < 1:
        parser.error("number and repeat must be positive")

    results = []
    for width in args.sizes:
        for op, implementations in cases(width).items():
            for name, func in implementations.items():
                results.append({
                    "width": width, "operation": op,
                    "implementation": name,
                    **measure(func, number=args.number, repeat=args.repeat),
                })
    output = {
        "python": sys.version,
        "platform": platform.platform(),
        "libraries": {
            name: importlib.metadata.version(name)
            for name in ("msgspec", "pydantic")
        },
        "parameters": {
            "sizes": args.sizes, "number": args.number,
            "repeat": args.repeat,
        },
        "results": results,
    }
    text = json.dumps(output, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
        print(f"Saved {len(results)} measurements to {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
