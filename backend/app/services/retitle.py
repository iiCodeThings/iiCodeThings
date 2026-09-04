from __future__ import annotations

from app.services.context import drop_oldest_turn, is_context_length_error
from app.services.llm import CompletionResult, chat_completion
from app.title import TITLE_SYSTEM_PROMPT, clean_generated_title, format_title_user_content


class TitleGenerationError(Exception):
    pass


async def generate_session_title(
    *,
    base_url: str,
    api_key: str,
    model: str,
    turns: list[dict],
    chat_fn=chat_completion,
) -> str:
    items = [dict(t) for t in turns]
    while True:
        messages = [
            {"role": "system", "content": TITLE_SYSTEM_PROMPT},
            {"role": "user", "content": format_title_user_content(items)},
        ]
        result: CompletionResult = await chat_fn(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=messages,
        )
        if not result.ok:
            if is_context_length_error(result.status_code or 0, result.error) and len(items) > 1:
                items = drop_oldest_turn(items)
                continue
            raise TitleGenerationError(result.error or "生成标题失败")
        cleaned = clean_generated_title(result.text)
        if not cleaned:
            raise TitleGenerationError("模型未返回标题")
        return cleaned
