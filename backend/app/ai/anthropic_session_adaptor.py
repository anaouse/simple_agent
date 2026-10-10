from datetime import UTC, datetime
from uuid import uuid4

from app.models import ChatMessage, TextChatMessage, ToolChatMessage
from app.tools.read_picture import picture_result


class AnthropicSessionAdaptor:
    @staticmethod
    def to_anthropic(messages: list[ChatMessage]) -> list[dict[str, object]]:
        """Convert persisted display nodes into Anthropic conversation messages."""
        anthropic_messages: list[dict[str, object]] = []
        pending_assistant: list[dict[str, object]] = []
        pending_tool_results: list[dict[str, object]] = []

        def flush_assistant() -> None:
            if pending_assistant:
                anthropic_messages.append(
                    {"role": "assistant", "content": list(pending_assistant)}
                )
                pending_assistant.clear()

        def flush_tool_results() -> None:
            if pending_tool_results:
                anthropic_messages.append(
                    {"role": "user", "content": list(pending_tool_results)}
                )
                pending_tool_results.clear()

        for message in messages:
            if message.role == "user":
                flush_assistant()
                flush_tool_results()
                if message.attachments:
                    blocks: list[dict[str, object]] = []
                    if message.content:
                        blocks.append({"type": "text", "text": message.content})
                    for attachment in message.attachments:
                        blocks.append(
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": attachment.media_type,
                                    "data": attachment.data,
                                },
                            }
                        )
                    anthropic_messages.append({"role": "user", "content": blocks})
                else:
                    anthropic_messages.append(
                        {"role": "user", "content": message.content}
                    )
            elif message.role == "assistant":
                flush_tool_results()
                pending_assistant.append({"type": "text", "text": message.content})
            else:
                flush_tool_results()
                pending_assistant.append(
                    {
                        "type": "tool_use",
                        "id": message.id,
                        "name": message.tool_name,
                        "input": message.arguments,
                    }
                )
                flush_assistant()
                pending_tool_results.append(
                    AnthropicSessionAdaptor.build_tool_result(
                        message.id, message.tool_name, message.result, message.status == "error"
                    )
                )

        flush_assistant()
        flush_tool_results()
        return anthropic_messages

    @staticmethod
    def build_tool_result(
        tool_id: str, tool_name: str, result: str, is_error: bool = False
    ) -> dict[str, object]:
        image = picture_result(tool_name, result, is_error)
        content: str | list[dict[str, object]] = result
        if image is not None:
            content = [
                {"type": "text", "text": f"Image read from: {image.get('path', '')}"},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image["media_type"],
                        "data": image["data"],
                    },
                },
            ]
        return {
            "type": "tool_result", "tool_use_id": tool_id,
            "content": content, "is_error": is_error,
        }

    @staticmethod
    def from_anthropic(messages: list[dict[str, object]]) -> list[ChatMessage]:
        """Convert Anthropic conversation messages into persisted display nodes."""
        result: list[ChatMessage] = []
        tool_nodes: dict[str, ToolChatMessage] = {}
        round_id = ""

        for message in messages:
            role = message.get("role")
            content = message.get("content")
            created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            if role == "user" and isinstance(content, str):
                round_id = str(uuid4())
                result.append(
                    TextChatMessage(
                        id=str(uuid4()),
                        role="user",
                        content=content,
                        status="complete",
                        created_at=created_at,
                    )
                )
                continue
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                block_type = block.get("type")
                if role == "assistant" and block_type == "text":
                    result.append(
                        TextChatMessage(
                            id=str(uuid4()),
                            parent_message_id=round_id or None,
                            role="assistant",
                            content=str(block.get("text", "")),
                            status="complete",
                            created_at=created_at,
                        )
                    )
                elif role == "assistant" and block_type == "tool_use":
                    tool_id = str(block.get("id", uuid4()))
                    arguments = block.get("input", {})
                    node = ToolChatMessage(
                        id=tool_id,
                        parent_message_id=round_id,
                        role="tool",
                        tool_name=str(block.get("name", "")),
                        arguments=arguments if isinstance(arguments, dict) else {},
                        result="",
                        status="streaming",
                        created_at=created_at,
                    )
                    result.append(node)
                    tool_nodes[tool_id] = node
                elif role == "user" and block_type == "tool_result":
                    tool_id = str(block.get("tool_use_id", ""))
                    node = tool_nodes.get(tool_id)
                    if node is not None:
                        node.result = str(block.get("content", ""))
                        node.status = "error" if block.get("is_error") else "complete"

        return result
