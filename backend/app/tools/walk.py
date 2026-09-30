from pathlib import Path

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".eggs",
    "build",
    "dist",
    ".egg-info",
}


def _should_skip_directory(name: str) -> bool:
    """Check whether a directory should be shown without its contents."""
    return name.startswith(".") or name in IGNORE_DIRS


def _tree_lines(directory: Path, prefix: str, lines: list[str]) -> None:
    """Recursively collect tree-formatted lines."""
    try:
        entries = sorted(
            directory.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower())
        )
    except (PermissionError, OSError):
        return

    visible = [entry for entry in entries if entry.is_dir() or not entry.name.startswith(".")]
    for index, child in enumerate(visible):
        is_last = index == len(visible) - 1
        connector = "└── " if is_last else "├── "
        suffix = "/" if child.is_dir() else ""
        lines.append(f"{prefix}{connector}{child.name}{suffix}")
        if child.is_dir() and not _should_skip_directory(child.name):
            extension = "    " if is_last else "│   "
            _tree_lines(child, prefix + extension, lines)


def walk(path: str) -> str:
    """Walk a directory recursively and show all dirs and files as a tree.

    Shows directories starting with '.' (such as .git and .venv) but not their contents; use ls or other commands to inspect them if needed. Other common noise directories (such as __pycache__ and node_modules) are also shown without contents. Files starting with '.' are omitted.

    Args:
        path: Full absolute path to the directory, e.g. 'D:/projects/src' or '/home/user'
    """
    directory = Path(path)
    if not directory.exists():
        return f"Path does not exist: {path}"
    if not directory.is_dir():
        return f"Path is not a directory: {path}"

    lines = [directory.as_posix() + "/"]
    _tree_lines(directory, "", lines)
    if len(lines) == 1:
        return f"{path} is an empty directory (or contains only hidden files)."
    return "\n".join(lines)
