from __future__ import annotations

import base64
from pathlib import Path


def is_context_length_error(status_code: int, body_text: str) -> bool:
    if status_code not in {400, 413}:
        return False
    lowered = body_text.lower()
    return (
        "context_length" in lowered
        or "too many tokens" in lowered
        or "maximum context" in lowered
    )


def drop_oldest_turn(items: list[dict]) -> list[dict]:
    if len(items) <= 1:
        return items
    rest = items[1:]
    if rest and rest[0]["role"] == "assistant" and len(rest) > 1:
        rest = rest[1:]
    return rest


def _user_text(item: dict) -> str:
    parts = [item.get("content") or ""]
    for att in item.get("attachments") or []:
        if att.get("kind") == "document" and att.get("extracted_text"):
            parts.append(att["extracted_text"])
    return "\n".join(p for p in parts if p)


def _image_data_url(path: str) -> str:
    raw = Path(path).read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    suffix = Path(path).suffix.lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(suffix, "png")
    return f"data:image/{mime};base64,{b64}"


def build_openai_messages(items: list[dict]) -> list[dict]:
    out: list[dict] = []
    for item in items:
        if item["role"] == "assistant":
            out.append({"role": "assistant", "content": item.get("content") or ""})
            continue
        text = _user_text(item)
        images = [
            a
            for a in (item.get("attachments") or [])
            if a.get("kind") == "image" and a.get("storage_path")
        ]
        if not images:
            out.append({"role": "user", "content": text})
            continue
        content: list[dict] = [{"type": "text", "text": text or " "}]
        for img in images:
            content.append(
                {"type": "image_url", "image_url": {"url": _image_data_url(img["storage_path"])}}
            )
        out.append({"role": "user", "content": content})
    return out
