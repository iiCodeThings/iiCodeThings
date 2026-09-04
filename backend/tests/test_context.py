from app.services.context import build_openai_messages, drop_oldest_turn, is_context_length_error


def test_omits_reasoning_and_adds_doc_text():
    msgs = build_openai_messages(
        [
            {
                "role": "user",
                "content": "看这个",
                "attachments": [
                    {"kind": "document", "storage_path": "", "extracted_text": "人类学笔记"}
                ],
            },
            {
                "role": "assistant",
                "content": "好",
                "reasoning": "internal chain of thought",
                "attachments": [],
            },
        ]
    )
    assert msgs[0]["role"] == "user"
    assert "人类学笔记" in msgs[0]["content"]
    assert "reasoning" not in msgs[1]


def test_drop_oldest_keeps_last():
    items = [
        {"role": "user", "content": "a", "attachments": []},
        {"role": "assistant", "content": "b", "attachments": []},
        {"role": "user", "content": "c", "attachments": [{"kind": "image"}]},
    ]
    out = drop_oldest_turn(items)
    assert out[-1]["content"] == "c"
    assert out[-1]["attachments"][0]["kind"] == "image"


def test_context_length_detect():
    assert is_context_length_error(400, '{"error":{"message":"context_length_exceeded"}}')
    assert not is_context_length_error(500, "oops")
