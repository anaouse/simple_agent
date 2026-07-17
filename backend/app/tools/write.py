from pathlib import Path

from app.tools.security import ensure_in_project


def write(path: str, content: str) -> str:
    """Write content to a file at the specified path, overwriting if it already exists.

    Only operates on files within the current working directory; out-of-scope paths will be rejected.

    Args:
        path: Full absolute path to the file, e.g. 'D:/projects/README.md' or '/home/user/main.py'
        content: The text content to write to the file
    """
    error = ensure_in_project(path)
    if error:
        return error

    candidate = Path(path)
    if candidate.exists() and not candidate.is_file():
        return f"Path exists but is not a file: {path}"
    try:
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text(content, encoding="utf-8")
        return f"Successfully wrote to file: {path}"
    except Exception as exception:
        return f"Failed to write file: {exception}"
