from collections.abc import AsyncIterator


class OpenAIAdaptor:
    async def text_deltas(self, events: AsyncIterator[object]) -> AsyncIterator[str]:
        """Extract text deltas from OpenAI streaming response."""
        async for chunk in events:
            if hasattr(chunk, "choices") and chunk.choices:
                choice = chunk.choices[0]
                if hasattr(choice, "delta"):
                    delta = choice.delta
                    if hasattr(delta, "content") and delta.content:
                        yield delta.content
