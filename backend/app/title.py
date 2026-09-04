from pathlib import Path


TITLE_SYSTEM_PROMPT = (
    "根据对话生成会话标题。言简意赅；与对话同一语言；"
    "不要引号、句号、不要「标题：」之类前缀；不要解释。"
)


def clean_generated_title(text: str, max_len: int = 128) -> str:
    raw = " ".join((text or "").split())
    quotes = "\"'“”‘’「」『』"
    raw = raw.strip(quotes + " \t")
    raw = " ".join(raw.split())
    return raw[:max_len]


def turns_from_messages(items: list[dict]) -> list[dict]:
    out: list[dict] = []
    for item in items:
        parts = [item.get("content") or ""]
        if item.get("role") == "user":
            for att in item.get("attachments") or []:
                if att.get("kind") == "document" and att.get("extracted_text"):
                    parts.append(att["extracted_text"])
        out.append(
            {
                "role": item["role"],
                "content": "\n".join(p for p in parts if p),
                "attachments": [],
            }
        )
    return out


def format_title_user_content(turns: list[dict]) -> str:
    labels = {"user": "用户：", "assistant": "助手："}
    lines = []
    for turn in turns:
        prefix = labels.get(turn["role"], f"{turn['role']}：")
        lines.append(f"{prefix}{turn.get('content') or ''}")
    return "\n".join(lines)


def auto_title(content: str, first_filename: str | None) -> str:
    text = " ".join((content or "").split())
    if text:
        return text[:40]
    if first_filename:
        return Path(first_filename).stem[:40]
    return "新对话"
