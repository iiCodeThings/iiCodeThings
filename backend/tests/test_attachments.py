import pytest

from app.services.attachments import UploadRejected, classify, extract_text, save_bytes


def test_classify_and_reject():
    assert classify("a.PNG") == "image"
    assert classify("b.md") == "document"
    with pytest.raises(UploadRejected) as ei:
        classify("x.exe")
    assert ei.value.status_code == 400


def test_save_rejects_oversize(tmp_path):
    with pytest.raises(UploadRejected) as ei:
        save_bytes(str(tmp_path), 1, "a.txt", b"hello", max_bytes=3)
    assert ei.value.status_code == 400


def test_extract_txt(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello 社会学", encoding="utf-8")
    assert extract_text(str(p), ".txt") == "hello 社会学"


def test_extract_bad_docx_returns_none(tmp_path):
    p = tmp_path / "bad.docx"
    p.write_bytes(b"not a zip")
    assert extract_text(str(p), ".docx") is None
