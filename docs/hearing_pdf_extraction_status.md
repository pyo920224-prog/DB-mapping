# Hearing PDF Extraction Status

공청회 관련 원본 자료 15건을 확인했습니다.

## 결과 요약

- 전체 자료: 15건
- PDF: 14건
- TXT: 1건
- 일반 텍스트 추출 가능: 2건
- OCR 처리 완료: 13건, 206페이지
- 최종 분석 DB 제외: `03_퇴은뜰 조류지 조성사업 편입 찬성에 대한 소유자동의서(118명).pdf`
- 최종 분석 DB 페이지 제한:
  - `01_주민건의서.pdf`: 1페이지
  - `주민건의서(화포천).pdf`: 1-2페이지
- OCR 회전 보정:
  - `02_탄원서 주요내용 요약.pdf`: 270도 회전 OCR

## 텍스트 추출 가능

- `1.화포천 주민설명회.pdf`
- `농림부장관 질의서.txt`

## OCR 필요

- `01_주민건의서.pdf`
- `02_탄원서 주요내용 요약.pdf`
- `03_퇴은뜰 조류지 조성사업 편입 찬성에 대한 소유자동의서(118명).pdf`
- `04_탄원서에 대한 처리결과(낙청 하천계획과).pdf`
- `04_탄원서에 대한 처리결과(농지과).pdf`
- `05_국제신문기사.pdf`
- `06_탄원서에 대한 처리결과(농지과).pdf`
- `16042025185255.pdf`
- `16042025185326.pdf`
- `16042025185348.pdf`
- `16042025185409.pdf`
- `16042025185437.pdf`
- `주민건의서(화포천).pdf`

위 13건은 Tesseract 한국어 OCR로 처리했습니다.

## 생성 산출물

스크립트 실행 시 아래 파일이 생성됩니다.

- `data/interim/hearing_pdf_documents.csv`
- `data/interim/hearing_pdf_pages.csv`
- `data/interim/hearing_pdf_texts/*.txt`
- `data/interim/hearing_pdf_ocr_documents.csv`
- `data/interim/hearing_pdf_ocr_pages.csv`
- `data/interim/hearing_pdf_ocr_texts/*.txt`
- `data/interim/hearing_pdf_ocr_documents_corrected.csv`
- `data/interim/hearing_pdf_ocr_pages_corrected.csv`
- `data/interim/hearing_pdf_ocr_texts_corrected/*.txt`
- `data/processed/hearing_documents.csv`
- `data/processed/hearing_pages.csv`

원본과 생성 데이터는 개인정보 또는 비공개 정보가 포함될 수 있어 Git 추적 대상에서 제외했습니다.
