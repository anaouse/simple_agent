from pathlib import Path

from app.models import SkillEntry, SkillsEvent


class SkillIndex:
    def __init__(self, root: Path | None) -> None:
        self.root = root
        self.entries = self._scan()

    def refresh(self, root: Path | None) -> SkillsEvent:
        self.root = root
        self.entries = self._scan()
        return self.event()

    def event(self) -> SkillsEvent:
        return SkillsEvent(entries=self.entries)

    def _scan(self) -> list[SkillEntry]:
        if self.root is None or not self.root.is_dir():
            return []
        try:
            return [
                SkillEntry(name=child.name)
                for child in self.root.iterdir()
                if child.is_dir() and (child / "SKILL.md").is_file()
            ]
        except OSError:
            return []
