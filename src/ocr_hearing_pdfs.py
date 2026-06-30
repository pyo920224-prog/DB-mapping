from __future__ import annotations

import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import fitz
import pytesseract
from PIL import Image

from extract_hearing_pdf_text import DOCUMENTS_CSV, INTERIM_DIR, PROJECT_ROOT, clean_text


TESSERACT_EXE = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
TESSDATA_DIR = PROJECT_ROOT / "tessdata"
OCR_PAGES_CSV = INTERIM_DIR / "hearing_pdf_ocr_pages_corrected.csv"
OCR_DOCUMENTS_CSV = INTERIM_DIR / "hearing_pdf_ocr_documents_corrected.csv"
OCR_TEXT_DIR = INTERIM_DIR / "hearing_pdf_ocr_texts_corrected"
PROCESSED_DOCUMENTS_CSV = PROJECT_ROOT / "data" / "processed" / "hearing_documents.csv"
OCR_ROTATIONS = {
    "hearing_pdf_02_탄원서_주요내용_요약": 270,
}


def read_documents() -> list[dict[str, str]]:
    source_path = DOCUMENTS_CSV if DOCUMENTS_CSV.exists() else PROCESSED_DOCUMENTS_CSV
    with source_path.open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def ocr_page(page: fitz.Page, dpi: int, rotation: int = 0) -> str:
    pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
    if rotation:
        image = image.rotate(rotation, expand=True)
    config = "--oem 1 --psm 6"
    text = pytesseract.image_to_string(image, lang="kor", config=config)
    return clean_text(text)


def main() -> None:
    if not TESSERACT_EXE.exists():
        raise FileNotFoundError(f"Tesseract executable not found: {TESSERACT_EXE}")
    if not (TESSDATA_DIR / "kor.traineddata").exists():
        raise FileNotFoundError(f"Korean traineddata not found: {TESSDATA_DIR / 'kor.traineddata'}")

    pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_EXE)
    os.environ["TESSDATA_PREFIX"] = str(TESSDATA_DIR)
    OCR_TEXT_DIR.mkdir(parents=True, exist_ok=True)

    documents = read_documents()
    targets = [
        doc
        for doc in documents
        if doc.get("source_type") == "hearing_pdf"
        and (doc.get("needs_ocr") == "True" or doc.get("text_source") == "ocr")
    ]
    selected_doc_ids = set(sys.argv[1:])
    if selected_doc_ids:
        targets = [doc for doc in targets if doc["doc_id"] in selected_doc_ids]

    ocr_documents: list[dict[str, object]] = []
    ocr_pages: list[dict[str, object]] = []

    for doc in targets:
        doc_id = doc["doc_id"]
        pdf_path = PROJECT_ROOT / doc["file_path"]
        print(f"OCR: {pdf_path.name}")

        page_rows: list[dict[str, object]] = []
        error = ""
        try:
            with fitz.open(pdf_path) as pdf:
                for page_index, page in enumerate(pdf, start=1):
                    text = ocr_page(page, dpi=250, rotation=OCR_ROTATIONS.get(doc_id, 0))
                    row = {
                        "doc_id": doc_id,
                        "page_no": page_index,
                        "text": text,
                        "char_count": len(text),
                    }
                    page_rows.append(row)
                    ocr_pages.append(row)
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"

        full_text = "\n\n".join(row["text"] for row in page_rows if row["text"])
        (OCR_TEXT_DIR / f"{doc_id}.txt").write_text(full_text, encoding="utf-8")

        ocr_documents.append(
            {
                "doc_id": doc_id,
                "title": doc["title"],
                "file_name": doc["file_name"],
                "page_count": doc["page_count"],
                "ocr_char_count": len(full_text),
                "ocr_done": len(full_text) > 0 and not error,
                "ocr_error": error,
                "ocr_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    write_csv(
        OCR_DOCUMENTS_CSV,
        ocr_documents,
        [
            "doc_id",
            "title",
            "file_name",
            "page_count",
            "ocr_char_count",
            "ocr_done",
            "ocr_error",
            "ocr_at",
        ],
    )
    write_csv(OCR_PAGES_CSV, ocr_pages, ["doc_id", "page_no", "text", "char_count"])

    print(f"OCR documents: {len(ocr_documents)}")
    print(f"OCR pages: {len(ocr_pages)}")
    print(f"OCR documents CSV: {OCR_DOCUMENTS_CSV}")
    print(f"OCR pages CSV: {OCR_PAGES_CSV}")
    print(f"OCR text files: {OCR_TEXT_DIR}")


if __name__ == "__main__":
    main()
