from pathlib import Path

from watchfiles import Change, awatch

from app.models import ProjectFileEntry, ProjectFilesEvent

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
}
ALLOW_DOT_DIRS = {".idle"}


class ProjectFileIndex:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.entries = self._scan()

    def refresh(self) -> ProjectFilesEvent:
        self.entries = self._scan()
        return self.event()

    def event(self) -> ProjectFilesEvent:
        return ProjectFilesEvent(entries=self.entries)

    def watch_filter(self, change: Change, changed_path: str) -> bool:
        try:
            relative = Path(changed_path).relative_to(self.root)
        except ValueError:
            return False
        return not self._is_ignored(relative)

    async def changes(self):
        async for _ in awatch(self.root, watch_filter=self.watch_filter):
            yield self.refresh()

    def _scan(self) -> list[ProjectFileEntry]:
        entries: list[ProjectFileEntry] = []
        for directory, dirnames, filenames in self.root.walk():
            relative_directory = directory.relative_to(self.root)
            dirnames[:] = [
                name
                for name in dirnames
                if not self._is_ignored(relative_directory / name)
            ]
            for name in dirnames:
                entries.append(
                    ProjectFileEntry(
                        path=(relative_directory / name).as_posix() + "/",
                        absolute_path=(directory / name).as_posix() + "/",
                        is_directory=True,
                    )
                )
            for name in filenames:
                relative = relative_directory / name
                if not self._is_ignored(relative):
                    entries.append(
                        ProjectFileEntry(
                            path=relative.as_posix(),
                            absolute_path=(directory / name).as_posix(),
                            is_directory=False,
                        )
                    )
        entries.sort(key=lambda entry: (not entry.is_directory, entry.path.lower()))
        return entries

    def _is_ignored(self, relative: Path) -> bool:
        for part in relative.parts:
            if part in IGNORE_DIRS:
                return True
            if part.startswith(".") and part not in ALLOW_DOT_DIRS:
                return True
        return False
