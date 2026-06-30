# News Collection

화포천 관련 뉴스기사는 네이버 뉴스 검색 결과를 기준으로 우선 수집합니다.

## 기본 검색어

- `화포천`
- `화포천습지`
- `김해 화포천`
- `화포천 개발`
- `화포천 생태`
- `화포천 조류`

## 수집 항목

- `doc_id`
- `source_type`
- `search_keyword`
- `search_page`
- `search_rank`
- `title`
- `publisher`
- `published_date_text`
- `url`
- `naver_news_url`
- `summary`
- `collected_at`

## 산출물

- `data/raw/news/naver_news_search_results.csv`
- `data/processed/news_documents.csv`

기사 본문 전문은 언론사별 구조와 저작권 이슈가 있어, 첫 단계에서는 검색 결과 메타데이터와 요약 중심으로 저장합니다.

기관망 프록시 환경에서 SSL 인증서 오류가 날 경우 `--insecure` 옵션으로 수집할 수 있습니다.

## 2026-06-30 수집 결과

- 검색어: 6개
- 검색어별 페이지: 5페이지
- 원자료 행 수: 601건
- 중복 제거 후 뉴스 문서 수: 323건

검색어별 최종 문서 수:

- `화포천`: 104건
- `화포천습지`: 35건
- `김해 화포천`: 12건
- `화포천 개발`: 51건
- `화포천 생태`: 31건
- `화포천 조류`: 90건
