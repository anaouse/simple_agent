from pathlib import Path

SENSITIVE_NAMES = {".env"}


def ensure_not_sensitive(path: str | Path) -> str | None:
    """Reject paths containing a sensitive file or directory name."""
    candidate = Path(path)
    for part in candidate.parts:
        if part in SENSITIVE_NAMES:
            return f"Access denied - sensitive name '{part}' matched in path: {path}"
    return None


def ensure_in_project(path: str | Path) -> str | None:
    """Ensure that a write target is inside the backend working directory."""
    error = ensure_not_sensitive(path)
    if error:
        return error

    candidate = Path(path).resolve()
    project_root = Path.cwd().resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError:
        return f"Path is outside the current working directory: {path}"
    return None
