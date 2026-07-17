from collections.abc import AsyncIterator

from anthropic.types import RawContentBlockDeltaEvent, TextDelta
from anthropic.types.raw_message_stream_event import RawMessageStreamEvent


class AnthropicAdaptor:
    async def text_deltas(
        self, events: AsyncIterator[RawMessageStreamEvent]
    ) -> AsyncIterator[str]:
        async for event in events:
            if isinstance(event, RawContentBlockDeltaEvent) and isinstance(
                event.delta, TextDelta
            ):
                yield event.delta.text
