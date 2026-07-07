# AI 빅데이터 교육 컨설팅 — MVP 기술 구현

사업계획서 3장(핵심 서비스 모델)의 4단계 AI 파이프라인(수집→분석→가공→제공)을
실제 코드로 구현한 초기 골격입니다. 여기에 "AI 교육 뉴스 커뮤니티 + 학부모 맘카페 +
지역 교육정보 플랫폼" 모듈이 같은 리포지토리 안에 추가 통합되어 있습니다
(별도 앱이 아니라 기존 crawler/api/dashboard/docs 구조를 그대로 확장).

## 구성

- `crawler/` — Scrapy 기반 데이터 수집기 (1단계: 수집)
  - `academy_spider.py`: 민간 학원 홈페이지 커리큘럼 수집
  - `public_data_spider.py`: 학교알리미·대학 공시 등 공공 데이터 수집
  - `education_news_spider.py`: 공개 교육 뉴스 매체 수집 (커뮤니티 모듈용, 로그인 필요
    사이트/사설 카페는 대상 아님 — `docs/community-platform.md` 참고)
  - `robots.txt`는 `ROBOTSTXT_OBEY=True`로 항상 자동 준수됨
- `api/` — FastAPI 백엔드 (2~4단계: 분석/가공/제공)
  - `/ingest`, `/records`, `/reports`: 기존 입시 컨설팅 MVP (변경 없음)
  - `/community/*`, `/news/*`, `/mom-cafe/*`, `/admin/*`: 커뮤니티/뉴스/맘카페 모듈
    (아래 "커뮤니티 모듈 API" 참고)
- `dashboard-community/` — Vite + React + TypeScript 프론트엔드 (커뮤니티/뉴스/맘카페 UI)
- `docs/` — 데이터 모델, 모더레이션 정책, 임시 인증 등 상세 문서

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
scrapy crawl education_news -a start_url="<교육 뉴스 목록 URL>"   # ALLOWED_SOURCES 등재 필요

# 3. 커뮤니티 대시보드 프론트엔드 (다른 터미널) — 기존 OSINT용 dashboard/(Next.js)와는 별개
cd dashboard-community
npm install
npm run dev   # http://localhost:5173, api(localhost:8000)를 CORS로 호출
```

## 커뮤니티 모듈 API

```
POST /community/users                  임시 가입 (닉네임만) → user_id 발급, X-User-Id 헤더로 사용
GET  /community/feed                   커뮤니티 피드 (board_slug/sort/limit/offset)
GET  /community/posts/{id}             게시글 상세 + 댓글 트리
POST /community/posts                  게시글 작성
POST /community/posts/{id}/comments    댓글/대댓글 작성 (AI 독성 탐지 advisory 부가)
POST /community/posts/{id}/vote        게시글 추천/비추천
POST /community/comments/{id}/vote     댓글 추천/비추천
POST /community/posts/{id}/report      게시글 신고
GET  /community/trending               화제 키워드 (extract_trending_keywords)
GET  /community/posts/{id}/related     관련 게시글 추천 (suggest_related_posts)

GET  /news/feed                        뉴스 피드 (category/region_slug)
GET  /news/{id}                        뉴스 상세 + 댓글 트리
POST /news/ingest                      크롤러 전용 수집 엔드포인트 (education_news_spider)
POST /news/import-url                  단일 기사 수동 등록
POST /news/{id}/summarize              AI 기사 요약 (summarize_news_article)
POST /news/{id}/debate-summary         AI 댓글 토론 요약 (summarize_comment_thread + extract_debate_points)
POST /news/{id}/comments · /vote · /report   커뮤니티 게시글과 동일한 댓글/투표/신고

GET  /mom-cafe/boards                  게시판 목록
GET  /mom-cafe/region/{region}         지역 게시판 피드
GET  /mom-cafe/education               교육 게시판 피드
GET  /mom-cafe/parenting               육아 게시판 피드

GET   /admin/community/reports              신고 큐 (관리자 전용)
PATCH /admin/community/posts/{id}/moderation      게시글 모더레이션 (관리자 전용)
PATCH /admin/news/posts/{id}/moderation           뉴스 모더레이션 (관리자 전용)
```

자세한 데이터 모델은 [`docs/community-platform.md`](docs/community-platform.md),
모더레이션 정책은 [`docs/moderation.md`](docs/moderation.md),
임시 인증 방식의 한계는 [`docs/temporary-auth.md`](docs/temporary-auth.md)를 참고하세요.

### 환경 변수

`api/.env` (기존 `OPENAI_API_KEY`, `DATABASE_URL`에서 추가/변경 없음 — 커뮤니티 모듈은
같은 SQLite DB와 같은 OpenAI 클라이언트를 재사용합니다).
`dashboard-community/.env.development`: `VITE_API_BASE_URL` (기본 `http://localhost:8000`).

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

## 아직 안 한 것 / 다음 단계

- 실제 대상 사이트(학교알리미 정확한 URL/HTML 구조, 특정 학원 사이트)에 맞춘
  셀렉터 커스터마이징 — 지금 스파이더의 CSS 셀렉터는 예시 placeholder입니다.
- 크롤링 대상 사이트별 이용약관 직접 확인 (계획서 6.1항 — 법적 책임은 코드가
  대신 판단할 수 없음, robots.txt 준수는 최소 안전장치일 뿐)
- 인증/티어별 결제 연동, React Native 앱(3.3항)
- k-익명성 같은 정식 비식별화 알고리즘 (현재 `AnonymizePipeline`은 단순 필드 제거 수준)
- 자체 ML 레이어로의 전환 (3단계 로드맵 중 2단계, 데이터 누적 후)
- **임시 인증(`X-User-Id` 헤더) — TODO: 실제 OAuth2/JWT 인증으로 교체.**
  현재는 비밀번호도 세션도 없이 헤더 값을 그대로 신뢰하므로 스푸핑이 가능합니다
  (`api/app/auth.py`, [`docs/temporary-auth.md`](docs/temporary-auth.md) 참고).
- `education_news_spider.py`의 `ALLOWED_SOURCES`가 아직 비어 있음 — 실제 대상 매체를
  정하고 robots.txt/로그인 필요 여부를 직접 확인한 뒤 등재해야 합니다.
- 댓글 단위 모더레이션(개별 댓글 숨김/삭제) 미구현 — 현재는 게시글/뉴스 단위만 지원.
- `dashboard-community/`는 아직 별도 배포 파이프라인이 없음 — `render.yaml`은 `api/`만 배포하므로
  프론트엔드는 별도 정적 호스팅 서비스 추가가 필요합니다.
