import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Callable, Literal, TypedDict

from anthropic import AsyncAnthropic
from loguru import logger

from app.ai.anthropic_session_adaptor import AnthropicSessionAdaptor
from app.config import AgentConfig, ModelConfig
from app.models import ChatMessage
from app.tools import bash, edit, read, walk, write
from app.tools.security import set_project_root
from app.tools.tool_utils import tools_from_functions


class ContentDelta(TypedDict):
    type: Literal["content_delta"]
    delta: str


class ToolCallStart(TypedDict):
    type: Literal["tool_call_start"]
    tool_call_id: str
    tool_name: str
    arguments: dict[str, object]


class ToolCallArguments(TypedDict):
    type: Literal["tool_call_arguments"]
    tool_call_id: str
    arguments: dict[str, object]


class ToolCallResult(TypedDict):
    type: Literal["tool_call_result"]
    tool_call_id: str
    result: str
    is_error: bool


class InternalToolResultEvent(TypedDict):
    type: Literal["tool_result_internal"]
    message: dict[str, object]


AgentEvent = ContentDelta | ToolCallStart | ToolCallArguments | ToolCallResult


class AnthropicAgent:
    def __init__(
        self, config: AgentConfig, model: ModelConfig, project_path: Path
    ) -> None:
        if model.compatible != "anthropic":
            raise ValueError(f"暂不支持的模型兼容格式: {model.compatible}")
        self._model = model
        self._project_path = project_path.resolve()
        set_project_root(self._project_path)
        self._client = AsyncAnthropic(
            api_key=model.api_key,
            base_url=model.url,
        )
        self._messages: list[dict[str, object]] = []
        self._total_token = 0
        base_prompt = self._read_system_prompt(config.system_prompt_path)
        self._system_prompt = self._build_system_prompt(base_prompt)
        self._tools, self._tool_functions = tools_from_functions(
            [read, write, edit, walk, bash]
        )

    def load_session(self, messages: list[ChatMessage]) -> None:
        self._messages = AnthropicSessionAdaptor.to_anthropic(messages)

    async def reply(self, user_content: str) -> AsyncIterator["AgentEvent"]:
        set_project_root(self._project_path)
        self._messages.append({"role": "user", "content": user_content})

        try:
            while True:
                logger.info("Upstream API call started")
                request: dict[str, object] = {
                    "model": self._model.name,
                    "max_tokens": 16384,
                    "messages": self._messages,
                    "tools": self._tools,
                }
                if self._system_prompt:
                    request["system"] = self._system_prompt

                stream = await self._client.messages.create(**request, stream=True)
                final_message: dict[str, object] = {
                    "role": "assistant",
                    "content": [],
                    "stop_reason": None,
                    "usage": {},
                }
                tool_json: dict[int, list[str]] = {}

                async for event in stream:
                    if event.type == "content_block_start":
                        block = event.content_block
                        if block.type == "text":
                            final_message["content"].append({"type": "text", "text": ""})
                        elif block.type == "thinking":
                            final_message["content"].append(
                                {"type": "thinking", "thinking": "", "signature": ""}
                            )
                        elif block.type == "tool_use":
                            logger.info("Tool call arguments started: {}", block.name)
                            final_message["content"].append(
                                {"type": "tool_use", "id": block.id, "name": block.name, "input": {}}
                            )
                            tool_json[event.index] = []
                            yield {
                                "type": "tool_call_start",
                                "tool_call_id": block.id,
                                "tool_name": block.name,
                                "arguments": {},
                            }
                    elif event.type == "content_block_delta":
                        block = final_message["content"][event.index]
                        if event.delta.type == "text_delta" and block["type"] == "text":
                            block["text"] += event.delta.text
                            yield {"type": "content_delta", "delta": event.delta.text}
                        elif event.delta.type == "thinking_delta" and block["type"] == "thinking":
                            block["thinking"] += event.delta.thinking
                        elif event.delta.type == "signature_delta" and block["type"] == "thinking":
                            block["signature"] = event.delta.signature
                        elif event.delta.type == "input_json_delta":
                            tool_json.setdefault(event.index, []).append(event.delta.partial_json)
                    elif event.type == "message_delta":
                        final_message["stop_reason"] = event.delta.stop_reason
                        final_message["usage"] = event.usage.model_dump()

                for index, raw_json in tool_json.items():
                    block = final_message["content"][index]
                    try:
                        block["input"] = json.loads("".join(raw_json))
                    except json.JSONDecodeError as exception:
                        logger.error("Invalid tool call JSON for {}: {}", block["name"], exception)
                        block["input"] = {"_invalid_json": str(exception)}

                logger.info("Upstream API call completed")
                usage = final_message["usage"]
                self._total_token = (
                    int(usage.get("input_tokens") or 0)
                    + int(usage.get("cache_read_input_tokens") or 0)
                    + int(usage.get("cache_creation_input_tokens") or 0)
                    + int(usage.get("output_tokens") or 0)
                )
                assistant_message = final_message
                self._messages.append(assistant_message)

                if final_message.get("stop_reason") != "tool_use":
                    break

                async for tool_event in self._execute_tools(assistant_message):
                    if tool_event["type"] == "tool_result_internal":
                        self._messages.append(tool_event["message"])
                    else:
                        yield tool_event
        except Exception:
            logger.exception("Agent reply failed")
            raise

    def get_total_token(self) -> int:
        return self._total_token

    async def _execute_tools(
        self, assistant_message: dict[str, object]
    ) -> AsyncIterator["AgentEvent | InternalToolResultEvent"]:
        result_blocks: list[dict[str, object]] = []
        content = assistant_message.get("content", [])
        if not isinstance(content, list):
            content = []

        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue

            tool_use_id = str(block.get("id", ""))
            tool_name = str(block.get("name", ""))
            tool_input = block.get("input", {})
            function = self._tool_functions.get(tool_name)
            arguments = tool_input if isinstance(tool_input, dict) else {}
            logger.info("Tool call arguments completed: {} | {}", tool_name, arguments)
            yield {
                "type": "tool_call_arguments",
                "tool_call_id": tool_use_id,
                "arguments": arguments,
            }
            logger.info("Tool call execution started: {}", tool_name)

            is_error = False
            if function is None:
                result = f"Error: unknown tool '{tool_name}'"
                is_error = True
            elif not isinstance(tool_input, dict):
                result = "Error: tool input must be an object"
                is_error = True
            else:
                try:
                    result = self._call_tool(function, tool_input)
                    is_error = self._is_tool_error(str(result))
                except Exception as exception:
                    logger.exception("Tool call failed: {}", tool_name)
                    result = f"Error executing tool '{tool_name}': {exception}"
                    is_error = True

            logger.info("Tool call execution completed: {}", tool_name)
            yield {
                "type": "tool_call_result",
                "tool_call_id": tool_use_id,
                "result": str(result),
                "is_error": is_error,
            }
            result_blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": str(result),
                    "is_error": is_error,
                }
            )

        yield {
            "type": "tool_result_internal",
            "message": {"role": "user", "content": result_blocks},
        }

    @staticmethod
    def _is_tool_error(result: str) -> bool:
        """Detect the error strings returned by local tools."""
        error_prefixes = (
            "Access denied",
            "Path does not exist",
            "Path is not",
            "Path exists but",
            "Path is outside",
            "Failed to",
            "No match found",
            "old_text",
            "All old_text",
            "Error:",
        )
        if result.startswith(error_prefixes):
            return True
        return any(f"\n{prefix}" in result for prefix in error_prefixes)

    def _call_tool(
        self, function: Callable[..., str], tool_input: dict[str, object]
    ) -> str:
        """Invoke a synchronous tool function in the active project context."""
        set_project_root(self._project_path)
        return function(**tool_input)

    @staticmethod
    def _message_to_dict(message: object) -> dict[str, object]:
        """Convert an SDK message into conversation-compatible content."""
        content: list[dict[str, object]] = []
        for block in message.content:
            if block.type == "text":
                content.append({"type": "text", "text": block.text})
            elif block.type == "thinking":
                content.append(
                    {
                        "type": "thinking",
                        "thinking": block.thinking,
                        "signature": getattr(block, "signature", ""),
                    }
                )
            elif block.type == "tool_use":
                content.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )
        return {"role": "assistant", "content": content}

    async def close(self) -> None:
        await self._client.close()

    def _build_system_prompt(self, base_prompt: str | None) -> str:
        """Add the active project path to the configured system prompt."""
        project_section = (
            "# 目前所在目录\n\n"
            f"当前工作目录是 `{self._project_path.as_posix()}`。write 和 edit 仅可操作该目录及其子目录；read、walk 以及 bash 中允许的 ls、grep、find 可访问进程权限允许的其他路径。bash 仅允许执行 ls、grep、find，且不要使用复合命令。"
        )
        if not base_prompt:
            return project_section
        lines = base_prompt.splitlines()
        if lines and lines[0].strip() == "# 目前所在目录":
            next_heading = next(
                (index for index, line in enumerate(lines[1:], start=1) if line.startswith("# ")),
                len(lines),
            )
            base_prompt = "\n".join(lines[next_heading:]).strip()
        return f"{project_section}\n\n{base_prompt}" if base_prompt else project_section

    @staticmethod
    def _read_system_prompt(path: Path | None) -> str | None:
        if path is None or not path.is_file():
            return None
        return path.read_text(encoding="utf-8").strip() or None
