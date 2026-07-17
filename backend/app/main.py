from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError

from app.ai.anthropic_agent import AnthropicAgent
from app.config import get_settings
from app.models import (
    ApiModel,
    ClientMessage,
    ContentDeltaEvent,
    ErrorBody,
    ErrorEvent,
    ErrorResponse,
    MessageEndEvent,
    MessageStartEvent,
)

SETTINGS = get_settings()
app = FastAPI(title=SETTINGS.APP_NAME)


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


@app.websocket("/ws/chat")
async def chat(websocket: WebSocket) -> None:
    await websocket.accept()
    agent = AnthropicAgent(SETTINGS)

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
            await send_event(
                websocket,
                MessageStartEvent(
                    message_id=message_id,
                    created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                ),
            )

            try:
                async for delta in agent.reply(message.content):
                    await send_event(
                        websocket,
                        ContentDeltaEvent(message_id=message_id, delta=delta),
                    )
                await send_event(websocket, MessageEndEvent(message_id=message_id))
            except Exception:
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
        await agent.close()


async def send_event(websocket: WebSocket, event: ApiModel) -> None:
    await websocket.send_text(event.model_dump_json(by_alias=True))
