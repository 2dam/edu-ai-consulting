# 데이터 수집 파이프라인 (scripts/)

`/site-stats`가 세는 지표(`curriculum_items`, `admission_data_points`)를 채우기 위한
수집기 + `POST /ingest-batch` 클라이언트.

## 구조

| 파일 | 역할 |
|------|------|
| `collect_academies.py` | data.go.kr 학원신고현황(시도별 공공 OpenAPI) → `CurriculumItem` |
| `collect_admissions.py` | 대학 입학처 공시 입결(CSV/JSON) → `AdmissionResultItem` |
| `ingest_client.py` | `/ingest-batch` 호출 래퍼 (수집기에서 import 또는 stdin 파이프) |
| `sample_admission.json` | 입결 샘플(테스트용, 운영 데이터 아님) |

## item_type (RawRecord)

- `CurriculumItem` ← `/site-stats`의 `curriculum_items`
- `AdmissionResultItem` ← `/site-stats`의 `admission_data_points`

## 실행

### 학원 (data.go.kr)
```bash
# 1. data.go.kr 에서 시도별 "학원신고현황" OpenAPI endpoint 를 ACADEMY_APIS 에 채움
# 2. 인증키 발급 후
DATA_API_KEY=xxxx python collect_academies.py --limit 10000
DATA_API_KEY=xxxx python collect_academies.py --only seoul --dry-run   # 미리보기
```

### 입결 (대학 공시)
```bash
# CSV(컬럼: university,department,admission_type,year,recruited,applied,admitted,enrolled,avg_grade,region)
python collect_admissions.py --csv admission_2024.csv
# 또는 단일 대학 JSON 샘플
python collect_admissions.py --sample-json sample_admission.json --dry-run
```

### 적재 (ingest_client)
수집기가 자동으로 `ingest_client.push_batch()` 호출.
직접 보낼 땐:
```bash
INGEST_BASE_URL=https://ichapterwise.com CONTENT_INGEST_API_KEY=xxx \
  python collect_admissions.py --csv admission_2024.csv
# 또는 stdin
cat payloads.jsonl | INGEST_BASE_URL=... CONTENT_INGEST_API_KEY=... python ingest_client.py
```

## ⚠️ 법적 주의
- 학원정보는 영리 무단 스크래핑 시 문제 소지. 공공데이터 이용조건(상업 이용 가능 여부, 출처 표기) 사전 확인.
- 요청 빈도(rate limit) 준수 (`collect_academies.py`의 `DEFAULT_DELAY`).
- `reports_issued`, `active_members` 는 **실제 비즈니스 실적**이므로 절대 허위로 채우지 말 것.

## 검증 상태
- `collect_admissions.py` 파싱 → `AdmissionResultItem` 래핑: 동작 확인됨
- `ingest_client` → `/ingest-batch` → DB `RawRecord` 기록: 동작 확인됨 (로컬 SQLite)
- 실제 운영(Render) 적재는 `CONTENT_INGEST_API_KEY` + 운영 `INGEST_BASE_URL` 로 실행 필요
