import json

import httpx
import pytest

from app.services.llm import chat_completion, stream_chat_completion


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


@pytest.mark.asyncio
async def test_chat_completion_reads_message_content():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert body["stream"] is False
        assert body["model"] == "gpt-test"
        assert body["messages"][0]["role"] == "user"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "韦伯与正当性"}}]},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await chat_completion(
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model="gpt-test",
            messages=[{"role": "user", "content": "hello"}],
            client=client,
        )
    assert result.ok is True
    assert result.text == "韦伯与正当性"


@pytest.mark.asyncio
async def test_chat_completion_non_200_is_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text='{"error":{"message":"context_length_exceeded"}}')

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await chat_completion(
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model="gpt-test",
            messages=[{"role": "user", "content": "hello"}],
            client=client,
        )
    assert result.ok is False
    assert result.status_code == 400
    assert "context_length" in result.error
