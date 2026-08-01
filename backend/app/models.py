from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=lambda name: "".join(
        [name.split("_")[0], *[part.title() for part in name.split("_")[1:]]]
    ), populate_by_name=True)


class ClientMessage(ApiModel):
    type: Literal["message"]
    content: str = Field(min_length=1, max_length=100_000)


class ModelSummary(ApiModel):
    name: str
    compatible: str


class ModelListResponse(ApiModel):
    models: list[ModelSummary]


class DefaultModelRequest(ApiModel):
    model_name: str = Field(min_length=1)


class DefaultModelResponse(ApiModel):
    default_model: str


class ModelsEvent(ApiModel):
    type: Literal["models"] = "models"
    models: list[ModelSummary]
    default_model: str | None = None


class SkillEntry(ApiModel):
    name: str


class SkillsEvent(ApiModel):
    type: Literal["skills"] = "skills"
    entries: list[SkillEntry]


class ProjectRequest(ApiModel):
    path: str = Field(min_length=1, max_length=4096)


class ProjectResponse(ApiModel):
    path: str


class ProjectFileEntry(ApiModel):
    path: str
    absolute_path: str
    is_directory: bool


class ProjectFilesEvent(ApiModel):
    type: Literal["project_files"] = "project_files"
    entries: list[ProjectFileEntry]


class BaseChatMessage(ApiModel):
    id: str
    status: Literal["complete", "streaming", "error"]
    created_at: str


class TextChatMessage(BaseChatMessage):
    role: Literal["user", "assistant"]
    content: str
    parent_message_id: str | None = None


class ToolChatMessage(BaseChatMessage):
    role: Literal["tool"]
    parent_message_id: str
    tool_name: str
    arguments: dict[str, JsonValue]
    result: str


ChatMessage = Annotated[TextChatMessage | ToolChatMessage, Field(discriminator="role")]
CHAT_MESSAGE_ADAPTER = TypeAdapter(ChatMessage)


class SessionResponse(ApiModel):
    session_file: str | None = None
    total_token: int = 0
    messages: list[TextChatMessage | ToolChatMessage]


class SessionStorage(ApiModel):
    total_token: int = 0
    messages: list[TextChatMessage | ToolChatMessage] = Field(default_factory=list)


class SessionSummary(ApiModel):
    file_name: str


class SessionListResponse(ApiModel):
    sessions: list[SessionSummary]


class SessionRequest(ApiModel):
    project_path: str = Field(min_length=1, max_length=4096)


class NewSessionRequest(SessionRequest):
    pass


class InterruptSessionRequest(SessionRequest):
    pass


class InterruptSessionResponse(ApiModel):
    interrupted: bool


class OpenSessionRequest(SessionRequest):
    session_file: str = Field(min_length=6, max_length=255)


class NewSessionResponse(ApiModel):
    project_path: str
    session_file: str


class UserMessageEvent(ApiModel):
    type: Literal["user_message"] = "user_message"
    content: str
    created_at: str


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
    total_token: int


class ToolCallStartEvent(ApiModel):
    type: Literal["tool_call_start"] = "tool_call_start"
    message_id: str
    tool_call_id: str
    tool_name: str
    arguments: dict[str, JsonValue]


class ToolCallArgumentsEvent(ApiModel):
    type: Literal["tool_call_arguments"] = "tool_call_arguments"
    message_id: str
    tool_call_id: str
    arguments: dict[str, JsonValue]


class ToolCallResultEvent(ApiModel):
    type: Literal["tool_call_result"] = "tool_call_result"
    message_id: str
    tool_call_id: str
    result: str
    is_error: bool = False


class ErrorBody(ApiModel):
    code: str
    message: str


class ErrorResponse(ApiModel):
    error: ErrorBody


class ErrorEvent(ApiModel):
    type: Literal["error"] = "error"
    error: ErrorBody
