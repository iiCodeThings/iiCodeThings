from app.title import auto_title


def test_auto_title_from_content():
    assert auto_title("hello\nworld " + "x" * 50, None) == ("hello world " + "x" * 50)[:40]


def test_auto_title_from_filename():
    assert auto_title("  ", "notes.md") == "notes"
