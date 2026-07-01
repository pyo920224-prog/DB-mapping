from __future__ import annotations

import argparse
import csv
import hashlib
import html
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import requests
import urllib3
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "press_releases"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RAW_CSV = RAW_DIR / "official_press_release_search_results.csv"
PROCESSED_CSV = PROCESSED_DIR / "press_release_analysis_candidates.csv"


KEYWORDS = [
    "화포천",
    "화포천 하천기본계획",
    "화포천 하천기본계획 변경",
    "화포천 홍수관리구역",
    "화포천 하천정비",
    "화포천 주민설명회",
    "화포천 공청회",
    "화포천 침수",
    "화포천 한림면",
    "김해 화포천",
    "김해 한림면 침수",
]


AGENCIES = [
    {
        "name": "김해시",
        "domains": ["gimhae.go.kr"],
        "query_prefix": "김해시",
    },
    {
        "name": "낙동강유역환경청",
        "domains": ["me.go.kr"],
        "query_prefix": "낙동강유역환경청",
    },
    {
        "name": "환경부",
        "domains": ["me.go.kr"],
        "query_prefix": "환경부",
    },
    {
        "name": "경상남도",
        "domains": ["gyeongnam.go.kr"],
        "query_prefix": "경상남도",
    },
    {
        "name": "한국농어촌공사",
        "domains": ["ekr.or.kr"],
        "query_prefix": "한국농어촌공사",
    },
    {
        "name": "기타 관련 공공기관",
        "domains": ["kwater.or.kr", "water.or.kr", "flood.go.kr", "gimhae.go.kr"],
        "query_prefix": "공공기관",
    },
]


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


ACTOR_PATTERNS = {
    "김해시": ["김해시", "김해시청"],
    "낙동강유역환경청": ["낙동강유역환경청", "낙동강환경청"],
    "환경부": ["환경부"],
    "경상남도": ["경상남도", "경남"],
    "한국농어촌공사": ["한국농어촌공사", "농어촌공사"],
    "주민": ["주민", "민원", "건의", "탄원"],
    "한림면": ["한림면"],
    "농민": ["농민", "농가", "농지"],
}

SECTION_PATTERNS = {
    "화포천": ["화포천"],
    "한림면": ["한림면"],
    "안하리": ["안하리"],
    "설창리": ["설창리"],
    "시산뜰": ["시산뜰"],
    "퇴은리": ["퇴은리"],
    "퇴은뜰": ["퇴은뜰"],
    "홍수관리구역": ["홍수관리구역", "홍수 관리구역"],
    "저류지": ["저류지", "조류지"],
}

ISSUE_PATTERNS = {
    "하천기본계획": ["하천기본계획", "기본계획"],
    "하천기본계획 변경": ["하천기본계획 변경", "기본계획 변경"],
    "홍수관리구역": ["홍수관리구역", "홍수 관리구역"],
    "하천정비": ["하천정비", "하천 정비", "정비사업"],
    "침수·홍수": ["침수", "홍수", "범람", "수해"],
    "주민의견·주민건의": ["주민의견", "주민 의견", "주민건의", "건의서", "탄원서", "민원"],
    "공청회·주민설명회": ["공청회", "설명회", "주민설명회", "간담회"],
    "재산권": ["재산권", "토지", "편입", "보상"],
    "농지보전": ["농지", "농업", "농민", "농가"],
    "생태보전": ["생태", "습지", "보전"],
    "자료정합성": ["자료", "정합성", "오류", "검토"],
}

CONFLICT_PATTERNS = {
    "계획·절차 갈등": ["하천기본계획", "기본계획", "공청회", "설명회", "간담회"],
    "홍수안전 갈등": ["홍수", "침수", "범람", "수해"],
    "재산권·토지이용 갈등": ["재산권", "토지", "편입", "보상"],
    "농지보전 갈등": ["농지", "농업", "농민", "농가"],
    "생태보전 갈등": ["생태", "습지", "보전"],
    "자료정합성 갈등": ["자료", "정합성", "오류"],
    "주민참여·의견수렴 갈등": ["주민", "건의", "탄원", "민원", "의견수렴"],
}

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
    "프로그램",
]

CORE_ANALYSIS_TERMS = [
    "하천기본계획",
    "기본계획",
    "홍수관리구역",
    "하천정비",
    "정비사업",
    "주민설명회",
    "공청회",
    "간담회",
    "침수",
    "홍수",
    "범람",
    "수해",
    "주민의견",
    "주민건의",
    "건의서",
    "탄원서",
    "민원",
    "재산권",
    "농지",
    "보상",
    "편입",
    "저류지",
]


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    return re.sub(r"\s+", " ", value).strip()


def stable_doc_id(url: str, title: str) -> str:
    digest = hashlib.sha1((url or title).encode("utf-8")).hexdigest()[:12]
    return f"press_{digest}"


def host_matches(url: str, domains: list[str]) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host == domain or host.endswith(f".{domain}") for domain in domains)


def is_valid_official_url(url: str, domains: list[str]) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not host_matches(url, domains):
        return False
    if any(blocked in url for blocked in ["search.naver.com", "blog.naver.com", "kin.naver.com"]):
        return False
    return True


