from pathlib import Path


def auto_title(content: str, first_filename: str | None) -> str:
    text = " ".join((content or "").split())
    if text:
        return text[:40]
    if first_filename:
        return Path(first_filename).stem[:40]
    return "新对话"
