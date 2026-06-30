from __future__ import annotations

import csv
from pathlib import Path

from extract_hearing_pdf_text import INTERIM_DIR, PROJECT_ROOT, extract_pdf, extract_txt


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DOCUMENTS_CSV = INTERIM_DIR / "hearing_pdf_documents.csv"
PAGES_CSV = INTERIM_DIR / "hearing_pdf_pages.csv"
OCR_DOCUMENTS_CSV = INTERIM_DIR / "hearing_pdf_ocr_documents_corrected.csv"
OCR_PAGES_CSV = INTERIM_DIR / "hearing_pdf_ocr_pages_corrected.csv"
PROCESSED_DOCUMENTS_CSV = PROCESSED_DIR / "hearing_documents.csv"
PROCESSED_PAGES_CSV = PROCESSED_DIR / "hearing_pages.csv"

EXCLUDE_DOC_IDS = {
    "hearing_pdf_03_퇴은뜰_조류지_조성사업_편입_찬성에_대한_소유자동의서_118명",
}

PAGE_FILTERS = {
    "hearing_pdf_01_주민건의서": {1},
    "hearing_pdf_주민건의서_화포천": {1, 2},
}


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
    documents = read_csv(DOCUMENTS_CSV) or read_csv(PROCESSED_DOCUMENTS_CSV)
    pages_by_doc = group_pages(read_csv(PAGES_CSV))
    ocr_pages_by_doc = group_pages(read_csv(OCR_PAGES_CSV))
    ocr_docs_by_id = {row["doc_id"]: row for row in read_csv(OCR_DOCUMENTS_CSV)}

    processed_documents: list[dict[str, object]] = []
    processed_pages: list[dict[str, object]] = []

    for doc in documents:
        doc_id = doc["doc_id"]
        if doc_id in EXCLUDE_DOC_IDS:
            continue
        use_ocr = doc_id in ocr_pages_by_doc and (
            doc.get("needs_ocr") == "True" or doc.get("text_source") == "ocr"
        )
        source_pages = ocr_pages_by_doc[doc_id] if use_ocr else pages_by_doc.get(doc_id, [])
        if not use_ocr and not source_pages:
            source_path = PROJECT_ROOT / doc["file_path"]
            if source_path.suffix.lower() == ".pdf":
                _, extracted_pages, _ = extract_pdf(source_path)
            else:
                _, extracted_pages, _ = extract_txt(source_path)
            source_pages = [
                {
                    "doc_id": str(page["doc_id"]),
                    "page_no": str(page["page_no"]),
                    "text": str(page["text"]),
                    "char_count": str(page["char_count"]),
                }
                for page in extracted_pages
            ]
        allowed_pages = PAGE_FILTERS.get(doc_id)
        if allowed_pages:
            source_pages = [page for page in source_pages if int(page["page_no"]) in allowed_pages]
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
