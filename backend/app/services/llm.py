from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx


@dataclass
class StreamEvent:
    kind: str
    text: str = ""
    status_code: int | None = None


def _join_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + path


async def stream_chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    timeout: float = 120.0,
    client: httpx.AsyncClient | None = None,
) -> AsyncIterator[StreamEvent]:
    own = client is None
    client = client or httpx.AsyncClient(timeout=timeout)
    url = _join_url(base_url, "/chat/completions")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "stream": True}
    try:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            if resp.status_code != 200:
                body = (await resp.aread())[:500].decode("utf-8", errors="replace")
                yield StreamEvent(kind="error", text=body, status_code=resp.status_code)
                return
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    yield StreamEvent(kind="done")
                    return
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = (parsed.get("choices") or [{}])[0].get("delta") or {}
                reasoning = delta.get("reasoning_content") or delta.get("reasoning")
                if reasoning:
                    yield StreamEvent(kind="reasoning", text=reasoning)
                content = delta.get("content")
                if content:
                    yield StreamEvent(kind="delta", text=content)
            yield StreamEvent(kind="done")
    except httpx.TimeoutException:
        yield StreamEvent(kind="error", text="上游请求超时")
    except httpx.RequestError as exc:
        yield StreamEvent(kind="error", text=f"上游连接失败：{exc}")
    finally:
        if own:
            await client.aclose()
