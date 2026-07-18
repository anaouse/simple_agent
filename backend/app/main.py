from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError

from app.ai.anthropic_agent import AnthropicAgent
from app.config import get_settings
from app.session import ConversationSession
from app.models import (
    ApiModel,
    ClientMessage,
    ContentDeltaEvent,
    ErrorBody,
    ErrorEvent,
    ErrorResponse,
    MessageEndEvent,
    MessageStartEvent,
    ProjectRequest,
    ProjectResponse,
    SessionResponse,
    ToolCallResultEvent,
    ToolCallStartEvent,
)

SETTINGS = get_settings()
app = FastAPI(title=SETTINGS.APP_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProjectPathError(Exception):
    pass


@app.exception_handler(ProjectPathError)
async def project_path_error_handler(
    request: Request, exception: ProjectPathError
) -> JSONResponse:
    response = ErrorResponse(
        error=ErrorBody(code="INVALID_PROJECT_PATH", message=str(exception))
    )
    return JSONResponse(status_code=400, content=response.model_dump(by_alias=True))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exception: RequestValidationError
) -> JSONResponse:
    logger.warning("Invalid request: {}", exception)
    response = ErrorResponse(
        error=ErrorBody(code="INVALID_REQUEST", message="请求数据无效")
    )
    return JSONResponse(status_code=422, content=response.model_dump(by_alias=True))


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exception: Exception) -> JSONResponse:
    logger.exception("Unhandled server error: {}", exception)
    response = ErrorResponse(
        error=ErrorBody(code="INTERNAL_ERROR", message="服务器内部错误")
    )
    return JSONResponse(status_code=500, content=response.model_dump(by_alias=True))


@app.post("/api/projects")
async def create_project(request: ProjectRequest) -> ProjectResponse:
    raw_path = request.path.strip()
    path = Path(raw_path).expanduser()
    if not raw_path or not path.is_absolute():
        raise ProjectPathError("请输入有效的绝对文件夹路径")
    try:
        path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir():
            raise ProjectPathError("该路径不是文件夹")
        resolved = path.resolve(strict=True)
    except ProjectPathError:
        raise
    except (OSError, RuntimeError) as exception:
        logger.warning("Failed to create project directory {}: {}", raw_path, exception)
        raise ProjectPathError("无法创建或访问该文件夹") from exception
    return ProjectResponse(path=resolved.as_posix())


@app.get("/api/sessions/current")
async def get_current_session(project_path: str) -> SessionResponse:
    resolved = resolve_project_path(project_path)
    session = ConversationSession(SETTINGS.DATA_DIR, resolved)
    try:
        messages = session.load_latest()
    except (OSError, ValueError):
        logger.exception("Failed to load session for {}", resolved)
        messages = []
    return SessionResponse(messages=messages)


def resolve_project_path(project_path: str) -> Path:
    path = Path(project_path).expanduser()
    try:
        resolved = path.resolve(strict=True)
        if not path.is_absolute() or not resolved.is_dir():
            raise ValueError
    except (OSError, RuntimeError, ValueError) as exception:
        raise ProjectPathError("请输入有效的绝对文件夹路径") from exception
    return resolved


@app.websocket("/ws/chat")
async def chat(websocket: WebSocket, project_path: str) -> None:
    path = Path(project_path).expanduser()
    try:
        resolved = path.resolve(strict=True)
        if not path.is_absolute() or not resolved.is_dir():
            raise ValueError
    except (OSError, RuntimeError, ValueError):
        await websocket.close(code=1008, reason="Invalid project path")
        return

    await websocket.accept()
    session = ConversationSession(SETTINGS.DATA_DIR, resolved)
    try:
        session.load_latest()
    except (OSError, ValueError):
        logger.exception("Failed to load session for {}", resolved)
    agent = AnthropicAgent(SETTINGS, resolved)
    agent.load_session(session.messages)

    try:
        while True:
            try:
                message = ClientMessage.model_validate_json(await websocket.receive_text())
            except ValidationError:
                await send_event(
                    websocket,
                    ErrorEvent(
                        error=ErrorBody(
                            code="INVALID_MESSAGE", message="消息格式无效"
                        )
                    ),
                )
                continue

            logger.info("User message received")
            message_id = str(uuid4())
            created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            session.append_user(message.content)
            await send_event(
                websocket,
                MessageStartEvent(message_id=message_id, created_at=created_at),
            )

            try:
                async for event in agent.reply(message.content):
                    if event["type"] == "content_delta":
                        session.append_delta(message_id, event["delta"], created_at)
                        await send_event(
                            websocket,
                            ContentDeltaEvent(
                                message_id=message_id, delta=event["delta"]
                            ),
                        )
                    elif event["type"] == "tool_call_start":
                        session.start_tool(
                            message_id,
                            event["tool_call_id"],
                            event["tool_name"],
                            event["arguments"],
                            created_at,
                        )
                        await send_event(
                            websocket,
                            ToolCallStartEvent(
                                message_id=message_id,
                                tool_call_id=event["tool_call_id"],
                                tool_name=event["tool_name"],
                                arguments=event["arguments"],
                            ),
                        )
                    else:
                        session.finish_tool(
                            event["tool_call_id"], event["result"], event["is_error"]
                        )
                        await send_event(
                            websocket,
                            ToolCallResultEvent(
                                message_id=message_id,
                                tool_call_id=event["tool_call_id"],
                                result=event["result"],
                                is_error=event["is_error"],
                            ),
                        )
                session.finish_message(message_id)
                session.save()
                await send_event(websocket, MessageEndEvent(message_id=message_id))
            except WebSocketDisconnect:
                raise
            except Exception:
                session.interrupt()
                session.save()
                await send_event(
                    websocket,
                    ErrorEvent(
                        error=ErrorBody(
                            code="UPSTREAM_ERROR", message="模型服务暂时不可用"
                        )
                    ),
                )
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    finally:
        session.interrupt()
        session.save()
        await agent.close()


async def send_event(websocket: WebSocket, event: ApiModel) -> None:
    await websocket.send_text(event.model_dump_json(by_alias=True))
