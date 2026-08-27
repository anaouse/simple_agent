import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError
from watchfiles import Change, awatch
from win11toast import toast

from app.ai.anthropic_agent import AnthropicAgent
from app.ai.openai_agent import OpenAIAgent
from app.config import CONFIG_PATH, get_agent_config, get_model_config, set_default_model
from app.project_files import ProjectFileIndex
from app.skill_files import SkillIndex
from app.session import ConversationSession
from app.models import (
    ApiModel,
    ClientMessage,
    ContentDeltaEvent,
    ErrorBody,
    ErrorEvent,
    ErrorResponse,
    MessageEndEvent,
    InterruptSessionRequest,
    InterruptSessionResponse,
    MessageStartEvent,
    ModelListResponse,
    ModelSummary,
    DefaultModelRequest,
    DefaultModelResponse,
    NewSessionRequest,
    NewSessionResponse,
    OpenSessionRequest,
    ProjectRequest,
    ProjectResponse,
    SessionListResponse,
    SessionResponse,
    SessionSummary,
    ModelsEvent,
    SkillsEvent,
    ToolCallArgumentsEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
    UserMessageEvent,
    UserMessageRejectedEvent,
)

ACTIVE_CHATS: dict[str, asyncio.Task[None]] = {}
app = FastAPI(title="Local Agent")
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


@app.get("/api/models")
async def list_models() -> ModelListResponse:
    return ModelListResponse(
        models=[
            ModelSummary(name=model.name, compatible=model.compatible)
            for model in get_agent_config().models
        ]
    )


@app.put("/api/models/default")
async def update_default_model(request: DefaultModelRequest) -> DefaultModelResponse:
    set_default_model(request.model_name)
    return DefaultModelResponse(default_model=request.model_name)


def model_event() -> ModelsEvent:
    try:
        models = [
            ModelSummary(name=model.name, compatible=model.compatible)
            for model in get_agent_config().models
        ]
    except (OSError, ValueError, ValidationError):
        models = []
    try:
        default_model = get_agent_config().default_model
    except (OSError, ValueError, ValidationError):
        default_model = None
    return ModelsEvent(models=models, default_model=default_model)


def skills_root() -> Path | None:
    try:
        configured_path = get_agent_config().skills_path
        if configured_path is None:
            return None
        resolved = configured_path.expanduser().resolve(strict=True)
        return resolved if resolved.is_dir() else None
    except (OSError, RuntimeError, ValueError, ValidationError):
        return None


def config_watch_filter(change: Change, changed_path: str) -> bool:
    try:
        return Path(changed_path).resolve() == CONFIG_PATH.resolve()
    except (OSError, RuntimeError):
        return False


