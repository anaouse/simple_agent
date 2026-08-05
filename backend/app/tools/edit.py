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


def edit(path: str, old_text: list[str], new_text: list[str]) -> str:
    """Precisely replace multiple segments of text in a file.

    Only operates on files within the current working directory; out-of-scope paths will be rejected.
    old_text and new_text must be non-empty lists of equal length. Each old_text item must have a unique match in the file.
    Replacements are applied sequentially, so old_text items must not overlap.

    Args:
        path: Full absolute path to the file, e.g. 'D:/projects/main.py'
        old_text: The exact texts to be replaced; each item must be uniquely matched
        new_text: The replacement texts, paired with old_text by index
    """
    error = ensure_in_project(path)
    if error:
        return error
    if not isinstance(old_text, list) or not isinstance(new_text, list):
        return "old_text and new_text must be lists"
    if not old_text or not new_text:
        return "old_text and new_text must be non-empty lists"
    if len(old_text) != len(new_text):
        return "old_text and new_text must contain the same number of items"
    if not all(isinstance(text, str) for text in old_text + new_text):
        return "All old_text and new_text items must be strings"
    if any(text == "" for text in old_text):
        return "old_text items must not be empty"

    old_text = [text.replace("\r\n", "\n").replace("\r", "\n") for text in old_text]
    new_text = [text.replace("\r\n", "\n").replace("\r", "\n") for text in new_text]

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

    for index, (old, new) in enumerate(zip(old_text, new_text), start=1):
        count = replaced.count(old)
        if count == 0:
            return (
                f"No match found for old_text item {index} in the file. "
                f"{closest_match_context(replaced, old)}"
            )
        if count > 1:
            return (
                f"old_text item {index} matched {count} occurrences, not unique. "
                "Expand it (include surrounding line context) to make it unique."
            )
        replaced = replaced.replace(old, new)

    try:
        with candidate.open("w", encoding="utf-8", newline="\n") as file:
            file.write(replaced)
        return f"Successfully applied {len(old_text)} edits to file: {path}"
    except Exception as exception:
        return f"Failed to write file: {exception}"
