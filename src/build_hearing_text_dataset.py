from __future__ import annotations

import csv
from pathlib import Path

from extract_hearing_pdf_text import INTERIM_DIR, PROJECT_ROOT


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DOCUMENTS_CSV = INTERIM_DIR / "hearing_pdf_documents.csv"
PAGES_CSV = INTERIM_DIR / "hearing_pdf_pages.csv"
OCR_DOCUMENTS_CSV = INTERIM_DIR / "hearing_pdf_ocr_documents.csv"
OCR_PAGES_CSV = INTERIM_DIR / "hearing_pdf_ocr_pages.csv"
PROCESSED_DOCUMENTS_CSV = PROCESSED_DIR / "hearing_documents.csv"
PROCESSED_PAGES_CSV = PROCESSED_DIR / "hearing_pages.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def group_pages(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["doc_id"], []).append(row)
    for page_rows in grouped.values():
        page_rows.sort(key=lambda row: int(row["page_no"]))
    return grouped


def main() -> None:
    documents = read_csv(DOCUMENTS_CSV)
    pages_by_doc = group_pages(read_csv(PAGES_CSV))
    ocr_pages_by_doc = group_pages(read_csv(OCR_PAGES_CSV))
    ocr_docs_by_id = {row["doc_id"]: row for row in read_csv(OCR_DOCUMENTS_CSV)}

    processed_documents: list[dict[str, object]] = []
    processed_pages: list[dict[str, object]] = []

    for doc in documents:
        doc_id = doc["doc_id"]
        use_ocr = doc.get("needs_ocr") == "True" and doc_id in ocr_pages_by_doc
        source_pages = ocr_pages_by_doc[doc_id] if use_ocr else pages_by_doc.get(doc_id, [])
        text_source = "ocr" if use_ocr else "pdf_text"
        full_text = "\n\n".join(page["text"] for page in source_pages if page.get("text"))

        for page in source_pages:
            processed_pages.append(
                {
                    "doc_id": doc_id,
                    "page_no": page["page_no"],
                    "text_source": text_source,
                    "text": page["text"],
                    "char_count": page["char_count"],
                }
            )

        processed_documents.append(
            {
                "doc_id": doc_id,
                "source_type": doc["source_type"],
                "title": doc["title"],
                "file_name": doc["file_name"],
                "file_path": doc["file_path"],
                "page_count": doc["page_count"],
                "text_source": text_source,
                "char_count": len(full_text),
                "ocr_done": ocr_docs_by_id.get(doc_id, {}).get("ocr_done", ""),
                "text": full_text,
            }
        )

    write_csv(
        PROCESSED_DOCUMENTS_CSV,
        processed_documents,
        [
            "doc_id",
            "source_type",
            "title",
            "file_name",
            "file_path",
            "page_count",
            "text_source",
            "char_count",
            "ocr_done",
            "text",
        ],
    )
    write_csv(
        PROCESSED_PAGES_CSV,
        processed_pages,
        ["doc_id", "page_no", "text_source", "text", "char_count"],
    )

    print(f"Processed documents: {len(processed_documents)}")
    print(f"Processed pages: {len(processed_pages)}")
    print(f"Documents CSV: {PROCESSED_DOCUMENTS_CSV}")
    print(f"Pages CSV: {PROCESSED_PAGES_CSV}")


if __name__ == "__main__":
    main()
