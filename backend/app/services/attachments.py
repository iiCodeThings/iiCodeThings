from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
DOC_EXT = {
    ".txt",
    ".md",
    ".doc",
    ".docx",
    ".pdf",
    ".xls",
    ".xlsx",
    ".csv",
    ".tsv",
    ".json",
    ".jsonl",
}


class UploadRejected(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def classify(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in IMAGE_EXT:
        return "image"
    if suffix in DOC_EXT:
        return "document"
    raise UploadRejected(400, "不支持的文件类型")


def save_bytes(
    upload_dir: str, message_id: int, filename: str, data: bytes, max_bytes: int
) -> str:
    if len(data) > max_bytes:
        raise UploadRejected(400, "文件过大")
    safe = Path(filename).name
    dest_dir = Path(upload_dir) / str(message_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / safe
    dest.write_bytes(data)
    return str(dest.resolve())


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _extract_csv(path: str, suffix: str) -> str | None:
    delim = "\t" if suffix == ".tsv" else ","
    rows: list[str] = []
    with Path(path).open(encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.reader(fh, delimiter=delim):
            rows.append("\t".join(row))
    text = "\n".join(rows).strip()
    return text or None


def _extract_json(path: str, suffix: str) -> str | None:
    raw = _read_text(path)
    if suffix == ".jsonl":
        lines = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                lines.append(json.dumps(json.loads(line), ensure_ascii=False))
            except json.JSONDecodeError:
                lines.append(line)
        text = "\n".join(lines).strip()
        return text or None
    try:
        return json.dumps(json.loads(raw), ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return raw or None


def _extract_xlsx(path: str) -> str | None:
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        chunks: list[str] = []
        for name in wb.sheetnames:
            ws = wb[name]
            chunks.append(f"## {name}")
            for row in ws.iter_rows(values_only=True):
                cells = ["" if c is None else str(c) for c in row]
                if any(cells):
                    chunks.append("\t".join(cells))
        text = "\n".join(chunks).strip()
        return text or None
    finally:
        wb.close()


def _extract_xls(path: str) -> str | None:
    import xlrd

    book = xlrd.open_workbook(path)
    chunks: list[str] = []
    for sheet in book.sheets():
        chunks.append(f"## {sheet.name}")
        for r in range(sheet.nrows):
            cells = ["" if c is None else str(c) for c in sheet.row_values(r)]
            if any(cells):
                chunks.append("\t".join(cells))
    text = "\n".join(chunks).strip()
    return text or None


def _extract_pdf(path: str) -> str | None:
    reader = PdfReader(path)
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    text = "\n\n".join(p for p in pages if p).strip()
    return text or None


def extract_text(path: str, suffix: str) -> str | None:
    suffix = suffix.lower()
    try:
        if suffix in {".txt", ".md"}:
            return _read_text(path)
        if suffix in {".csv", ".tsv"}:
            return _extract_csv(path, suffix)
        if suffix in {".json", ".jsonl"}:
            return _extract_json(path, suffix)
        if suffix == ".xlsx":
            return _extract_xlsx(path)
        if suffix == ".xls":
            return _extract_xls(path)
        if suffix == ".pdf":
            return _extract_pdf(path)
        if suffix == ".docx":
            return "\n".join(p.text for p in Document(path).paragraphs)
        if suffix == ".doc":
            try:
                proc = subprocess.run(
                    ["antiword", path], capture_output=True, timeout=30, check=False
                )
            except FileNotFoundError:
                return None
            if proc.returncode != 0:
                return None
            return proc.stdout.decode("utf-8", errors="replace")
        return None
    except Exception:
        return None
