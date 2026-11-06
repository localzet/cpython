# Declared type inclusion: limited supported grammar

This tool is NOT mypy, Pyright, a general type solver or a runtime validator.
It looks for synthetic values admitted by an old annotation but excluded
by a newer annotation, otherwise returning unknown.

Supported: Literal, str/int/float/bool/bytes/None, unions (including
Optional), list[T], dict[str, T] and homogeneous tuple[T, ...].
The checker compares container *values*, not static generic variance.

Unsupported and unknown: Any, Annotated constraints, custom classes,
Protocols, recursive dataclasses, coercion, provider-specific validators,
serialization hooks, arbitrary subtyping or user-defined generic types.

A breaking report includes an illustrative **synthetic counterexample**
constructed from simple candidates, never customer input. Missing a witness
does NOT establish safety. In particular, a Python bool is a subtype of int
under ordinary isinstance but strict Pydantic/msgspec rules may reject it.

On 2025-09-20 FastAPI changed Schema.type from Optional[str] to a union
containing a restricted Literal set and list of that set, plus None.
A string outside the restricted set supplies a declared counterexample.
See CASE_STUDIES.md for upstream commit and simplified runtime reproduction.

The full Pydantic runtime model is NOT proven equivalent to the annotation.
Custom validators and settings may accept excluded values or reject included
values. Treat the analyzer as a human review tool for API evolution.
