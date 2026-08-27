import hashlib
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from loguru import logger

from app.models import (
    CHAT_MESSAGE_ADAPTER,
    Attachment,
    ChatMessage,
    SessionStorage,
    TextChatMessage,
    ToolChatMessage,
)

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
        self.total_token = 0
        self.messages: list[ChatMessage] = []

    @property
    def file_name(self) -> str | None:
        return self._path.name if self._path is not None else None

    def list_files(self) -> list[str]:
        if not self._directory.is_dir():
            return []
        return [
            path.name
            for path in sorted(
                self._directory.glob("*.json"),
                key=lambda item: item.stat().st_mtime,
                reverse=True,
            )
        ]

    def load_latest(self) -> list[ChatMessage]:
        files = self.list_files()
        if not files:
            return []
        return self.load(files[0])

    def load(self, file_name: str) -> list[ChatMessage]:
        if Path(file_name).name != file_name or not file_name.endswith(".json"):
            raise ValueError("Invalid session file")
        path = self._directory / file_name
        if not path.is_file():
            raise ValueError("Session file does not exist")
        self._path = path
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            self.messages = [CHAT_MESSAGE_ADAPTER.validate_python(item) for item in data]
            self.total_token = 0
        else:
            storage = SessionStorage.model_validate(data)
            self.messages = storage.messages
            self.total_token = storage.total_token
        self._dirty = False
        return self.messages

    def start_new(self) -> None:
        # Reuse the latest session file if it is still empty, instead of
        # creating another empty file every time "new session" is clicked.
        files = self.list_files()
        if files:
            latest_path = self._directory / files[0]
            try:
                data = json.loads(latest_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = None
            if data == [] or data == {"totalToken": 0, "messages": []}:
                self._path = latest_path
                self.total_token = 0
                self.messages = []
                self._dirty = False
                logger.info("Reused empty session: {}", self._path)
                return

        self._directory.mkdir(parents=True, exist_ok=True)
        self._path = self._next_path()
        self._path.write_text(
            '{\n  "totalToken": 0,\n  "messages": []\n}', encoding="utf-8"
        )
        self.total_token = 0
        self.messages = []
        self._dirty = False
        logger.info("Session created: {}", self._path)

    def update_total_token(self, total_token: int) -> None:
        self.total_token = total_token
        self._dirty = True

    def append_user(
        self, content: str, attachments: list[Attachment] | None = None
    ) -> str:
        self._dirty = True
        message_id = str(uuid4())
        self.messages.append(
            TextChatMessage(
                id=message_id,
                role="user",
                content=content,
                attachments=attachments or [],
                status="complete",
                created_at=datetime.now().astimezone().isoformat(),
            )
        )
        return message_id

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

    def update_tool_arguments(
        self, tool_call_id: str, arguments: dict[str, object]
    ) -> None:
        for message in reversed(self.messages):
            if isinstance(message, ToolChatMessage) and message.id == tool_call_id:
                message.arguments = arguments
                self._dirty = True
                return

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

    def truncate(self, count: int) -> None:
        if len(self.messages) > count:
            self.messages = self.messages[:count]
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
            self._path = self._next_path()
        storage = SessionStorage(total_token=self.total_token, messages=self.messages)
        self._path.write_text(
            json.dumps(
                storage.model_dump(by_alias=True),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self._dirty = False
        logger.info("Session saved: {}", self._path)

    def _next_path(self) -> Path:
        # Colons are invalid in Windows filenames, so use hyphens in the time part.
        stem = datetime.now().astimezone().strftime("%Y-%m-%d %H-%M-%S")
        path = self._directory / f"{stem}.json"
        suffix = 1
        while path.exists():
            path = self._directory / f"{stem}-{suffix}.json"
            suffix += 1
        return path

    def _complete_assistant_nodes(self, message_id: str) -> None:
        for message in self.messages:
            if (
                isinstance(message, TextChatMessage)
                and message.role == "assistant"
                and message.parent_message_id == message_id
                and message.status == "streaming"
            ):
                message.status = "complete"
