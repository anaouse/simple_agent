from pathlib import Path

from app.tools.security import ensure_in_project

MAX_LINES = 2000
MAX_CHARS = 20_000


def _read_one(path: str, offset: int, limit: int) -> str:
    """Read one file while keeping failures local to that file."""
    error = ensure_in_project(path)
    if error:
        return f"[File: {path}]\n{error}"

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
    start = offset - 1 if offset > 0 else 0
    start = min(start, total)
    end = min(start + limit, total)
    header = f"[File: {path} | Lines {start + 1}-{end} / {total}]"
    result = "\n".join(lines[start:end])
    max_result_chars = MAX_CHARS - len(header) - 5
    if len(result) > max_result_chars:
        result = result[:max_result_chars] + (
            f"\n...[Result truncated; exceeded {MAX_CHARS} character limit. "
            "Use offset/limit to read in batches]"
        )
    return header + "\n" + result


def read(paths: list[str], offset: int = 0, limit: int | None = None) -> str:
    """Read multiple files. Each file is read and truncated independently so one failure does not affect the others.

    Args:
        paths: Full absolute paths to the files to read
        offset: Line number to start reading from in each file (1-indexed; default 0 means from the beginning)
        limit: Maximum number of lines to read from each file (None defaults to at most 2000 lines)
    """
    try:
        parsed_offset = int(offset) if offset is not None else 0
    except (TypeError, ValueError):
        parsed_offset = 0
    try:
        parsed_limit = int(limit) if limit is not None else MAX_LINES
    except (TypeError, ValueError):
        parsed_limit = MAX_LINES

    parsed_offset = max(parsed_offset, 0)
    parsed_limit = max(0, min(parsed_limit, MAX_LINES))
    results: list[str] = []
    for path in paths:
        try:
            results.append(_read_one(path, parsed_offset, parsed_limit))
        except Exception as exception:
            results.append(f"[File: {path}]\nFailed to read file: {exception}")
    return "\n\n".join(results)
