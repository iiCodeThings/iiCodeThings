import pytest

from app.services.attachments import UploadRejected, classify, extract_text, save_bytes


def test_classify_and_reject():
    assert classify("a.PNG") == "image"
    assert classify("b.md") == "document"
    assert classify("notes.pdf") == "document"
    assert classify("data.XLSX") == "document"
    assert classify("table.csv") == "document"
    assert classify("payload.json") == "document"
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


def test_extract_csv_json_xlsx(tmp_path):
    csv_path = tmp_path / "a.csv"
    csv_path.write_text("name,city\n韦伯,海德堡\n", encoding="utf-8")
    csv_text = extract_text(str(csv_path), ".csv")
    assert csv_text is not None
    assert "韦伯" in csv_text

    json_path = tmp_path / "a.json"
    json_path.write_text('{"topic":"人类学"}', encoding="utf-8")
    json_text = extract_text(str(json_path), ".json")
    assert json_text is not None
    assert "人类学" in json_text

    from openpyxl import Workbook

    xlsx_path = tmp_path / "a.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["学科", "人物"])
    ws.append(["社会学", "韦伯"])
    wb.save(xlsx_path)
    xlsx_text = extract_text(str(xlsx_path), ".xlsx")
    assert xlsx_text is not None
    assert "韦伯" in xlsx_text


def test_extract_bad_pdf_returns_none(tmp_path):
    p = tmp_path / "bad.pdf"
    p.write_bytes(b"not a pdf")
    assert extract_text(str(p), ".pdf") is None
