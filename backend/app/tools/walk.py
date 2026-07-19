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


def _should_ignore(name: str, is_dir: bool) -> bool:
    """Check whether an entry should be omitted."""
    return name.startswith(".") or (is_dir and name in IGNORE_DIRS)


def _tree_lines(directory: Path, prefix: str, lines: list[str]) -> None:
    """Recursively collect tree-formatted lines."""
    try:
        entries = sorted(
            directory.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower())
        )
    except (PermissionError, OSError):
        return

    visible = [
        entry for entry in entries if not _should_ignore(entry.name, entry.is_dir())
    ]
    for index, child in enumerate(visible):
        is_last = index == len(visible) - 1
        connector = "└── " if is_last else "├── "
        suffix = "/" if child.is_dir() else ""
        lines.append(f"{prefix}{connector}{child.name}{suffix}")
        if child.is_dir():
            extension = "    " if is_last else "│   "
            _tree_lines(child, prefix + extension, lines)


def walk(path: str) -> str:
    """Walk a directory recursively and show all dirs and files as a tree.

    Skips hidden entries and common noise directories (.git, __pycache__, node_modules, etc.).

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
        return f"{path} is an empty directory (or all entries are ignored)."
    return "\n".join(lines)
