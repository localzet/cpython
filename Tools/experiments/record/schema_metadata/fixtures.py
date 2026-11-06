"""Two intentionally different API versions for the migration CLI."""
from dataclasses import dataclass
from typing import NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict, Field


class ApiV1(TypedDict):
    id: int
    display: NotRequired[str]


class ApiV2Breaking(TypedDict):
    id: int
    display: str
    region: str


class ApiV2Relaxed(TypedDict):
    id: int
    display: NotRequired[str]
    timezone: NotRequired[str]


@dataclass(slots=True)
class ObjectV1:
    id: int
    nickname: str = "Anonymous"


@dataclass(slots=True)
class ObjectV2:
    id: int
    nickname: str = "Guest"


class AliasV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    display: str = Field(validation_alias="display_in",
                         serialization_alias="display_out")


class AliasV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    display: str = Field(validation_alias="name_in",
                         serialization_alias="name_out")
