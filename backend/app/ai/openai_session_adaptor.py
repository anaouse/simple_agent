import json
from datetime import UTC, datetime
from uuid import uuid4

from app.models import Attachment, ChatMessage, TextChatMessage, ToolChatMessage
from app.tools.read_picture import picture_result


class OpenAISessionAdaptor:
    @staticmethod
    def to_openai(messages: list[ChatMessage]) -> list[dict[str, object]]:
        """Convert persisted display nodes into OpenAI conversation messages."""
        openai_messages: list[dict[str, object]] = []
        pending_tool_calls: list[dict[str, object]] = []
        pending_tool_results: list[dict[str, object]] = []
        pending_image_messages: list[dict[str, object]] = []
        assistant_content = ""

        def flush_assistant() -> None:
            nonlocal assistant_content
            if assistant_content or pending_tool_calls:
                message: dict[str, object] = {"role": "assistant"}
                if assistant_content:
                    message["content"] = assistant_content
                if pending_tool_calls:
                    message["tool_calls"] = list(pending_tool_calls)
                openai_messages.append(message)
                assistant_content = ""
                pending_tool_calls.clear()

        def flush_tool_results() -> None:
            if pending_tool_results:
                openai_messages.extend(pending_tool_results)
                pending_tool_results.clear()
            if pending_image_messages:
                openai_messages.extend(pending_image_messages)
                pending_image_messages.clear()

        for message in messages:
            if message.role == "user":
                flush_assistant()
                flush_tool_results()
                openai_messages.append(
                    OpenAISessionAdaptor.build_user_message(message.content, message.attachments)
                )
            elif message.role == "assistant":
                flush_tool_results()
                assistant_content += message.content
            else:
                flush_tool_results()
                pending_tool_calls.append(
                    {
                        "id": message.id,
                        "type": "function",
                        "function": {
                            "name": message.tool_name,
                            "arguments": json.dumps(message.arguments),
                        },
                    }
                )
                flush_assistant()
                tool_message, image_message = OpenAISessionAdaptor.build_tool_result(
                    message.id, message.tool_name, message.result, message.status == "error"
                )
                pending_tool_results.append(tool_message)
                if image_message is not None:
                    pending_image_messages.append(image_message)

        flush_assistant()
        flush_tool_results()
        return openai_messages

    @staticmethod
    def build_tool_result(
        tool_id: str, tool_name: str, result: str, is_error: bool = False
    ) -> tuple[dict[str, object], dict[str, object] | None]:
        image = picture_result(tool_name, result, is_error)
        tool_message: dict[str, object] = {
            "role": "tool", "tool_call_id": tool_id, "content": result,
        }
        if image is None:
            return tool_message, None
        description = f"Image read by read_picture (tool call {tool_id}): {image.get('path', '')}"
        tool_message["content"] = description + "; image content follows."
        image_message = OpenAISessionAdaptor.build_user_message(
            description,
            [Attachment(media_type=image["media_type"], data=image["data"])],
        )
        return tool_message, image_message

    @staticmethod
    def build_user_message(
        content: str, attachments: list[Attachment] | None
    ) -> dict[str, object]:
        if not attachments:
            return {"role": "user", "content": content}
        parts: list[dict[str, object]] = []
        if content:
            parts.append({"type": "text", "text": content})
        for attachment in attachments:
            parts.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{attachment.media_type};base64,{attachment.data}"
                    },
                }
            )
        return {"role": "user", "content": parts}

    @staticmethod
    def from_openai(messages: list[dict[str, object]]) -> list[ChatMessage]:
        """Convert OpenAI conversation messages into persisted display nodes."""
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
            elif role == "assistant":
                if isinstance(content, str) and content:
                    result.append(
                        TextChatMessage(
                            id=str(uuid4()),
                            parent_message_id=round_id or None,
                            role="assistant",
                            content=content,
                            status="complete",
                            created_at=created_at,
                        )
                    )
                tool_calls = message.get("tool_calls")
                if isinstance(tool_calls, list):
                    for tool_call in tool_calls:
                        if not isinstance(tool_call, dict):
                            continue
                        tool_id = str(tool_call.get("id", uuid4()))
                        function = tool_call.get("function", {})
                        if not isinstance(function, dict):
                            continue

                        arguments_str = function.get("arguments", "{}")
                        try:
                            arguments = json.loads(str(arguments_str))
                        except json.JSONDecodeError:
                            arguments = {}
                        node = ToolChatMessage(
                            id=tool_id,
                            parent_message_id=round_id,
                            role="tool",
                            tool_name=str(function.get("name", "")),
                            arguments=arguments if isinstance(arguments, dict) else {},
                            result="",
                            status="streaming",
                            created_at=created_at,
                        )
                        result.append(node)
                        tool_nodes[tool_id] = node
            elif role == "tool":
                tool_id = str(message.get("tool_call_id", ""))
                node = tool_nodes.get(tool_id)
                if node is not None:
                    node.result = str(message.get("content", ""))
                    node.status = "complete"

        return result
