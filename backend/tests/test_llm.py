import httpx
import pytest

from app.services.llm import stream_chat_completion


@pytest.mark.asyncio
async def test_stream_chat_completion_reasoning_delta_done():
    sse_body = (
        'data: {"choices":[{"delta":{"reasoning_content":"think","content":"hi"}}]}\n'
        "\n"
        "data: [DONE]\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path.endswith("/chat/completions")
        assert request.headers.get("Authorization") == "Bearer test-key"
        return httpx.Response(
            200,
            content=sse_body.encode("utf-8"),
            headers={"Content-Type": "text/event-stream"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        events = [
            event
            async for event in stream_chat_completion(
                base_url="https://api.example.com/v1",
                api_key="test-key",
                model="gpt-test",
                messages=[{"role": "user", "content": "hello"}],
                client=client,
            )
        ]

    assert [(e.kind, e.text) for e in events] == [
        ("reasoning", "think"),
        ("delta", "hi"),
        ("done", ""),
    ]


@pytest.mark.asyncio
async def test_stream_chat_completion_timeout_yields_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        events = [
            event
            async for event in stream_chat_completion(
                base_url="https://api.example.com/v1",
                api_key="test-key",
                model="gpt-test",
                messages=[{"role": "user", "content": "hello"}],
                client=client,
            )
        ]

    assert len(events) == 1
    assert events[0].kind == "error"
    assert events[0].text
