# Benchmark methodology

This experiment compares **different operations separately** for schemas
with 3, 10 and 30 required integer fields. The values are deterministic.
Each validated-mapping implementation is checked to reject strings for int
fields and to reject unknown fields.

Operations:
- validate_mapping: strict mapping input -> model
- encode_mapping: already-built model -> mapping
- decode_json: JSON input -> validated model
- encode_json: model -> valid JSON text or bytes
- compile_adapter: construct SchemaBridge from two already-created types

Manual validation, bridge validation, msgspec.convert(strict=True) and
Pydantic.model_validate(strict=True) are measured on the same flat data.
Their complete semantics are still not equivalent on complex types.
The bridge uses standard-library JSON parsing; msgspec and Pydantic use
dedicated decoders. Compile time is measured separately to expose startup
overhead. No direct-dataclass constructor is substituted for validation.

timeit uses 150 warmups plus repeated measurements; the output includes
individual ns/call samples, medians, interpreter, operating system and package
versions. Results are run-specific and do not demonstrate throughput,
native memory usage or a need for a C implementation.

Reproduce from Tools/experiments/record:

    python -m pip install -r requirements-research.txt
    python -m bridge.benchmark_bridge --number 3000 --repeat 5 \
      --sizes 3 10 30 --output bridge-results.json

Use several machines, nested representative payloads and production workloads
before making an upstream performance claim. For memory layout baselines,
refer to the parent study's RESULTS.md (bridge models are slotted dataclasses).
