import base64
import io
import json
import warnings
from pathlib import Path

from PIL import Image


SUPPORTED_FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg", "GIF": "image/gif", "WEBP": "image/webp"}


def read_picture(path: str) -> str:
    """Read an image file so the model can inspect its visual content.

    Supports PNG, JPEG, GIF and WebP. Image data is stored as base64 in
    conversation history and sent as image content, not plain base64 text.

    Args:
        path: Full absolute path to the image file to read

    Returns:
        A JSON image result containing its path, media type and base64 data,
        or an error message if the path is invalid or image decoding fails.
    """
    candidate = Path(path)
    if not candidate.is_absolute():
        return f"Error: image path must be absolute: {path}"
    if not candidate.exists():
        return f"Path does not exist: {path}"
    if not candidate.is_file():
        return f"Path is not a file: {path}"
    try:
        data = candidate.read_bytes()
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                media_type = SUPPORTED_FORMATS.get(image.format)
                if media_type is None:
                    return "Error: unsupported image format; use PNG, JPEG, GIF or WebP"
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                image.load()
        return json.dumps({
            "type": "read_picture",
            "path": path,
            "media_type": media_type,
            "data": base64.b64encode(data).decode("ascii"),
        }, ensure_ascii=False)
    except Exception as exception:
        return f"Failed to read image: {exception}"


def picture_result(tool_name: str, result: str, is_error: bool = False) -> dict | None:
    """Recognize a successful persisted read_picture result."""
    if tool_name != "read_picture" or is_error:
        return None
    try:
        image = json.loads(result)
    except (ValueError, TypeError):
        return None
    if (
        isinstance(image, dict)
        and image.get("type") == "read_picture"
        and image.get("media_type") in SUPPORTED_FORMATS.values()
        and isinstance(image.get("data"), str)
        and image["data"]
    ):
        return image
    return None
