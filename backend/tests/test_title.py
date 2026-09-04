from app.title import (
    TITLE_SYSTEM_PROMPT,
    auto_title,
    clean_generated_title,
    format_title_user_content,
    turns_from_messages,
)


def test_auto_title_from_content():
    assert auto_title("hello\nworld " + "x" * 50, None) == ("hello world " + "x" * 50)[:40]


def test_auto_title_from_filename():
    assert auto_title("  ", "notes.md") == "notes"


def test_clean_generated_title_strips_quotes_and_newlines():
    assert clean_generated_title('  「韦伯与正当性」\n ') == "韦伯与正当性"
    assert clean_generated_title('"Hello"') == "Hello"
    assert clean_generated_title("   ") == ""
    assert len(clean_generated_title("字" * 200)) == 128


def test_turns_from_messages_uses_doc_text_omits_reasoning_and_images():
    turns = turns_from_messages(
        [
            {
                "role": "user",
                "content": "看这个",
                "reasoning": "should-not-appear",
                "attachments": [
                    {"kind": "document", "extracted_text": "人类学笔记"},
                    {"kind": "image", "extracted_text": None, "storage_path": "/tmp/a.png"},
                ],
            },
            {
                "role": "assistant",
                "content": "好",
                "reasoning": "internal",
                "attachments": [],
            },
        ]
    )
    blob = format_title_user_content(turns)
    assert TITLE_SYSTEM_PROMPT
    assert blob == "用户：看这个\n人类学笔记\n助手：好"
    assert "internal" not in blob
    assert "should-not-appear" not in blob
    assert "/tmp/a.png" not in blob
