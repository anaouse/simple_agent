from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=lambda name: "".join(
        [name.split("_")[0], *[part.title() for part in name.split("_")[1:]]]
    ), populate_by_name=True)


class ClientMessage(ApiModel):
    type: Literal["message"]
    content: str = Field(min_length=1, max_length=100_000)


class MessageStartEvent(ApiModel):
    type: Literal["message_start"] = "message_start"
    message_id: str
    created_at: str


class ContentDeltaEvent(ApiModel):
    type: Literal["content_delta"] = "content_delta"
    message_id: str
    delta: str


class MessageEndEvent(ApiModel):
    type: Literal["message_end"] = "message_end"
    message_id: str


class ErrorBody(ApiModel):
    code: str
    message: str


class ErrorResponse(ApiModel):
    error: ErrorBody


class ErrorEvent(ApiModel):
    type: Literal["error"] = "error"
    error: ErrorBody
