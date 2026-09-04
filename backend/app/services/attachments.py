from __future__ import annotations

import subprocess
from pathlib import Path

from docx import Document

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
DOC_EXT = {".txt", ".md", ".doc", ".docx"}


class UploadRejected(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def classify(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in IMAGE_EXT:
        return "image"
    if suffix in DOC_EXT:
        return "document"
    raise UploadRejected(400, "不支持的文件类型")


def save_bytes(
    upload_dir: str, message_id: int, filename: str, data: bytes, max_bytes: int
) -> str:
    if len(data) > max_bytes:
        raise UploadRejected(400, "文件过大")
    safe = Path(filename).name
    dest_dir = Path(upload_dir) / str(message_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / safe
    dest.write_bytes(data)
    return str(dest.resolve())


def extract_text(path: str, suffix: str) -> str | None:
    suffix = suffix.lower()
    if suffix in {".txt", ".md"}:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    if suffix == ".docx":
        return "\n".join(p.text for p in Document(path).paragraphs)
    if suffix == ".doc":
        try:
            proc = subprocess.run(
                ["antiword", path], capture_output=True, timeout=30, check=False
            )
        except FileNotFoundError:
            return None
        if proc.returncode != 0:
            return None
        return proc.stdout.decode("utf-8", errors="replace")
    return None
