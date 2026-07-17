import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Callable

from anthropic import AsyncAnthropic
from loguru import logger

from app.config import Settings
from app.tools.tool_utils import tools_from_functions
from app.tools import edit, read, walk, write


class AnthropicAgent:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncAnthropic(
            api_key=settings.API_KEY,
            base_url=settings.ANTHROPIC_URL,
        )
        self._messages: list[dict[str, object]] = []
        self._system_prompt = self._read_system_prompt(settings.SYSTEM_PROMPT_PATH)
        self._tools, self._tool_functions = tools_from_functions(
            [read, write, edit, walk]
        )

    async def reply(self, user_content: str) -> AsyncIterator[str]:
        self._messages.append({"role": "user", "content": user_content})

        try:
            while True:
                logger.info("Upstream API call started")
                request: dict[str, object] = {
                    "model": self._settings.ANTHROPIC_MODEL,
                    "max_tokens": 4096,
                    "messages": self._messages,
                    "tools": self._tools,
                }
                if self._system_prompt:
                    request["system"] = self._system_prompt

                async with self._client.messages.stream(**request) as stream:
                    async for event in stream:
                        if event.type != "content_block_delta":
                            continue
                        if event.delta.type == "text_delta":
                            yield event.delta.text
                    final_message = await stream.get_final_message()

                logger.info("Upstream API call completed")
                assistant_message = self._message_to_dict(final_message)
                self._messages.append(assistant_message)

                if final_message.stop_reason != "tool_use":
                    break

                tool_result_message = await self._execute_tools(assistant_message)
                self._messages.append(tool_result_message)
        except Exception:
            logger.exception("Agent reply failed")
            raise

    async def _execute_tools(
        self, assistant_message: dict[str, object]
    ) -> dict[str, object]:
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
            logger.info("Tool call started: {}", tool_name)

            is_error = False
            if function is None:
                result = f"Error: unknown tool '{tool_name}'"
                is_error = True
            elif not isinstance(tool_input, dict):
                result = "Error: tool input must be an object"
                is_error = True
            else:
                try:
                    result = await asyncio.to_thread(
                        self._call_tool, function, tool_input
                    )
                except Exception as exception:
                    logger.exception("Tool call failed: {}", tool_name)
                    result = f"Error executing tool '{tool_name}': {exception}"
                    is_error = True

            logger.info("Tool call completed: {}", tool_name)
            result_blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": str(result),
                    "is_error": is_error,
                }
            )

        return {"role": "user", "content": result_blocks}

    @staticmethod
    def _call_tool(
        function: Callable[..., str], tool_input: dict[str, object]
    ) -> str:
        """Invoke a synchronous tool function."""
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

    @staticmethod
    def _read_system_prompt(path: Path | None) -> str | None:
        if path is None or not path.is_file():
            return None
        return path.read_text(encoding="utf-8").strip() or None
