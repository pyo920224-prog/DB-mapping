from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "hearing_pdf"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
TEXT_DIR = INTERIM_DIR / "hearing_pdf_texts"
DOCUMENTS_CSV = INTERIM_DIR / "hearing_pdf_documents.csv"
PAGES_CSV = INTERIM_DIR / "hearing_pdf_pages.csv"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_text(text: str) -> str:
    lines = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        stripped = " ".join(line.split())
        if stripped:
            lines.append(stripped)
    return "\n".join(lines)


def doc_id_for(path: Path) -> str:
    stem = path.stem.lower()
    normalized = "".join(char if char.isalnum() else "_" for char in stem)
    normalized = "_".join(part for part in normalized.split("_") if part)
    return f"hearing_pdf_{normalized}"


def extract_pdf(path: Path) -> tuple[dict[str, object], list[dict[str, object]], str]:
    doc_id = doc_id_for(path)
    pages: list[dict[str, object]] = []
    error = ""

    try:
        reader = PdfReader(str(path))
        page_count = len(reader.pages)
        for index, page in enumerate(reader.pages, start=1):
            try:
                text = clean_text(page.extract_text() or "")
            except Exception as exc:  # noqa: BLE001
                text = ""
                error = f"{type(exc).__name__}: {exc}"
            pages.append(
                {
                    "doc_id": doc_id,
                    "page_no": index,
                    "text": text,
                    "char_count": len(text),
                }
            )
    except Exception as exc:  # noqa: BLE001
        page_count = 0
        error = f"{type(exc).__name__}: {exc}"

    full_text = "\n\n".join(page["text"] for page in pages if page["text"])
    doc = {
        "doc_id": doc_id,
        "source_type": "hearing_pdf",
        "title": path.stem,
        "file_name": path.name,
        "file_path": str(path.relative_to(PROJECT_ROOT)),
        "file_size": path.stat().st_size,
        "sha256": file_sha256(path),
        "page_count": page_count,
        "char_count": len(full_text),
        "needs_ocr": len(full_text) < 100,
        "extraction_error": error,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }
    return doc, pages, full_text


def extract_txt(path: Path) -> tuple[dict[str, object], list[dict[str, object]], str]:
    doc_id = doc_id_for(path)
    text = ""
    error = ""
    for encoding in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            text = clean_text(path.read_text(encoding=encoding))
            break
        except UnicodeDecodeError:
            continue
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
            break

    pages = [{"doc_id": doc_id, "page_no": 1, "text": text, "char_count": len(text)}]
    doc = {
        "doc_id": doc_id,
        "source_type": "hearing_txt",
        "title": path.stem,
        "file_name": path.name,
        "file_path": str(path.relative_to(PROJECT_ROOT)),
        "file_size": path.stat().st_size,
        "sha256": file_sha256(path),
        "page_count": 1,
        "char_count": len(text),
        "needs_ocr": False,
        "extraction_error": error,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }
    return doc, pages, text


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    TEXT_DIR.mkdir(parents=True, exist_ok=True)

    source_files = sorted(
        [
            path
            for path in RAW_DIR.iterdir()
            if path.is_file() and path.suffix.lower() in {".pdf", ".txt"}
        ],
        key=lambda path: path.name,
    )

    documents: list[dict[str, object]] = []
    pages: list[dict[str, object]] = []

    for path in source_files:
        if path.suffix.lower() == ".pdf":
            doc, doc_pages, full_text = extract_pdf(path)
        else:
            doc, doc_pages, full_text = extract_txt(path)

        documents.append(doc)
        pages.extend(doc_pages)
        (TEXT_DIR / f"{doc['doc_id']}.txt").write_text(full_text, encoding="utf-8")

    write_csv(
        DOCUMENTS_CSV,
        documents,
        [
            "doc_id",
            "source_type",
            "title",
            "file_name",
            "file_path",
            "file_size",
            "sha256",
            "page_count",
            "char_count",
            "needs_ocr",
            "extraction_error",
            "extracted_at",
        ],
    )
    write_csv(PAGES_CSV, pages, ["doc_id", "page_no", "text", "char_count"])

    print(f"Processed files: {len(documents)}")
    print(f"Documents CSV: {DOCUMENTS_CSV}")
    print(f"Pages CSV: {PAGES_CSV}")
    print(f"Text files: {TEXT_DIR}")


if __name__ == "__main__":
    main()
