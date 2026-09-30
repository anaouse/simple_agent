import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Callable, Literal, TypedDict

from loguru import logger
from openai import AsyncOpenAI

from app.ai.openai_session_adaptor import OpenAISessionAdaptor
from app.config import AgentConfig, ModelConfig
from app.models import Attachment, ChatMessage
from app.tools import bash, edit, read, walk, write
from app.tools.security import set_project_root


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


class OpenAIAgent:
    def __init__(
        self, config: AgentConfig, model: ModelConfig, project_path: Path
    ) -> None:
        if model.compatible != "openai":
            raise ValueError(f"暂不支持的模型兼容格式: {model.compatible}")
        self._model = model
        self._project_path = project_path.resolve()
        set_project_root(self._project_path)
        self._client = AsyncOpenAI(
            api_key=model.api_key,
            base_url=model.url,
        )
        self._messages: list[dict[str, object]] = []
        self._total_token = 0
        base_prompt = self._read_system_prompt(config.system_prompt_path)
        self._system_prompt = self._build_system_prompt(base_prompt)
        self._tools = self._build_openai_tools()
        self._tool_functions: dict[str, Callable[..., str]] = {
            "read": read,
            "write": write,
            "edit": edit,
            "walk": walk,
            "bash": bash,
        }

    def load_session(self, messages: list[ChatMessage]) -> None:
        """Load conversation history from persisted messages."""
        self._messages = OpenAISessionAdaptor.to_openai(messages)

    async def reply(
        self, user_content: str, attachments: list[Attachment] | None = None
    ) -> AsyncIterator["AgentEvent"]:
        """Generate a reply to the user message, yielding events as they occur."""
        set_project_root(self._project_path)
        self._messages.append(
            OpenAISessionAdaptor.build_user_message(user_content, attachments)
        )

        try:
            while True:
                logger.info("Upstream API call started")
                request: dict[str, object] = {
                    "model": self._model.name,
                    "messages": self._messages,
                    "tools": self._tools,
                    "stream": True,
                    "stream_options": {"include_usage": True},
                }

                # Add system prompt as first message if exists
                messages_to_send = self._messages.copy()
                if self._system_prompt:
                    messages_to_send.insert(
                        0, {"role": "system", "content": self._system_prompt}
                    )
                request["messages"] = messages_to_send

                stream = await self._client.chat.completions.create(**request)

                # Collect streaming response
                assistant_content = ""
                tool_calls_data: dict[int, dict[str, object]] = {}
                started_tool_calls: set[int] = set()

                async for chunk in stream:
                    if chunk.usage is not None:
                        self._total_token = (
                            chunk.usage.prompt_tokens + chunk.usage.completion_tokens
                        )
                    if not chunk.choices:
                        continue

                    choice = chunk.choices[0]
                    if choice.finish_reason:
                        continue

                    delta = choice.delta

                    # Handle content delta
                    if delta.content:
                        assistant_content += delta.content
                        yield {"type": "content_delta", "delta": delta.content}

                    # Handle tool calls delta
                    if delta.tool_calls:
                        for tool_call in delta.tool_calls:
                            index = tool_call.index
                            if index not in tool_calls_data:
                                tool_calls_data[index] = {
                                    "id": tool_call.id or "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                }

                            if tool_call.id:
                                tool_calls_data[index]["id"] = tool_call.id

                            if tool_call.function:
                                function = tool_calls_data[index]["function"]
                                if not isinstance(function, dict):
                                    function = {"name": "", "arguments": ""}
                                    tool_calls_data[index]["function"] = function

                                if tool_call.function.name:
                                    function["name"] = tool_call.function.name
                                    if index not in started_tool_calls:
                                        started_tool_calls.add(index)
                                        tool_name = tool_call.function.name
                                        tool_id = str(tool_calls_data[index].get("id", ""))
                                        logger.info("Tool call arguments started: {}", tool_name)
                                        yield {
                                            "type": "tool_call_start",
                                            "tool_call_id": tool_id,
                                            "tool_name": tool_name,
                                            "arguments": {},
                                        }

                                if tool_call.function.arguments:
                                    function["arguments"] = (
                                        function.get("arguments", "") or ""
                                    ) + tool_call.function.arguments

                logger.info("Upstream API call completed")

                # Build assistant message
                assistant_message: dict[str, object] = {"role": "assistant"}
                if assistant_content:
                    assistant_message["content"] = assistant_content
                if tool_calls_data:
                    assistant_message["tool_calls"] = [
                        tool_calls_data[i] for i in sorted(tool_calls_data.keys())
                    ]

                self._messages.append(assistant_message)

                # If no tool calls, we're done
                if not tool_calls_data:
                    break

                # Execute tools
                async for tool_event in self._execute_tools(tool_calls_data):
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
        self, tool_calls_data: dict[int, dict[str, object]]
    ) -> AsyncIterator["AgentEvent | InternalToolResultEvent"]:
        """Execute tool calls and yield events."""
        for index in sorted(tool_calls_data.keys()):
            tool_call = tool_calls_data[index]
            tool_id = str(tool_call.get("id", ""))
            function_data = tool_call.get("function", {})
            if not isinstance(function_data, dict):
                continue

            tool_name = str(function_data.get("name", ""))
            arguments_str = str(function_data.get("arguments", "{}"))

            # Parse arguments
            try:
                arguments = json.loads(arguments_str)
                input_error = None
            except json.JSONDecodeError as exception:
                logger.error(
                    "Invalid tool call JSON for {}: {}\nraw arguments: {}",
                    tool_name, exception, arguments_str,
                )
                arguments = {}
                input_error = str(exception)

            function = self._tool_functions.get(tool_name)
            parsed_arguments = arguments if isinstance(arguments, dict) else {}
            logger.info("Tool call arguments completed: {} | {}", tool_name, parsed_arguments)
            yield {
                "type": "tool_call_arguments",
                "tool_call_id": tool_id,
                "arguments": parsed_arguments,
            }
            logger.info("Tool call execution started: {}", tool_name)

            is_error = False
            if function is None:
                result = f"Error: unknown tool '{tool_name}'"
                is_error = True
            elif input_error is not None:
                result = (
                    f"Error: tool '{tool_name}' received invalid JSON arguments: "
                    f"{input_error}"
                )
                is_error = True
            elif not isinstance(arguments, dict):
                result = "Error: tool arguments must be an object"
                is_error = True
            else:
                try:
                    result = self._call_tool(function, arguments)
                    is_error = self._is_tool_error(str(result))
                except Exception as exception:
                    logger.exception("Tool call failed: {}", tool_name)
                    result = f"Error executing tool '{tool_name}': {exception}"
                    is_error = True

            logger.info("Tool call execution completed: {}", tool_name)
            yield {
                "type": "tool_call_result",
                "tool_call_id": tool_id,
                "result": str(result),
                "is_error": is_error,
            }

            # Add tool result to messages
            yield {
                "type": "tool_result_internal",
                "message": {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": str(result),
                },
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

    async def close(self) -> None:
        """Close the OpenAI client."""
        await self._client.close()

    def _build_system_prompt(self, base_prompt: str | None) -> str:
        """Add the active project path to the configured system prompt."""
        project_section = f"""# Agent 内部约定

## 当前项目

当前工作目录是 `{self._project_path.as_posix()}`。

- `write` 和 `edit` 仅可操作当前项目目录及其子目录。
- `read`、`walk` 以及 `bash` 可访问进程权限允许的其他路径。

## 文件操作

- 不要使用 `rm` 命令删除文件，即使看起来没用的文件也保留着。

## 工具调用参数

工具调用参数必须是合法 JSON：所有字符串值必须用双引号包裹（如 `"old_text": "..."`），字符串内的换行必须写成 `\n`，禁止输出不带引号的裸文本。

## 公式输出

需要输出数学公式时，必须使用 Markdown 数学定界符 `$$`：行内公式和块级公式都使用 `$$` 包裹。不要使用 `\\(`、`\\)`、`\\[`、`\\]` 或单个 `$`。"""
        if not base_prompt:
            return project_section
        lines = base_prompt.splitlines()
        if lines and lines[0].strip() == "# 目前所在目录":
            next_heading = next(
                (
                    index
                    for index, line in enumerate(lines[1:], start=1)
                    if line.startswith("# ")
                ),
                len(lines),
            )
            base_prompt = "\n".join(lines[next_heading:]).strip()
        return (
            f"{project_section}\n\n{base_prompt}" if base_prompt else project_section
        )

    @staticmethod
    def _read_system_prompt(path: Path | None) -> str | None:
        """Read system prompt from file."""
        if path is None or not path.is_file():
            return None
        return path.read_text(encoding="utf-8").strip() or None

    def _build_openai_tools(self) -> list[dict[str, object]]:
        """Build OpenAI-compatible tool definitions."""
        from app.tools.tool_utils import tools_from_functions

        anthropic_tools, _ = tools_from_functions(
            [read, write, edit, walk, bash]
        )

        # Convert Anthropic tool schema to OpenAI function calling schema
        openai_tools = []
        for tool in anthropic_tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            }
            openai_tools.append(openai_tool)

        return openai_tools
