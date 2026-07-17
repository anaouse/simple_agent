from collections.abc import AsyncIterator
from pathlib import Path

from anthropic import AsyncAnthropic
from loguru import logger

from app.ai.anthropic_adaptor import AnthropicAdaptor
from app.config import Settings


class AnthropicAgent:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncAnthropic(
            api_key=settings.API_KEY,
            base_url=settings.ANTHROPIC_URL,
        )
        self._adaptor = AnthropicAdaptor()
        self._messages: list[dict[str, str]] = []
        self._system_prompt = self._read_system_prompt(settings.SYSTEM_PROMPT_PATH)

    async def reply(self, user_content: str) -> AsyncIterator[str]:
        self._messages.append({"role": "user", "content": user_content})
        assistant_content = ""
        logger.info("Upstream API call started")

        try:
            request = {
                "model": self._settings.ANTHROPIC_MODEL,
                "max_tokens": 4096,
                "messages": self._messages,
            }
            if self._system_prompt:
                request["system"] = self._system_prompt

            async with self._client.messages.stream(**request) as stream:
                async for delta in self._adaptor.text_deltas(stream):
                    assistant_content += delta
                    yield delta

            self._messages.append({"role": "assistant", "content": assistant_content})
            logger.info("Upstream API call completed")
        except Exception:
            logger.exception("Upstream API call failed")
            raise

    async def close(self) -> None:
        await self._client.close()

    @staticmethod
    def _read_system_prompt(path: Path | None) -> str | None:
        if path is None or not path.is_file():
            return None
        return path.read_text(encoding="utf-8").strip() or None
