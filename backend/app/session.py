import hashlib
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from loguru import logger

from app.models import CHAT_MESSAGE_ADAPTER, ChatMessage, TextChatMessage, ToolChatMessage

_INTERRUPTED_TEXT = "\n\n[用户中断了本次回答]"
_INTERRUPTED_RESULT = "用户中断"


class ConversationSession:
    def __init__(self, data_dir: Path, project_path: Path) -> None:
        project_key = hashlib.sha256(
            project_path.resolve().as_posix().encode("utf-8")
        ).hexdigest()
        self._directory = data_dir.expanduser().resolve() / project_key
        self._path: Path | None = None
        self._dirty = False
        self.messages: list[ChatMessage] = []

    def load_latest(self) -> list[ChatMessage]:
        if not self._directory.is_dir():
            return []
        for temporary in self._directory.glob("*.json.tmp"):
            try:
                temporary.unlink()
            except OSError:
                logger.warning("Failed to remove stale session file: {}", temporary)
        files = sorted(self._directory.glob("*.json"), key=lambda path: path.stat().st_mtime)
        if not files:
            return []
        self._path = files[-1]
        data = json.loads(self._path.read_text(encoding="utf-8"))
        self.messages = [CHAT_MESSAGE_ADAPTER.validate_python(item) for item in data]
        self._dirty = False
        return self.messages

    def append_user(self, content: str) -> None:
        self._dirty = True
        self.messages.append(
            TextChatMessage(
                id=str(uuid4()),
                role="user",
                content=content,
                status="complete",
                created_at=datetime.now().astimezone().isoformat(),
            )
        )

    def append_delta(self, message_id: str, content: str, created_at: str) -> None:
        self._dirty = True
        last = self.messages[-1] if self.messages else None
        if (
            isinstance(last, TextChatMessage)
            and last.role == "assistant"
            and last.parent_message_id == message_id
            and last.status == "streaming"
        ):
            last.content += content
            return
        self.messages.append(
            TextChatMessage(
                id=str(uuid4()),
                parent_message_id=message_id,
                role="assistant",
                content=content,
                status="streaming",
                created_at=created_at,
            )
        )

    def start_tool(
        self,
        message_id: str,
        tool_call_id: str,
        tool_name: str,
        arguments: dict[str, object],
        created_at: str,
    ) -> None:
        self._dirty = True
        self._complete_assistant_nodes(message_id)
        self.messages.append(
            ToolChatMessage(
                id=tool_call_id,
                parent_message_id=message_id,
                role="tool",
                tool_name=tool_name,
                arguments=arguments,
                result="",
                status="streaming",
                created_at=created_at,
            )
        )

    def finish_tool(self, tool_call_id: str, result: str, is_error: bool) -> None:
        for message in reversed(self.messages):
            if isinstance(message, ToolChatMessage) and message.id == tool_call_id:
                message.result = result
                message.status = "error" if is_error else "complete"
                self._dirty = True
                return

    def finish_message(self, message_id: str) -> None:
        for message in self.messages:
            if message.parent_message_id == message_id and message.status == "streaming":
                message.status = "complete"
                self._dirty = True

    def interrupt(self) -> None:
        for message in self.messages:
            if message.status != "streaming":
                continue
            if isinstance(message, ToolChatMessage):
                message.result = message.result or _INTERRUPTED_RESULT
                message.status = "error"
                self._dirty = True
            elif message.role == "assistant":
                message.content += _INTERRUPTED_TEXT
                message.status = "error"
                self._dirty = True

    def save(self) -> None:
        if not self.messages or not self._dirty:
            return
        self._directory.mkdir(parents=True, exist_ok=True)
        if self._path is None:
            # Colons are invalid in Windows filenames, so use hyphens in the time part.
            filename = datetime.now().astimezone().strftime("%Y-%m-%d %H-%M-%S.json")
            self._path = self._directory / filename
        self._path.write_text(
            json.dumps(
                [message.model_dump(by_alias=True) for message in self.messages],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self._dirty = False
        logger.info("Session saved: {}", self._path)

    def _complete_assistant_nodes(self, message_id: str) -> None:
        for message in self.messages:
            if (
                isinstance(message, TextChatMessage)
                and message.role == "assistant"
                and message.parent_message_id == message_id
                and message.status == "streaming"
            ):
                message.status = "complete"
