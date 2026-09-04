import pytest

from app.services.llm import CompletionResult
from app.services.retitle import TitleGenerationError, generate_session_title


@pytest.mark.asyncio
async def test_generate_session_title_returns_cleaned_text():
    async def fake_chat(**kwargs):
        assert kwargs["messages"][0]["role"] == "system"
        assert "用户：韦伯" in kwargs["messages"][1]["content"]
        return CompletionResult(ok=True, text='「正当性」\n')

    title = await generate_session_title(
        base_url="https://example.com/v1",
        api_key="sk",
        model="m",
        turns=[{"role": "user", "content": "韦伯", "attachments": []}],
        chat_fn=fake_chat,
    )
    assert title == "正当性"


@pytest.mark.asyncio
async def test_generate_session_title_retries_after_context_length():
    calls = []

    async def fake_chat(**kwargs):
        calls.append(kwargs["messages"][1]["content"])
        if len(calls) == 1:
            return CompletionResult(
                ok=False,
                error='{"error":{"message":"context_length_exceeded"}}',
                status_code=400,
            )
        return CompletionResult(ok=True, text="后一轮")

    title = await generate_session_title(
        base_url="https://example.com/v1",
        api_key="sk",
        model="m",
        turns=[
            {"role": "user", "content": "早", "attachments": []},
            {"role": "assistant", "content": "回", "attachments": []},
            {"role": "user", "content": "晚", "attachments": []},
        ],
        chat_fn=fake_chat,
    )
    assert title == "后一轮"
    assert "早" in calls[0]
    assert "早" not in calls[1]
    assert "晚" in calls[1]


@pytest.mark.asyncio
async def test_generate_session_title_empty_output_raises():
    async def fake_chat(**kwargs):
        return CompletionResult(ok=True, text="   ")

    with pytest.raises(TitleGenerationError):
        await generate_session_title(
            base_url="https://example.com/v1",
            api_key="sk",
            model="m",
            turns=[{"role": "user", "content": "x", "attachments": []}],
            chat_fn=fake_chat,
        )
