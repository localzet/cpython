"""Field-level reproductions of documented upstream changes (not exact models).

Sources and limitations are in docs/CASE_STUDIES.md.
"""
from typing import Literal
from pydantic import BaseModel, ConfigDict

# fastapi/fastapi commit 8ede27223e48386b4cc97302eea0818e2e767187
class FastAPISchemaOld(BaseModel):
    type: str | None = None

SchemaType = Literal["array", "boolean", "integer", "null", "number", "object", "string"]

class FastAPISchemaNew(BaseModel):
    type: SchemaType | list[SchemaType] | None = None

# openai/openai-python commit ff14a33c1b21c36b9e43a0150a3818ee3aa3712a
# The actual library uses its own BaseModel subclass. We only model the field.
class ChatCompletionOld(BaseModel):
    id: str
    object: Literal["chat.completion"]

class ChatCompletionNew(BaseModel):
    id: str
    object: Literal["chat.completion"]
    metadata: dict[str, str] | None = None

class StrictOld(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int

class StrictNew(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    region: str
