from contextvars import ContextVar
from pathlib import Path

SENSITIVE_NAMES = {".env"}
_project_root: ContextVar[Path | None] = ContextVar("project_root", default=None)


def set_project_root(path: Path) -> None:
    """Set the active project root for the current agent context."""
    _project_root.set(path.resolve())


def get_project_root() -> Path | None:
    """Return the active project root for the current agent context."""
    return _project_root.get()


def ensure_not_sensitive(path: str | Path) -> str | None:
    """Reject paths containing a sensitive file or directory name."""
    candidate = Path(path)
    for part in candidate.parts:
        if part in SENSITIVE_NAMES:
            return f"Access denied - sensitive name '{part}' matched in path: {path}"
    return None


def ensure_in_project(path: str | Path) -> str | None:
    """Ensure that a target is inside the active project directory."""
    error = ensure_not_sensitive(path)
    if error:
        return error

    project_root = _project_root.get()
    if project_root is None:
        return "Access denied - no active project"

    candidate = Path(path).resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError:
        return f"Path is outside the active project directory: {path}"
    return None