@app.websocket("/ws/models")
async def models(websocket: WebSocket) -> None:
    await websocket.accept()
    config_path = CONFIG_PATH
    changes = awatch(config_path.parent, watch_filter=config_watch_filter)
    try:
        await send_event(websocket, model_event())
        while True:
            change_task = asyncio.create_task(anext(changes))
            disconnect_task = asyncio.create_task(websocket.receive_text())
            done, pending = await asyncio.wait(
                {change_task, disconnect_task}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            if disconnect_task in done:
                disconnect_task.result()
                continue
            await send_event(websocket, model_event())
    except WebSocketDisconnect:
        logger.info("Models WebSocket disconnected")
    finally:
        await changes.aclose()


@app.websocket("/ws/skills")
async def skills(websocket: WebSocket) -> None:
    await websocket.accept()
    index = SkillIndex(skills_root())
    try:
        await send_event(websocket, index.event())
        while True:
            paths = [CONFIG_PATH.parent]
            if index.root is not None:
                paths.append(index.root)
            changes = awatch(*paths)
            try:
                change_task = asyncio.create_task(anext(changes))
                disconnect_task = asyncio.create_task(websocket.receive_text())
                done, pending = await asyncio.wait(
                    {change_task, disconnect_task}, return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
                if disconnect_task in done:
                    disconnect_task.result()
                    continue
                await send_event(websocket, index.refresh(skills_root()))
            finally:
                await changes.aclose()
    except WebSocketDisconnect:
        logger.info("Skills WebSocket disconnected")


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


@app.post("/api/sessions")
async def create_session(request: NewSessionRequest) -> NewSessionResponse:
    resolved = resolve_project_path(request.project_path)
    await interrupt_active_chat(resolved)
    session = ConversationSession(get_agent_config().data_dir, resolved)
    session.start_new()
    logger.info("New session started for project: {}", resolved)
    return NewSessionResponse(
        project_path=resolved.as_posix(), session_file=session.file_name or ""
    )


@app.post("/api/sessions/interrupt")
async def interrupt_session(request: InterruptSessionRequest) -> InterruptSessionResponse:
    resolved = resolve_project_path(request.project_path)
    active_chat = ACTIVE_CHATS.get(resolved.as_posix())
    interrupted = active_chat is not None and not active_chat.done()
    await interrupt_active_chat(resolved)
    return InterruptSessionResponse(interrupted=interrupted)


@app.get("/api/sessions")
async def list_sessions(project_path: str) -> SessionListResponse:
    resolved = resolve_project_path(project_path)
    session = ConversationSession(get_agent_config().data_dir, resolved)
    return SessionListResponse(
        sessions=[SessionSummary(file_name=name) for name in session.list_files()]
    )


@app.get("/api/sessions/current")
async def get_current_session(project_path: str) -> SessionResponse:
    resolved = resolve_project_path(project_path)
    session = ConversationSession(get_agent_config().data_dir, resolved)
    try:
        messages = session.load_latest()
    except (OSError, ValueError):
        logger.exception("Failed to load session for {}", resolved)
        messages = []
    return SessionResponse(
        session_file=session.file_name,
        total_token=session.total_token,
        messages=messages,
    )


@app.post("/api/sessions/open")
async def open_session(request: OpenSessionRequest) -> SessionResponse:
    resolved = resolve_project_path(request.project_path)
    await interrupt_active_chat(resolved)
    session = ConversationSession(get_agent_config().data_dir, resolved)
    messages = session.load(request.session_file)
    logger.info("Session opened: {}", session.file_name)
    return SessionResponse(
        session_file=session.file_name,
        total_token=session.total_token,
        messages=messages,
    )


def resolve_skill_message(content: str) -> str:
    command, separator, question = content.partition(" ")
    if command != "/skill" or not separator:
        return content
    skill_name, separator, question = question.strip().partition(" ")
    root = skills_root()
    if not skill_name or not separator or root is None:
        return content
    skill_directory = root / skill_name
    skill_file = skill_directory / "SKILL.md"
    if not skill_directory.is_dir() or not skill_file.is_file():
        return content
    return (
        f"请你阅读 `{skill_file.as_posix()}` 然后结合这个文件夹下的提示理解接下来的问题："
        f"{question.strip()}"
    )


async def interrupt_active_chat(project_path: Path) -> None:
    active_chat = ACTIVE_CHATS.get(project_path.as_posix())
    if active_chat is None or active_chat.done():
        return
    active_chat.cancel()
    try:
        await active_chat
    except asyncio.CancelledError:
        pass


def resolve_project_path(project_path: str) -> Path:
    path = Path(project_path).expanduser()
    try:
        resolved = path.resolve(strict=True)
        if not path.is_absolute() or not resolved.is_dir():
            raise ValueError
    except (OSError, RuntimeError, ValueError) as exception:
        raise ProjectPathError("请输入有效的绝对文件夹路径") from exception
    return resolved


@app.websocket("/ws/project-files")
async def project_files(websocket: WebSocket, project_path: str) -> None:
    try:
        resolved = resolve_project_path(project_path)
    except ProjectPathError:
        await websocket.close(code=1008, reason="Invalid project path")
        return

    await websocket.accept()
    index = ProjectFileIndex(resolved)
    changes = index.changes()
    try:
        await send_event(websocket, index.event())
        while True:
            change_task = asyncio.create_task(anext(changes))
            disconnect_task = asyncio.create_task(websocket.receive_text())
            done, pending = await asyncio.wait(
                {change_task, disconnect_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            if disconnect_task in done:
                disconnect_task.result()
                continue
            await send_event(websocket, change_task.result())
    except WebSocketDisconnect:
        logger.info("Project files WebSocket disconnected: {}", resolved)
    except asyncio.CancelledError:
        logger.info("Project files watcher stopped: {}", resolved)
    finally:
        await changes.aclose()


@app.websocket("/ws/chat")
async def chat(
    websocket: WebSocket,
    project_path: str,
    session_file: str | None = None,
    model: str | None = None,
) -> None:
    path = Path(project_path).expanduser()
    try:
        resolved = path.resolve(strict=True)
        if not path.is_absolute() or not resolved.is_dir():
            raise ValueError
    except (OSError, RuntimeError, ValueError):
        await websocket.close(code=1008, reason="Invalid project path")
        return
    try:
        model_config = get_model_config(model)
        if model_config.compatible not in ("anthropic", "openai"):
            raise ValueError
    except ValueError:
        await websocket.close(code=1008, reason="Invalid model")
        return

    await websocket.accept()
    project_key = resolved.as_posix()
    current_task = asyncio.current_task()
    if current_task is not None:
        ACTIVE_CHATS[project_key] = current_task
    session = ConversationSession(get_agent_config().data_dir, resolved)
    try:
        if session_file is None:
            session.load_latest()
        else:
            session.load(session_file)
    except (OSError, ValueError):
        logger.exception("Failed to load session for {}", resolved)
    
    # Create agent based on compatible field
    if model_config.compatible == "openai":
        agent = OpenAIAgent(get_agent_config(), model_config, resolved)
    else:
        agent = AnthropicAgent(get_agent_config(), model_config, resolved)
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
            content = resolve_skill_message(message.content)
            attachments = message.attachments
            message_id = str(uuid4())
            created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            marker = len(session.messages)
            user_message_id = session.append_user(content, attachments)
            await send_event(
                websocket,
                UserMessageEvent(
                    id=user_message_id,
                    content=content,
                    attachments=attachments,
                    created_at=created_at,
                ),
            )
            await send_event(
                websocket,
                MessageStartEvent(message_id=message_id, created_at=created_at),
            )

            try:
                async for event in agent.reply(content, attachments):
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
                    elif event["type"] == "tool_call_arguments":
                        session.update_tool_arguments(
                            event["tool_call_id"], event["arguments"]
                        )
                        await send_event(
                            websocket,
                            ToolCallArgumentsEvent(
                                message_id=message_id,
                                tool_call_id=event["tool_call_id"],
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
                session.update_total_token(agent.get_total_token())
                session.save()
                await send_event(
                    websocket,
                    MessageEndEvent(
                        message_id=message_id,
                        total_token=session.total_token,
                    ),
                )
                toast("Simple Agent", "模型回答已结束", app_id="Simple Agent")
            except WebSocketDisconnect:
                raise
            except Exception as exception:
                if attachments and getattr(exception, "status_code", None) == 400:
                    session.truncate(marker)
                    agent.load_session(session.messages)
                    await send_event(
                        websocket,
                        UserMessageRejectedEvent(
                            message_id=user_message_id,
                            content=content,
                            attachments=attachments,
                            error=ErrorBody(
                                code="IMAGE_NOT_SUPPORTED",
                                message="该模型不支持图片输入",
                            ),
                        ),
                    )
                    continue
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
                toast("Simple Agent", "模型回答出错", app_id="Simple Agent")
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except asyncio.CancelledError:
        logger.info("WebSocket chat interrupted for new session: {}", resolved)
    finally:
        session.interrupt()
        session.save()
        await agent.close()
        if current_task is not None and ACTIVE_CHATS.get(project_key) is current_task:
            ACTIVE_CHATS.pop(project_key, None)


async def send_event(websocket: WebSocket, event: ApiModel) -> None:
    await websocket.send_text(event.model_dump_json(by_alias=True))