def is_bad_title(title: str, agency_name: str) -> bool:
    normalized = clean_text(title)
    if not normalized:
        return True
    if normalized == agency_name:
        return True
    if "www." in normalized and len(normalized.split()) <= 3:
        return True
    if normalized in {"홈", "본문 바로가기", "사이트맵", "검색"}:
        return True
    return False


def infer_doc_type(text: str) -> str:
    if any(term in text for term in ["보도자료", "보도 자료"]):
        return "보도자료"
    if any(term in text for term in ["설명자료", "설명 자료"]):
        return "설명자료"
    if any(term in text for term in ["고시", "공고"]):
        return "고시공고"
    if any(term in text for term in ["공지", "알림"]):
        return "공지사항"
    if any(term in text for term in ["정책", "계획"]):
        return "정책자료"
    if any(term in text for term in ["회의", "간담회", "공청회", "설명회"]):
        return "회의자료"
    return "기타"


def extract_date_text(text: str) -> str:
    match = re.search(r"(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}|20\d{2}년\s*\d{1,2}월\s*\d{1,2}일)", text)
    return match.group(1) if match else ""


def find_labels(text: str, patterns: dict[str, list[str]]) -> str:
    labels = []
    for label, terms in patterns.items():
        if any(term in text for term in terms):
            labels.append(label)
    return "; ".join(labels)


def analysis_flag(text: str) -> str:
    has_core_issue = any(term in text for term in CORE_ANALYSIS_TERMS)
    has_exclude = any(term in text for term in EXCLUDE_TERMS)
    if has_core_issue:
        return "활용"
    if has_exclude:
        return "제외"
    if bool(find_labels(text, ISSUE_PATTERNS)):
        return "검토"
    return "검토"


def search_naver(session: requests.Session, query: str, page: int, verify_ssl: bool) -> BeautifulSoup:
    start = (page - 1) * 10 + 1
    url = f"https://search.naver.com/search.naver?where=web&query={quote_plus(query)}&start={start}"
    response = session.get(url, timeout=20, verify=verify_ssl)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def collect(pages: int, delay: float, verify_ssl: bool) -> list[dict[str, str]]:
    session = requests.Session()
    session.headers.update(HEADERS)
    rows: list[dict[str, str]] = []

    for agency in AGENCIES:
        for keyword in KEYWORDS:
            domain_query = " OR ".join(f"site:{domain}" for domain in agency["domains"])
            query = f"{domain_query} {agency['query_prefix']} {keyword}"
            print(f"Collecting: {agency['name']} / {keyword}")
            for page in range(1, pages + 1):
                try:
                    soup = search_naver(session, query=query, page=page, verify_ssl=verify_ssl)
                except requests.HTTPError as exc:
                    print(f"Skipped HTTP error: {agency['name']} / {keyword} / page {page}: {exc}")
                    break
                except requests.RequestException as exc:
                    print(f"Skipped request error: {agency['name']} / {keyword} / page {page}: {exc}")
                    break
                for link in soup.find_all("a", href=True):
                    url = link.get("href", "").strip()
                    title = clean_text(link.get_text(" "))
                    if not title or len(title) < 3:
                        continue
                    if is_bad_title(title, agency["name"]):
                        continue
                    if not is_valid_official_url(url, agency["domains"]):
                        continue
                    context = clean_text(link.parent.get_text(" ") if link.parent else title)
                    text = f"{agency['name']} {keyword} {title} {context}"
                    rows.append(
                        {
                            "문서ID": stable_doc_id(url, title),
                            "기관명": agency["name"],
                            "자료유형": infer_doc_type(text),
                            "제목": title,
                            "배포일": extract_date_text(context),
                            "URL": url,
                            "관련 구간": find_labels(text, SECTION_PATTERNS),
                            "주요 행위자": find_labels(text, ACTOR_PATTERNS),
                            "주요 쟁점": find_labels(text, ISSUE_PATTERNS),
                            "갈등유형 후보": find_labels(text, CONFLICT_PATTERNS),
                            "분석대상 여부": analysis_flag(text),
                            "비고": f"검색어={keyword}",
                        }
                    )
                time.sleep(delay)
    return rows


def deduplicate(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    unique_rows: list[dict[str, str]] = []
    for row in rows:
        key = row["URL"]
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)
    return unique_rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "문서ID",
        "기관명",
        "자료유형",
        "제목",
        "배포일",
        "URL",
        "관련 구간",
        "주요 행위자",
        "주요 쟁점",
        "갈등유형 후보",
        "분석대상 여부",
        "비고",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect official press release candidates.")
    parser.add_argument("--pages", type=int, default=3, help="Search pages per agency/keyword.")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay seconds between requests.")
    parser.add_argument("--insecure", action="store_true", help="Disable SSL verification.")
    args = parser.parse_args()

    if args.insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    raw_rows = collect(pages=args.pages, delay=args.delay, verify_ssl=not args.insecure)
    unique_rows = deduplicate(raw_rows)
    write_csv(RAW_CSV, raw_rows)
    write_csv(PROCESSED_CSV, unique_rows)
    print(f"Raw rows: {len(raw_rows)}")
    print(f"Unique rows: {len(unique_rows)}")
    print(f"Raw CSV: {RAW_CSV}")
    print(f"Processed CSV: {PROCESSED_CSV}")


if __name__ == "__main__":
    main()
