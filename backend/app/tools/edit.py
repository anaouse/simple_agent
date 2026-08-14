import difflib
from pathlib import Path

from app.tools.security import ensure_in_project


def closest_match_context(content: str, old_text: str) -> str:
    lines = content.splitlines()
    target = old_text.splitlines()[0]
    if not lines:
        return "The file is empty."

    closest_index = max(
        range(len(lines)),
        key=lambda index: difflib.SequenceMatcher(None, target, lines[index]).ratio(),
    )
    start = max(0, closest_index - 2)
    end = min(len(lines), closest_index + 3)
    context = "\n".join(f"{line_number + 1}: {lines[line_number]}" for line_number in range(start, end))
    return f"Closest match to the first line is near line {closest_index + 1}:\n{context}"


def edit(path: str, old_text: str, new_text: str) -> str:
    """Precisely replace a single segment of text in a file.

    Only operates on files within the current working directory; out-of-scope paths will be rejected.
    old_text must have a unique match in the file.

    Args:
        path: Full absolute path to the file, e.g. 'D:/projects/main.py'
        old_text: The exact text to be replaced; it must be uniquely matched
        new_text: The replacement text
    """
    error = ensure_in_project(path)
    if error:
        return error
    if not isinstance(old_text, str) or not isinstance(new_text, str):
        return "old_text and new_text must be strings"
    if old_text == "":
        return "old_text must not be empty"

    old_text = old_text.replace("\r\n", "\n").replace("\r", "\n")
    new_text = new_text.replace("\r\n", "\n").replace("\r", "\n")

    candidate = Path(path)
    if not candidate.exists():
        return f"Path does not exist: {path}"
    if not candidate.is_file():
        return f"Path is not a file: {path}"
    try:
        with candidate.open("r", encoding="utf-8", newline=None) as file:
            replaced = file.read()
    except Exception as exception:
        return f"Failed to read file: {exception}"

    count = replaced.count(old_text)
    if count == 0:
        return (
            f"No match found for old_text in the file. "
            f"{closest_match_context(replaced, old_text)}"
        )
    if count > 1:
        return (
            f"old_text matched {count} occurrences, not unique. "
            "Expand it (include surrounding line context) to make it unique."
        )
    replaced = replaced.replace(old_text, new_text)

    try:
        with candidate.open("w", encoding="utf-8", newline="\n") as file:
            file.write(replaced)
        return f"Successfully applied edit to file: {path}"
    except Exception as exception:
        return f"Failed to write file: {exception}"
