# AI 빅데이터 교육 컨설팅 — MVP 기술 구현

사업계획서 3장(핵심 서비스 모델)의 4단계 AI 파이프라인(수집→분석→가공→제공)을
실제 코드로 구현한 초기 골격입니다.

## 구성

- `crawler/` — Scrapy 기반 데이터 수집기 (1단계: 수집)
  - `academy_spider.py`: 민간 학원 홈페이지 커리큘럼 수집
  - `public_data_spider.py`: 학교알리미·대학 공시 등 공공 데이터 수집
  - `robots.txt`는 `ROBOTSTXT_OBEY=True`로 항상 자동 준수됨
- `api/` — FastAPI 백엔드 (2~4단계: 분석/가공/제공)
  - `/ingest`: 크롤러가 수집 결과를 적재
  - `/reports`: OpenAI 기반 AI 리포트 생성 (BASIC/STANDARD/PREMIUM 티어별 분량 차등)
  - `/predict-missing-cutoffs`: 비공개·미수집된 대학×학과 컷오프(`cutoff_score`)를
    관측된 데이터로부터 추정 (`app/imputation.py`). 관측치가 적으면 반복 SVD
    행렬완성, 충분히 쌓이면(`VAE_MIN_OBSERVATIONS` 이상) 소형 VAE 인페인팅으로
    자동 전환. 참고: [jasper-research/beyond-the-smile-paper](https://github.com/jasper-research/beyond-the-smile-paper)
    (변동성 표면을 격자로 만들어 VAE로 인페인팅하는 아이디어를 응용)

## 실행 방법

```bash
# 1. API 서버
cd api
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
cp .env.example .env   # OPENAI_API_KEY 입력
uvicorn app.main:app --reload

# 2. 크롤러 (다른 터미널)
cd crawler
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
scrapy crawl public_data -a start_url="<공시자료 URL>" -a item_kind=admission
scrapy crawl academy -a start_url="<학원 페이지 URL>" -a academy_name="OO학원" -a region="강남"
```

## 사용 예시 (리포트 생성)

```bash
curl -X POST http://localhost:8000/reports \
  -H "Content-Type: application/json" \
  -d '{
    "student_label": "stu-anon-001",
    "tier": "STANDARD",
    "profile": {"성적대": "내신 2등급", "지망학과": "전기전자공학", "지역": "광주"}
  }'
```

## 사용 예시 (결측 컷오프 예측)

```bash
curl http://localhost:8000/predict-missing-cutoffs
```

표본이 적을 때(`n_observed < 200`)는 SVD 결과에 "표본이 적어 신뢰도가 낮다"는
경고가 함께 반환됩니다. 실제 서비스에 적용하려면 PREMIUM 리포트 등에서 이
경고를 사용자에게 그대로 노출해야 함.

## 아직 안 한 것 / 다음 단계

- 실제 대상 사이트(학교알리미 정확한 URL/HTML 구조, 특정 학원 사이트)에 맞춘
  셀렉터 커스터마이징 — 지금 스파이더의 CSS 셀렉터는 예시 placeholder입니다.
- 크롤링 대상 사이트별 이용약관 직접 확인 (계획서 6.1항 — 법적 책임은 코드가
  대신 판단할 수 없음, robots.txt 준수는 최소 안전장치일 뿐)
- 인증/티어별 결제 연동, React Native 앱(3.3항)
- k-익명성 같은 정식 비식별화 알고리즘 (현재 `AnonymizePipeline`은 단순 필드 제거 수준)
- 자체 ML 레이어로의 전환 (3단계 로드맵 중 2단계, 데이터 누적 후)
