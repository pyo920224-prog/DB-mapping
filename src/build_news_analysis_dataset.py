from __future__ import annotations

import csv
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NEWS_DOCUMENTS_CSV = PROJECT_ROOT / "data" / "processed" / "news_documents.csv"
NEWS_ANALYSIS_CSV = PROJECT_ROOT / "data" / "processed" / "news_analysis_candidates.csv"


ACTOR_PATTERNS = {
    "김해시": ["김해시", "김해시청"],
    "경상남도": ["경남", "경상남도"],
    "환경부": ["환경부"],
    "낙동강유역환경청": ["낙동강유역환경청", "낙동강환경청"],
    "주민": ["주민", "주민들", "민원인"],
    "한림면": ["한림면"],
    "시의회": ["시의회", "의회", "시의원"],
    "농민": ["농민", "농가"],
}

SECTION_PATTERNS = {
    "화포천": ["화포천"],
    "한림면": ["한림면"],
    "안하리": ["안하리"],
    "설창리": ["설창리"],
    "시산뜰": ["시산뜰"],
    "퇴은리": ["퇴은리"],
    "퇴은뜰": ["퇴은뜰"],
}

ISSUE_PATTERNS = {
    "하천기본계획": ["하천기본계획", "기본계획"],
    "홍수관리구역": ["홍수관리구역", "홍수 관리구역"],
    "하천정비": ["하천정비", "하천 정비", "정비사업", "정비 사업"],
    "주민의견": ["주민의견", "주민 의견", "주민건의", "주민 건의", "건의서", "탄원서", "민원"],
    "공청회·설명회": ["공청회", "설명회", "주민설명회", "주민 설명회"],
    "침수·홍수": ["침수", "홍수", "범람", "수해", "피해"],
    "저류지": ["저류지", "조류지"],
}

CONFLICT_PATTERNS = {
    "계획·절차 갈등": ["하천기본계획", "기본계획", "공청회", "설명회"],
    "홍수·침수 위험 갈등": ["홍수", "침수", "범람", "수해"],
    "하천정비·토지이용 갈등": ["하천정비", "정비사업", "저류지", "조류지", "편입"],
    "주민의견·민원 갈등": ["주민", "건의", "건의서", "탄원", "민원"],
}

INCLUDE_TERMS = [
    "하천기본계획",
    "기본계획",
    "홍수관리구역",
    "홍수",
    "침수",
    "범람",
    "수해",
    "하천정비",
    "정비사업",
    "주민설명회",
    "설명회",
    "공청회",
    "주민의견",
    "주민건의",
    "건의서",
    "탄원서",
    "민원",
    "한림면",
    "안하리",
    "설창리",
    "시산뜰",
    "퇴은리",
    "퇴은뜰",
    "저류지",
]

EXCLUDE_TERMS = [
    "축제",
    "탐방",
    "관광",
    "홍보",
    "교육",
    "체험",
    "캠프",
    "반딧불이",
    "생태관광",
    "걷기",
    "행사",
    "개최",
    "프로그램",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def find_labels(text: str, patterns: dict[str, list[str]]) -> str:
    labels = []
    for label, terms in patterns.items():
        if any(term in text for term in terms):
            labels.append(label)
    return "; ".join(labels)


def should_use(text: str) -> str:
    has_include = any(term in text for term in INCLUDE_TERMS)
    has_exclude = any(term in text for term in EXCLUDE_TERMS)
    if has_include:
        return "활용"
    if has_exclude:
        return "제외"
    return "검토"


def main() -> None:
    source_rows = read_csv(NEWS_DOCUMENTS_CSV)
    output_rows: list[dict[str, str]] = []

    for row in source_rows:
        title = normalize_space(row.get("title", ""))
        summary = normalize_space(row.get("summary", ""))
        text = f"{row.get('search_keyword', '')} {title} {summary}"
        output_rows.append(
            {
                "기사ID": row.get("doc_id", ""),
                "제목": title,
                "언론사": row.get("publisher", ""),
                "날짜": row.get("published_date_text", ""),
                "URL": row.get("url", ""),
                "주요 내용": summary,
                "등장 행위자": find_labels(text, ACTOR_PATTERNS),
                "관련 구간": find_labels(text, SECTION_PATTERNS),
                "주요 쟁점": find_labels(text, ISSUE_PATTERNS),
                "갈등유형 후보": find_labels(text, CONFLICT_PATTERNS),
                "분석 활용 여부": should_use(text),
            }
        )

    fieldnames = [
        "기사ID",
        "제목",
        "언론사",
        "날짜",
        "URL",
        "주요 내용",
        "등장 행위자",
        "관련 구간",
        "주요 쟁점",
        "갈등유형 후보",
        "분석 활용 여부",
    ]
    write_csv(NEWS_ANALYSIS_CSV, output_rows, fieldnames)
    print(f"Rows: {len(output_rows)}")
    print(f"Output: {NEWS_ANALYSIS_CSV}")


if __name__ == "__main__":
    main()
