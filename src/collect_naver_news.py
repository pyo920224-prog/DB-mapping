from __future__ import annotations

import argparse
import csv
import hashlib
import html
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.parse import quote_plus

import requests
import urllib3
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_NEWS_DIR = PROJECT_ROOT / "data" / "raw" / "news"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RAW_NEWS_CSV = RAW_NEWS_DIR / "naver_news_search_results.csv"
PROCESSED_NEWS_CSV = PROCESSED_DIR / "news_documents.csv"

DEFAULT_KEYWORDS = [
    "화포천",
    "화포천습지",
    "김해 화포천",
    "화포천 개발",
    "화포천 생태",
    "화포천 조류",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def stable_doc_id(url: str, title: str) -> str:
    key = url or title
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"news_{digest}"


def parse_info_texts(info_texts: list[str]) -> tuple[str, str]:
    publisher = ""
    published_date = ""
    for text in info_texts:
        text = clean_text(text)
        if not text or text == "네이버뉴스":
            continue
        if not publisher:
            publisher = text
            continue
        if any(token in text for token in ["전", ".", "-"]) or re.search(r"\d", text):
            published_date = text
    return publisher, published_date


def looks_like_article_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    if not host or host in {"search.naver.com", "help.naver.com"}:
        return False
    if "news.naver.com/main/static" in url:
        return False
    if path in {"", "/"}:
        return False
    article_markers = [
        "article",
        "articleview",
        "view",
        "news",
        "mnews",
        "idxno",
        "no=",
    ]
    return any(marker in url.lower() for marker in article_markers)


def publisher_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def extract_date_text(link) -> str:
    date_pattern = re.compile(
        r"(\d{4}\.\d{1,2}\.\d{1,2}\.|\d+\s*(?:분|시간|일|주|개월|년)\s*전|어제)"
    )
    current = link
    for _ in range(8):
        current = current.parent
        if current is None:
            break
        text = clean_text(current.get_text(" "))
        match = date_pattern.search(text)
        if match:
            return match.group(1).replace(" ", "")
    return ""


def parse_current_naver_news(soup: BeautifulSoup, keyword: str, page: int) -> list[dict[str, str]]:
    grouped: dict[str, list[str]] = {}
    date_texts: dict[str, str] = {}
    naver_urls: dict[str, str] = {}

    for link in soup.select(".group_news a[href]"):
        url = link.get("href", "").strip()
        text = clean_text(link.get_text(" "))
        if not text or not looks_like_article_url(url):
            continue
        if text in {"네이버뉴스", "언론사 선정"}:
            continue
        if "n.news.naver.com" in url:
            naver_urls.setdefault(url, url)
        grouped.setdefault(url, [])
        if text not in grouped[url]:
            grouped[url].append(text)
        date_texts.setdefault(url, extract_date_text(link))

    rows: list[dict[str, str]] = []
    for rank, (article_url, texts) in enumerate(grouped.items(), start=1):
        if not texts:
            continue
        title = texts[0]
        summary_candidates = [text for text in texts[1:] if text != title]
        summary = max(summary_candidates, key=len) if summary_candidates else ""
        rows.append(
            {
                "doc_id": stable_doc_id(article_url, title),
                "source_type": "news",
                "search_keyword": keyword,
                "search_page": str(page),
                "search_rank": str(rank),
                "title": title,
                "publisher": publisher_from_url(article_url),
                "published_date_text": date_texts.get(article_url, ""),
                "url": article_url,
                "naver_news_url": naver_urls.get(article_url, ""),
                "summary": summary,
                "collected_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    return rows


def fetch_keyword(keyword: str, pages: int, delay: float, verify_ssl: bool) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for page in range(1, pages + 1):
        start = (page - 1) * 10 + 1
        url = (
            "https://search.naver.com/search.naver"
            f"?where=news&sm=tab_pge&query={quote_plus(keyword)}&start={start}"
        )
        response = session.get(url, timeout=20, verify=verify_ssl)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select("div.news_area")
        if not items:
            rows.extend(parse_current_naver_news(soup, keyword=keyword, page=page))
            time.sleep(delay)
            continue

        for rank, item in enumerate(items, start=1):
            title_tag = item.select_one("a.news_tit")
            if not title_tag:
                continue
            title = clean_text(title_tag.get("title") or title_tag.get_text(" "))
            article_url = title_tag.get("href", "").strip()
            summary_tag = item.select_one("a.api_txt_lines.dsc_txt_wrap")
            summary = clean_text(summary_tag.get_text(" ")) if summary_tag else ""
            info_texts = [node.get_text(" ") for node in item.select("span.info")]
            publisher, published_date = parse_info_texts(info_texts)
            naver_url_tag = item.select_one("a.info[href*='n.news.naver.com']")

            rows.append(
                {
                    "doc_id": stable_doc_id(article_url, title),
                    "source_type": "news",
                    "search_keyword": keyword,
                    "search_page": str(page),
                    "search_rank": str(rank),
                    "title": title,
                    "publisher": publisher,
                    "published_date_text": published_date,
                    "url": article_url,
                    "naver_news_url": naver_url_tag.get("href", "").strip() if naver_url_tag else "",
                    "summary": summary,
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        time.sleep(delay)
    return rows


def deduplicate(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    unique_rows: list[dict[str, str]] = []
    for row in rows:
        key = row["url"] or f"{row['title']}::{row['publisher']}"
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)
    return unique_rows


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Naver news search metadata.")
    parser.add_argument("--pages", type=int, default=5, help="Search result pages per keyword.")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay seconds between requests.")
    parser.add_argument("--keyword", action="append", dest="keywords", help="Keyword to collect.")
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable SSL certificate verification for restricted proxy environments.",
    )
    args = parser.parse_args()

    verify_ssl = not args.insecure
    if args.insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    keywords = args.keywords or DEFAULT_KEYWORDS
    all_rows: list[dict[str, str]] = []
    for keyword in keywords:
        print(f"Collecting: {keyword}")
        all_rows.extend(fetch_keyword(keyword, pages=args.pages, delay=args.delay, verify_ssl=verify_ssl))

    raw_rows = all_rows
    processed_rows = deduplicate(all_rows)
    fieldnames = [
        "doc_id",
        "source_type",
        "search_keyword",
        "search_page",
        "search_rank",
        "title",
        "publisher",
        "published_date_text",
        "url",
        "naver_news_url",
        "summary",
        "collected_at",
    ]

    write_csv(RAW_NEWS_CSV, raw_rows, fieldnames)
    write_csv(PROCESSED_NEWS_CSV, processed_rows, fieldnames)

    print(f"Raw rows: {len(raw_rows)}")
    print(f"Unique rows: {len(processed_rows)}")
    print(f"Raw CSV: {RAW_NEWS_CSV}")
    print(f"Processed CSV: {PROCESSED_NEWS_CSV}")


if __name__ == "__main__":
    main()
