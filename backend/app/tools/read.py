from pathlib import Path

MAX_LINES = 2000
TRUNCATED_HEAD = 500
TRUNCATED_TAIL = 500


def read(path: str, offset: int = 0, limit: int | None = None) -> str:
    """Read a single file.

    Args:
        path: Full absolute path to the file to read
        offset: Starting line number (1-indexed; 0 means from the beginning)
        limit: Maximum number of lines to read from the start; None means read to the end

    Returns:
        The file content, or an error message if the path is invalid.
        If the range to read exceeds 2000 lines, returns the first 500 lines
        and the last 500 lines joined by "...".
    """
    candidate = Path(path)
    if not candidate.exists():
        return f"[File: {path}]\nPath does not exist: {path}"
    if not candidate.is_file():
        return f"[File: {path}]\nPath is not a file: {path}"
    try:
        lines = candidate.read_text(encoding="utf-8").splitlines()
    except Exception as exception:
        return f"[File: {path}]\nFailed to read file: {exception}"

    total = len(lines)
    try:
        parsed_offset = int(offset) if offset is not None else 0
    except (TypeError, ValueError):
        parsed_offset = 0
    parsed_offset = max(parsed_offset, 0)
    start = parsed_offset - 1 if parsed_offset > 0 else 0
    start = min(start, total)

    try:
        parsed_limit = int(limit) if limit is not None else total - start
    except (TypeError, ValueError):
        parsed_limit = total - start
    parsed_limit = max(parsed_limit, 0)
    end = min(start + parsed_limit, total)

    header = f"[File: {path} | Lines {start + 1}-{end} / {total}]"

    count = end - start
    if count > MAX_LINES:
        head = lines[start : start + TRUNCATED_HEAD]
        tail = lines[end - TRUNCATED_TAIL : end]
        return header + "\n" + "\n".join(head) + "\n...\n" + "\n".join(tail)

    return header + "\n" + "\n".join(lines[start:end])
