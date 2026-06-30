# DB Mapping

화포천 관련 자료를 수집, 정제, 분석용 DB로 구축하기 위한 프로젝트입니다.

## 작업 범위

1. 화포천 관련 뉴스기사 수집
2. 화포천 관련 보도자료 수집
3. 공청회 PDF 자료 데이터화
4. 텍스트 분석 및 네트워크 분석용 DB 구축

## 권장 작업 흐름

1. 원본 자료를 `data/raw/`에 저장합니다.
2. 원문 텍스트와 메타데이터를 `data/interim/`에 정리합니다.
3. 분석에 사용할 표준 테이블을 `data/processed/`에 생성합니다.
4. 수집, 정제, 분석 코드는 `src/`에 작성합니다.
5. 분석 결과와 시각화 산출물은 `outputs/`에 저장합니다.

## 기본 DB 설계 초안

### documents

자료 1건을 1행으로 관리하는 중심 테이블입니다.

- `doc_id`: 문서 고유 ID
- `source_type`: `news`, `press_release`, `hearing_pdf`
- `title`: 제목
- `published_date`: 발행일
- `publisher`: 언론사, 기관명 등
- `author`: 기자명 또는 작성부서
- `url`: 원문 URL
- `file_path`: 로컬 원본 파일 경로
- `raw_text`: 원문 텍스트
- `clean_text`: 정제 텍스트
- `collected_at`: 수집일시

### document_terms

텍스트 분석용 단어/키워드 테이블입니다.

- `doc_id`: 문서 고유 ID
- `term`: 단어 또는 키워드
- `term_count`: 문서 내 출현 빈도
- `tfidf`: TF-IDF 값

### network_edges

네트워크 분석용 연결 테이블입니다.

- `source`: 출발 노드
- `target`: 도착 노드
- `edge_type`: 연결 유형
- `weight`: 연결 강도
- `doc_id`: 근거 문서 ID

## 폴더 구조

```text
data/
  raw/
    news/
    press_releases/
    hearing_pdf/
  interim/
  processed/
docs/
notebooks/
outputs/
src/
```
