# Case studies of public model changes

These tests reproduce only the changed fields using Pydantic v2.
They do NOT execute complete upstream model implementations or all
application validators. References below are verified source commits.

## FastAPI: OpenAPI Schema.type (2025-09-20)

https://github.com/fastapi/fastapi/commit/8ede27223e48386b4cc97302eea0818e2e767187

File: fastapi/openapi/models.py; old type annotation was Optional[str].
New annotation is Optional[Union[SchemaType, List[SchemaType]]], with
SchemaType limited to seven Literal strings.

The analyzer reports review_required (annotation_changed), not a definite
break. A Pydantic-v2 minimal witness shows that old accepted
{"type": "custom-extension"} while new rejects it; the new form also
accepts {"type": ["string", "null"]}, which old rejects.

CONCLUSION: A definite break can be hidden behind review_required.
A CI gate that fails only for breaking_detected misses this case.

## openai-python: new response metadata (2026-08-17)

https://github.com/openai/openai-python/commit/ff14a33c1b21c36b9e43a0150a3818ee3aa3712a

File: src/openai/types/chat/chat_completion.py. New ChatCompletion
response model has an Optional[Metadata] = None field.

Our *minimal* reconstruction models the field as dict[str, str] | None
and uses Pydantic's plain BaseModel, not openai._models.BaseModel.
For output migration the analyzer reports review_required (new_output_field).
The minimal old Pydantic reader ignores the extra key, so the observed
sample succeeds. An actual specialized old reader could behave differently.

CONCLUSION: review warnings are not synonymous with actual breakage.

## Calibration control

Two synthetic Pydantic models differ by a new required string field.
The analyzer reports breaking_detected, and a previously valid input
fails under the new model.

## Observations

| Case | Analyzer | Minimal runtime check |
|---|---|---|
| FastAPI field type | review_required | Breaking witness |
| openai-python optional output field | review_required | Old default-Pydantic reader accepts |
| Synthetic new required field | breaking_detected | Breaking witness |

These two source-derived field-level studies do not support numerical
sensitivity, specificity, precision, or false-positive-rate claims.
To generalize, pin and run full upstream project environments on actual
schema revisions and historical payloads, including custom behavior.
