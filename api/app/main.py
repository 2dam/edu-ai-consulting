
import asyncio
import hmac
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import ai_engine, career_guidance_centers, cctv, feedback_loop, imputation, naver_news, official_sources, predictive_model, psychology_engine, qcrm_engine, university_admissions, youtube
from app import models_community  # noqa: F401 - Base.metadata에 커뮤니티 테이블을 등록시키기 위한 import
from app.models_community import Comment, CommunityPost, User
from app import models_reputation  # noqa: F401 - Base.metadata에 학원 평판 테이블을 등록시키기 위한 import
from app.database import Base, engine, get_db
from app.models import ConsultingReport, FeedbackRecord, RawRecord
from app import understanding_models  # noqa: F401 - 상호이해 모델 등록
from app import understanding_engine
from app.routers import admin, authentication, committee, community, mom_cafe, news, reputation, videos
from app.schemas import (
    CctvInfo,
    CctvResponse,
    DropoutRiskRequest,
    DropoutRiskResponse,
    FeedbackRequest,
    FeedbackResponse,
    IngestPayload,
    LoopStatusResponse,
    PsychAssessmentRequest,
    PsychAssessmentResponse,
    QcrmAssessmentRequest,
    QcrmAssessmentResponse,
    ReportRequest,
    ReportResponse,
)
from app.seed import seed_defaults
from app import timeseries_engine  # noqa: F401 - ts_* 테이블을 Base.metadata에 등록
from app import timeseries_models  # noqa: F401

logger = logging.getLogger(__name__)

# ── 백그라운드 루프 스케줄러 ──────────────────────────────────────────────────
LOOP_INTERVAL_SECONDS = 30 * 60  # 30분마다 루프 틱


async def _loop_scheduler() -> None:
    """서버가 살아있는 동안 주기적으로 feedback_loop.run_loop_tick() 을 호출한다."""
    await asyncio.sleep(60)  # 서버 기동 직후 1분 대기
    while True:
        try:
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                metric = feedback_loop.run_loop_tick(db, trigger="scheduled")
                if metric:
                    logger.info("[스케줄러] 루프 사이클 완료: metric_id=%d", metric.id)
            finally:
                db.close()
        except Exception as exc:
            logger.error("[스케줄러] 루프 틱 오류: %s", exc)
        await asyncio.sleep(LOOP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.auth import validate_auth_configuration
    validate_auth_configuration()
    Base.metadata.create_all(bind=engine)
    # SQLite 영구 디스크에 구버전 테이블이 남아있을 때 누락 컬럼 추가(멱등/운영데이터 보존)
    try:
        from app.understanding_models import migrate_understanding_columns
        migrate_understanding_columns(engine)
    except Exception as _e:
        logging.warning("understanding migration skipped: %s", _e)
    # 운영 DB의 raw_records가 수만 건 규모라 CREATE INDEX/ANALYZE를 앱 시작(lifespan) 경로에
    # 동기로 넣었더니 기동 자체가 헬스체크 타임아웃을 넘겨버려 502를 유발했다 — 되돌림.
    # 인덱스 보정은 별도 1회성 스크립트로 오프라인에서 실행할 것(앱 기동 경로에 넣지 않는다).
    # facility_type/region/district 컬럼 승격(ADD COLUMN + 백필 + 인덱스)도 같은 이유로
    # backfill_facility_columns.py로 뺐다 — 새 DB는 모델 정의에 컬럼이 이미 있어 문제없다.
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        from app.seed import migrate_auth_schema
        migrate_auth_schema(db)
        # 재시작 시 마지막 활성 prompt variant 복원
        feedback_loop.restore_variant_from_db(db)
        # 커뮤니티 모듈 기본 지역/게시판 시드 (멱등)
        seed_defaults(db)
    finally:
        db.close()
    # 백그라운드 루프 시작
    task = asyncio.create_task(_loop_scheduler())
    yield
    task.cancel()


app = FastAPI(title="AI 빅데이터 교육 컨설팅 API", lifespan=lifespan)

# dashboard-community/(Vite 개발 서버 localhost:5173 + Render Static Site 배포본)에서
# 오는 요청을 허용한다. 커뮤니티/뉴스 모듈이 별도 프론트엔드로 분리되며 새로 필요해진
# 설정 — 기존 라우트에는 영향 없음.
# TODO: community.ichapterwise.com 커스텀 도메인을 연결하면 여기에도 추가할 것.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://ichapterwise.com",
        "https://www.ichapterwise.com",
        "https://app.ichapterwise.com",
        "https://community.ichapterwise.com",
        "https://edu-ai-consulting-community.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(community.router)
app.include_router(authentication.router)
app.include_router(news.router)
app.include_router(videos.router)
app.include_router(mom_cafe.router)
app.include_router(admin.router)
app.include_router(committee.router)
app.include_router(reputation.router)

STATIC_DIR = Path(__file__).parent / "static"


class NoCacheStaticFiles(StaticFiles):
    """정적 파일(특히 대시보드 HTML) 캐시 무력화 — 버튼 수정 즉시 반영되도록."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def file_response(self, full_path, stat_result, scope, status_code=200):
        resp = super().file_response(full_path, stat_result, scope, status_code)
        resp.headers.update({"Cache-Control": "no-store, max-age=0"})
        return resp


app.mount("/static", NoCacheStaticFiles(directory=STATIC_DIR), name="static")


# ── 정적 페이지 ───────────────────────────────────────────────────────────────

@app.get("/")
def index():
    # 통합된 랜딩 페이지(마케팅 + 리포트 체험 폼)를 기본 페이지로 제공.
    return FileResponse(STATIC_DIR / "landing.html")


@app.get("/landing")
def landing():
    return FileResponse(STATIC_DIR / "landing.html")


@app.get("/survey")
def survey():
    return FileResponse(STATIC_DIR / "survey.html")


@app.get("/admin")
def admin(key: str | None = None):
    # 내부 참고용 지표 대시보드 — 외부 공개 차단
    if key != "internal":
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            "<!doctype html><meta charset='utf-8'><title>접근 제한</title>"
            "<body style='font-family:sans-serif;background:#0d1117;color:#ddd;display:flex;"
            "align-items:center;justify-content:center;height:100vh;margin:0'>"
            "<div style='text-align:center'><h1>내부 전용</h1>"
            "<p>이 페이지는 내부 참고용입니다. 관리자 키가 필요합니다.</p></div></body>",
            status_code=403,
        )
    return FileResponse(STATIC_DIR / "admin.html")


@app.get("/education")
def education_columns():
    # 교육 데이터 칼럼 (SEO 콘텐츠용, 광고 없음)
    return FileResponse(STATIC_DIR / "education.html")


@app.get("/guide")
def parent_guide():
    # 학부모 가이드 (SEO 콘텐츠용, 광고 없음)
    return FileResponse(STATIC_DIR / "guide.html")


@app.get("/timesfm")
def timesfm_page():
    resp = FileResponse(STATIC_DIR / "timesfm.html")
    resp.headers.update({"Cache-Control": "no-store, max-age=0"})
    return resp


@app.get("/understand")
def understand_page():
    return FileResponse(STATIC_DIR / "understand.html")


@app.get("/rti-pbis")
def rti_pbis_page():
    resp = FileResponse(STATIC_DIR / "rti_pbis.html")
    resp.headers.update({"Cache-Control": "no-store, max-age=0"})
    return resp


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/official-admission-sources")
def official_admission_sources():
    """콘텐츠를 복제하지 않고 입시 공식 원문과 연동 상태를 안내한다."""
    return {"items": official_sources.list_official_sources()}


@app.get("/university-admissions")
def university_admission_sites(q: str | None = None, region: str | None = None):
    """검증한 대학 공식 입학처 링크를 대학명 또는 지역으로 조회한다."""
    items = university_admissions.list_university_admissions(query=q, region=region)
    return {"items": items, "count": len(items), "verified_at": university_admissions.VERIFIED_AT}


@app.get("/career-guidance-centers")
def career_guidance_center_sites(q: str | None = None, region: str | None = None):
    """전국 시도교육청의 공식 진로·진학 지원 서비스 링크를 조회한다."""
    items = career_guidance_centers.list_career_guidance_centers(query=q, region=region)
    return {"items": items, "count": len(items), "verified_at": career_guidance_centers.VERIFIED_AT}


# ── 크롤러 데이터 적재 ────────────────────────────────────────────────────────

def require_ingest_key(x_ingest_key: str | None = Header(default=None)) -> None:
    expected_key = os.getenv("CONTENT_INGEST_API_KEY", "").strip() or os.getenv("VIDEO_INGEST_API_KEY", "").strip()
    if not expected_key:
        raise HTTPException(status_code=503, detail="Content ingestion is not configured")
    if not x_ingest_key or not hmac.compare_digest(x_ingest_key, expected_key):
        raise HTTPException(status_code=401, detail="Invalid ingestion key")


def _apply_raw_payload(record: RawRecord, payload: IngestPayload) -> None:
    record.item_type = payload.item_type
    record.data = payload.data
    record.source_url = payload.data.get("source_url", "")
    record.facility_type = payload.data.get("facility_type")
    record.region = payload.data.get("region")
    record.district = payload.data.get("district")


@app.post("/ingest", dependencies=[Depends(require_ingest_key)])
def ingest(payload: IngestPayload, db: Session = Depends(get_db)):
    source_url = str(payload.data.get("source_url") or "")
    record = None
    if payload.item_type == "EducationFacilityItem" and source_url:
        record = db.query(RawRecord).filter(
            RawRecord.item_type == payload.item_type,
            RawRecord.source_url == source_url,
        ).first()
    if record is None:
        record = RawRecord()
        db.add(record)
    _apply_raw_payload(record, payload)
    db.commit()
    return {"id": record.id}


@app.post("/ingest-batch", dependencies=[Depends(require_ingest_key)])
def ingest_batch(payloads: list[IngestPayload], db: Session = Depends(get_db)):
    """대량 적재. 시설은 공식 원문 식별 URL을 기준으로 갱신해 재수집 중복을 막는다."""
    facility_urls = {
        str(p.data.get("source_url"))
        for p in payloads
        if p.item_type == "EducationFacilityItem" and p.data.get("source_url")
    }
    existing = {}
    if facility_urls:
        existing = {
            record.source_url: record
            for record in db.query(RawRecord).filter(
                RawRecord.item_type == "EducationFacilityItem",
                RawRecord.source_url.in_(facility_urls),
            ).all()
        }

    for payload in payloads:
        source_url = str(payload.data.get("source_url") or "")
        record = existing.get(source_url) if payload.item_type == "EducationFacilityItem" else None
        if record is None:
            record = RawRecord()
            db.add(record)
            if payload.item_type == "EducationFacilityItem" and source_url:
                existing[source_url] = record
        _apply_raw_payload(record, payload)
    db.commit()
    return {"count": len(payloads)}


@app.get("/records")
def list_records(item_type: str | None = None, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(RawRecord)
    if item_type:
        query = query.filter(RawRecord.item_type == item_type)
    records = query.order_by(RawRecord.created_at.desc()).limit(limit).all()
    return [
        {"id": r.id, "item_type": r.item_type, "data": r.data, "created_at": r.created_at}
        for r in records
    ]


# ── 어린이집·유치원·초등학교 기초자료 (컨설팅 대상 확장) ─────────────────────

_EDUCATION_FACILITIES_MAX_LIMIT = 3000  # 수만 건을 한 번에 메모리로 올리다 인스턴스 OOM을 유발한 적이 있어 서버 측에서 상한을 강제한다.
_EDUCATION_FACILITIES_CACHE_TTL = 60  # 초 — 크롤러가 계속 새로 적재하므로 /region-stats(600초)보다 짧게 둔다.
_education_facilities_cache: dict[tuple, dict] = {}
_EDUCATION_FACILITIES_CACHE_MAX_KEYS = 200  # 쿼리 파라미터 조합이 비정상적으로 늘어나는 걸 대비한 안전장치.


@app.get("/education-facilities")
def list_education_facilities(
    facility_type: str | None = None,
    region: str | None = None,
    district: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """crawler/early_education_spider 가 수집한 어린이집·유치원·초등학교 기초자료 조회.

    facility_type: daycare | kindergarten | elementary | academy | university

    facility_type/region/district는 limit을 적용하기 전에 SQL 레벨에서 걸러낸다 — 예전엔
    "최근 limit건을 가져온 뒤 Python에서 필터"하는 방식이라, 특정 facility_type의 크롤이
    대량으로 몰리면(예: 유치원 8만건 적재) 그보다 오래된 다른 타입(학원·초등 등)이 최근
    limit건 안에 아예 안 들어와 조회 결과에서 통째로 사라지는 버그가 있었다.

    예전엔 json_extract(data, '$.facility_type')로 걸러 raw_records 12만 건대를 매번
    풀스캔했다 — facility_type/region/district를 실제 컬럼으로 승격해 인덱스를 태우고
    (backfill_facility_columns.py), 짧은 TTL 캐시로 HUD 대시보드의 동시 방문 부하까지 흡수한다.
    """
    limit = min(limit, _EDUCATION_FACILITIES_MAX_LIMIT)
    cache_key = (facility_type, region, district, limit)
    now = time.monotonic()
    cached = _education_facilities_cache.get(cache_key)
    if cached is not None and now - cached["computed_at"] < _EDUCATION_FACILITIES_CACHE_TTL:
        return cached["data"]

    query = db.query(RawRecord).filter(RawRecord.item_type == "EducationFacilityItem")
    if facility_type:
        query = query.filter(RawRecord.facility_type == facility_type)
    if region:
        query = query.filter(RawRecord.region == region)
    if district:
        query = query.filter(RawRecord.district == district)
    matching_total = query.count()
    records = query.order_by(RawRecord.created_at.desc()).limit(limit).all()

    results = []
    summary: dict[str, int] = {}
    for r in records:
        data = r.data or {}
        results.append({"id": r.id, "data": data, "created_at": r.created_at})
        ft = data.get("facility_type", "unknown")
        summary[ft] = summary.get(ft, 0) + 1

    result = {
        "items": results,
        "total": len(results),
        "matching_total": matching_total,
        "summary_by_type": summary,
    }
    if len(_education_facilities_cache) >= _EDUCATION_FACILITIES_CACHE_MAX_KEYS:
        _education_facilities_cache.clear()
    _education_facilities_cache[cache_key] = {"data": result, "computed_at": now}
    return result


_region_stats_cache: dict = {"data": None, "computed_at": 0.0}
_REGION_STATS_CACHE_TTL = 600  # 초 — 아래 참고


_REGION_STAT_TARGETS = [
    ("서울특별시", "강남구"),
    ("서울특별시", "서초구"),
    ("서울특별시", "송파구"),
    ("서울특별시", "마포구"),
    ("서울특별시", "노원구"),
    ("부산광역시", None),
    ("대구광역시", None),
    ("인천광역시", None),
    ("광주광역시", None),
    ("대전광역시", None),
    ("울산광역시", None),
    ("세종특별자치시", None),
    (None, "수원시"),
    (None, "창원시"),
    (None, "청주시"),
    (None, "전주시"),
    (None, "춘천시"),
    (None, "제주시"),
    (None, "목포시"),
    (None, "포항시"),
]


@app.get("/region-stats")
def region_stats(db: Session = Depends(get_db)):
    """전국 시군구별 시설 유형 카운트 집계.

    대시보드의 "격차 계산기"가 지역별 academy_count/gap_index를 하드코딩된 가짜 숫자
    대신 실제 크롤링 데이터로 보여주는 데 쓴다. 로우 전체를 Python으로 끌어오지 않고
    SQL GROUP BY로 DB가 집계하게 한다 — 오늘 겪은 OOM(수만 건을 메모리로 올려 인스턴스
    재시작)이 재발하지 않도록.

    긴급: 배포 직후 raw_records가 12만 건대로 커진 상태에서 대시보드가 30초마다
    이 엔드포인트를 호출하면서(여러 탭 동시 접속 시 더 심함) json_extract GROUP BY가
    반복 실행돼 SQLite 락 경합으로 서버 전체가 응답 불가(health check까지 타임아웃)에
    빠졌다. 결과가 자주 바뀌는 데이터가 아니므로 프로세스 메모리에 캐싱해 실제 집계는
    캐시가 만료됐을 때만 한 번 실행되게 한다.

    추가 수정: 캐시 미스일 때도 여전히 _REGION_STAT_TARGETS(20개 지역)마다 별도
    쿼리로 raw_records를 풀스캔했다 — 캐시가 만료된 순간 20번의 풀스캔이 몰려
    응답 불가가 재발했다. GROUP BY 한 번으로 전체 지역/시군구 집계를 끝내고,
    타겟 목록은 그 결과에서 조회만 하도록 바꿔 풀스캔을 20회 -> 1회로 줄인다.
    """
    now = time.monotonic()
    if _region_stats_cache["data"] is not None and now - _region_stats_cache["computed_at"] < _REGION_STATS_CACHE_TTL:
        return _region_stats_cache["data"]

    # 예전엔 json_extract(data, '$.region') 등으로 걸러 raw_records를 풀스캔했다 — 실제
    # 컬럼으로 승격된 facility_type/region/district를 쓰면 인덱스를 태운다(백필: backfill_facility_columns.py).
    grouped = (
        db.query(RawRecord.region, RawRecord.district, func.count(RawRecord.id))
        .filter(
            RawRecord.item_type == "EducationFacilityItem",
            RawRecord.facility_type == "academy",
        )
        .group_by(RawRecord.region, RawRecord.district)
        .all()
    )
    by_region_and_district: dict[tuple[str | None, str | None], int] = {}
    by_region_total: dict[str, int] = {}
    by_district_total: dict[str, int] = {}
    for region, district, count in grouped:
        by_region_and_district[(region, district)] = count
        if region:
            by_region_total[region] = by_region_total.get(region, 0) + count
        if district:
            by_district_total[district] = by_district_total.get(district, 0) + count

    districts = []
    academy_counts = []
    for region, district in _REGION_STAT_TARGETS:
        if region and district:
            academy_count = by_region_and_district.get((region, district), 0)
        elif district:
            academy_count = by_district_total.get(district, 0)
        else:
            academy_count = by_region_total.get(region, 0)
        academy_counts.append(academy_count)
        districts.append(
            {
                "region": region or "",
                "district": district or region or "",
                "counts": {"academy": academy_count},
                "academy_count": academy_count,
            }
        )

    # 학원 수 기반 상대 지수(0~1) — 인구 대비 정규화가 아니라 전국 시군구 중 상대적
    # 위치만 나타낸다. 정밀한 지표인 척하지 않는다.
    lo = min(academy_counts) if academy_counts else 0
    hi = max(academy_counts) if academy_counts else 0
    span = (hi - lo) or 1
    for d in districts:
        d["gap_index"] = round((d["academy_count"] - lo) / span, 4)

    result = {
        "districts": districts,
        "note": "gap_index는 대시보드 주요 지역의 학원 수 기반 상대 지수(min-max 정규화)이며 인구 대비 정규화는 아님",
    }
    _region_stats_cache["data"] = result
    _region_stats_cache["computed_at"] = now
    return result


_site_stats_cache: dict = {"data": None, "computed_at": 0.0}
_SITE_STATS_CACHE_TTL = 120  # 초 — 랜딩페이지 지표라 실시간성이 중요하지 않다. COUNT 7개가 방문마다
# 몰리는 걸 흡수해 DB 커넥션 풀 고갈(QueuePool timeout)에 조금이라도 덜 기여하게 한다.


@app.get("/site-stats")
def site_stats(db: Session = Depends(get_db)):
    """랜딩페이지("숫자로 먼저 보여드립니다" 섹션)가 쓰는 실제 운영 지표.

    전부 단순 COUNT 쿼리 — 무거운 집계 없음. 예전엔 이 숫자들이 landing.html에
    하드코딩된 시안용 예시치("1,842개 학원 커리큘럼" 등)였다.
    """
    now_monotonic = time.monotonic()
    if _site_stats_cache["data"] is not None and now_monotonic - _site_stats_cache["computed_at"] < _SITE_STATS_CACHE_TTL:
        return _site_stats_cache["data"]

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    facility_records = (
        db.query(func.count(RawRecord.id)).filter(RawRecord.item_type == "EducationFacilityItem").scalar()
    )
    curriculum_items = db.query(func.count(RawRecord.id)).filter(RawRecord.item_type == "CurriculumItem").scalar()
    admission_data_points = (
        db.query(func.count(RawRecord.id)).filter(RawRecord.item_type == "AdmissionResultItem").scalar()
    )
    reports_issued = db.query(func.count(ConsultingReport.id)).scalar()
    active_members = db.query(func.count(User.id)).scalar()
    posts_today = db.query(func.count(CommunityPost.id)).filter(CommunityPost.created_at >= today_start).scalar()
    comments_this_week = db.query(func.count(Comment.id)).filter(Comment.created_at >= week_ago).scalar()

    result = {
        "facility_records": facility_records or 0,
        "curriculum_items": curriculum_items or 0,
        "admission_data_points": admission_data_points or 0,
        "reports_issued": reports_issued or 0,
        "active_members": active_members or 0,
        "posts_today": posts_today or 0,
        "comments_this_week": comments_this_week or 0,
    }
    _site_stats_cache["data"] = result
    _site_stats_cache["computed_at"] = now_monotonic
    return result


# ── 전국 공공 CCTV (국가교통정보센터 ITS, 도로 구간만) ────────────────────────

@app.get("/cctv", response_model=CctvResponse)
def list_cctv(
    min_x: float = cctv.KOREA_BBOX["min_x"],
    min_y: float = cctv.KOREA_BBOX["min_y"],
    max_x: float = cctv.KOREA_BBOX["max_x"],
    max_y: float = cctv.KOREA_BBOX["max_y"],
    cctv_type: int = 1,
):
    """bbox(경도/위도) 내 공공 도로 CCTV 목록. 기본값은 전국 범위.

    ITS_API_KEY 미설정 시 빈 목록을 반환한다 — 시설(어린이집·학교) 내부 CCTV는
    법적으로 열람 권한이 없어 다루지 않으며, 오직 도로 구간 CCTV만 대상이다.
    """
    items = cctv.fetch_cctv(min_x, min_y, max_x, max_y, cctv_type)
    return CctvResponse(items=[CctvInfo(**i) for i in items], total=len(items))


# ── 실시간 교육 동영상 (YouTube Data API) ─────────────────────────────────────

@app.get("/youtube-video")
def youtube_video(q: str):
    """검색어에 맞는 최신 영상 1건. listType=search 임베드 트릭 대신 정식 Data API로
    실제 videoId를 찾아 표준 embed URL을 쓸 수 있게 한다.

    YOUTUBE_API_KEY 미설정 또는 검색 결과 없음 시 result: null 반환.
    """
    return {"result": youtube.search_video(q)}


# ── 실시간 교육 뉴스 (네이버 뉴스 검색 오픈API) ────────────────────────────────

_EDUCATION_NEWS_QUERIES = ["수능", "대입", "교육부", "학원", "교육정책"]

# 교육 전문 매체 화이트리스트 — "교육" 단어가 우연히 들어간 무관한 기사(인사 발령,
# 지역 소식 등)를 걸러내기 위해 아래 매체의 기사만 노출한다.
_EDU_MEDIA_DOMAINS = {
    "news.unn.net",  # 한국대학신문
    "veritas-a.com",  # 베리타스알파
    "dhnews.co.kr",  # 대학저널
    "chosunedu.co.kr",  # 조선에듀
    "edunews.or.kr",  # 에듀뉴스
    "kedupress.com",  # 대한민국교육신문
    "eduyonhap.com",  # 교육연합신문
    "ebs.co.kr",  # EBS
    "ebsi.co.kr",  # EBSi
    "edudonga.com",  # 에듀동아
}

# 화이트리스트 매체는 발행량이 적어 주제어 검색만으로는 잘 안 걸리므로,
# 매체명 자체도 검색어로 써서 최근 기사를 직접 끌어온다.
_EDU_MEDIA_NAME_QUERIES = [
    "한국대학신문", "베리타스알파", "대학저널", "조선에듀",
    "에듀뉴스", "대한민국교육신문", "교육연합신문", "에듀동아",
]


# 학부모 관련 기사는 입시전문매체(위 화이트리스트) 발행량이 적어 잘 안 걸린다 —
# 실제 검색해보니 오마이뉴스·서울경제·이투데이 등 종합 일간지/매체에서 주로 나온다.
# 그래서 별도로 신뢰할 수 있는 종합 언론사 화이트리스트를 둔다(연예/스포츠 매체 제외).
_PARENTS_MEDIA_DOMAINS = {
    "chosun.com", "joongang.co.kr", "joins.com", "donga.com",  # 조선/중앙/동아
    "hani.co.kr", "khan.co.kr",  # 한겨레/경향
    "yna.co.kr",  # 연합뉴스
    "kbs.co.kr", "sbs.co.kr", "imbc.com", "mbc.co.kr",  # 지상파
    "ohmynews.com", "sedaily.com", "etoday.co.kr",  # 오마이뉴스/서울경제/이투데이
}


def _matches_domain(url: str, domains: set[str]) -> bool:
    # "khan.co.kr" in url 같은 부분 문자열 검사는 sports.khan.co.kr(연예/스포츠),
    # realty.chosun.com(부동산) 같은 화이트리스트 매체의 무관한 서브도메인까지
    # 통과시킨다 — 호스트 전체를 정확히 비교해서 본지 도메인만 남긴다.
    host = urlparse(url).netloc
    return any(host == d or host == f"www.{d}" for d in domains)


def _search_news_by_domains(queries: list[str], domains: set[str], limit: int) -> dict:
    """검색어 목록으로 네이버 뉴스를 동시 검색해 지정된 매체 화이트리스트만 걸러
    최신순으로 반환. /education-news와 /parents-news가 검색어·화이트리스트만 다르게
    해서 공유한다."""
    with ThreadPoolExecutor(max_workers=len(queries)) as executor:
        results = executor.map(lambda q: naver_news.search_news(q, display=10), queries)

    seen_urls: set[str] = set()
    merged: list[dict] = []
    for items in results:
        for item in items:
            if item["url"] in seen_urls or not _matches_domain(item["url"], domains):
                continue
            seen_urls.add(item["url"])
            merged.append(item)

    merged.sort(key=lambda x: x["pub_date"] or "", reverse=True)
    return {"items": merged[:limit], "total": len(merged)}


@app.get("/education-news")
def education_news(limit: int = 20):
    """교육 전문 매체(화이트리스트)의 최신 기사만 모아 최신순으로 반환.

    NAVER_CLIENT_ID/SECRET 미설정 시 빈 목록 반환. 검색어가 13개라 순차 호출하면
    캐시가 비어있을 때 100초 이상 걸릴 수 있어 동시에 호출한다.
    """
    return _search_news_by_domains(_EDUCATION_NEWS_QUERIES + _EDU_MEDIA_NAME_QUERIES, _EDU_MEDIA_DOMAINS, limit)


_PARENTS_NEWS_QUERIES = ["학부모", "학부모 교육", "자녀교육", "학부모 상담"]


@app.get("/parents-news")
def parents_news(limit: int = 20):
    """학부모On누리(www.parents.go.kr) 관련 최신 기사.

    학부모On누리는 robots.txt가 모든 크롤러(구글·네이버·다음 자체 검색봇 제외)를 막고
    있고 콘텐츠 Open API도 없어, 사이트 자체 콘텐츠를 직접 가져올 수 없다(이 프로젝트는
    ROBOTSTXT_OBEY=True를 항상 지킨다 — crawler/edu_crawler/settings.py 참고). 대신
    이미 연동돼 있는 네이버 뉴스 오픈API로 '학부모' 관련 종합 언론사 기사를 모아
    비슷한 실시간 피드를 제공한다 — 학부모On누리 자체 게시물이 아니라 관련 뉴스임을
    프런트에서 명확히 표시해야 한다.
    """
    return _search_news_by_domains(_PARENTS_NEWS_QUERIES, _PARENTS_MEDIA_DOMAINS, limit)


# ── 예측 모델 ─────────────────────────────────────────────────────────────────

@app.get("/predict-missing-cutoffs")
def predict_missing_cutoffs(db: Session = Depends(get_db)):
    return imputation.predict_missing_cutoffs(db)


@app.post("/psych-assessment", response_model=PsychAssessmentResponse)
def psych_assessment(req: PsychAssessmentRequest):
    scores = psychology_engine.score_assessment(req.answers, req.answers_by_source)
    return PsychAssessmentResponse(scores=scores, narrative=psychology_engine.to_consulting_context(scores))


@app.post("/predict-dropout-risk", response_model=DropoutRiskResponse)
def predict_dropout_risk(req: DropoutRiskRequest, db: Session = Depends(get_db)):
    result = predictive_model.predict_dropout_risk(db, req.student_features)
    return DropoutRiskResponse(**result)


@app.post("/qcrm-assessment", response_model=QcrmAssessmentResponse)
def qcrm_assessment(req: QcrmAssessmentRequest):
    result = qcrm_engine.run_mini_qcrm(req.profile, req.profiles_by_source, req.iterations)
    return QcrmAssessmentResponse(**result, narrative=qcrm_engine.to_consulting_context(result))


# ── 리포트 생성 ───────────────────────────────────────────────────────────────

@app.post("/reports", response_model=ReportResponse)
def create_report(req: ReportRequest, db: Session = Depends(get_db)):
    psych_scores = None
    psych_context = ""
    if req.psych_answers:
        psych_scores = psychology_engine.score_assessment(req.psych_answers)
        psych_context = psychology_engine.to_consulting_context(psych_scores)

    risk_context = ""
    if req.student_features:
        risk_result = predictive_model.predict_dropout_risk(db, req.student_features)
        risk_context = predictive_model.to_consulting_context(risk_result)

    qcrm_context = ""
    if req.qcrm_profile:
        qcrm_result = qcrm_engine.run_mini_qcrm(req.qcrm_profile)
        qcrm_context = qcrm_engine.to_consulting_context(qcrm_result)

    combined_psych_context = "\n\n".join(filter(None, [psych_context, risk_context, qcrm_context]))

    try:
        report_text, variant = ai_engine.generate_report(
            db, req.student_label, req.tier, req.profile,
            req.context_item_types, combined_psych_context,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    record = ConsultingReport(
        student_label=req.student_label,
        tier=req.tier,
        input_summary=str(req.profile),
        psych_scores=psych_scores,
        student_features=req.student_features,
        prompt_variant=variant,
        report_text=report_text,
    )
    db.add(record)
    db.commit()
    return ReportResponse(
        id=record.id,
        student_label=record.student_label,
        tier=record.tier,
        prompt_variant=record.prompt_variant,
        report_text=record.report_text,
    )


@app.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db)):
    record = db.get(ConsultingReport, report_id)
    if not record:
        raise HTTPException(status_code=404, detail="report not found")
    return ReportResponse(
        id=record.id,
        student_label=record.student_label,
        tier=record.tier,
        prompt_variant=record.prompt_variant,
        report_text=record.report_text,
    )


# ── 피드백 수집 (루프 핵심 입력) ─────────────────────────────────────────────

@app.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(req: FeedbackRequest, db: Session = Depends(get_db)):
    """리포트에 대한 평점·실제 결과를 제출한다. 누적된 피드백은 자동 재학습에 사용된다."""
    report = db.get(ConsultingReport, req.report_id)
    if not report:
        raise HTTPException(status_code=404, detail="report not found")

    fb = FeedbackRecord(
        report_id=req.report_id,
        student_label=req.student_label,
        rating=req.rating,
        comment=req.comment,
        actual_outcome=req.actual_outcome,
        processed=False,
    )
    db.add(fb)
    db.commit()

    unprocessed = feedback_loop.unprocessed_count(db)
    until_retrain = max(0, feedback_loop.RETRAIN_THRESHOLD - unprocessed)

    # 임계치 즉시 도달 시 동기 재학습 트리거 (백그라운드 스케줄러보다 빠르게 반응)
    if feedback_loop.should_retrain(db):
        asyncio.get_event_loop().run_in_executor(
            None,
            lambda: _sync_retrain("feedback_threshold"),
        )
        message = f"피드백 접수 완료 (평점 {req.rating}/5). 재학습 임계치 도달 — 백그라운드에서 루프 사이클이 시작됩니다."
    else:
        message = f"피드백 접수 완료 (평점 {req.rating}/5). 재학습까지 {until_retrain}건 남았습니다."

    return FeedbackResponse(id=fb.id, report_id=fb.report_id, rating=fb.rating, message=message)


def _sync_retrain(trigger: str) -> None:
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        feedback_loop.run_retrain_cycle(db, trigger=trigger)
    except Exception as exc:
        logger.error("백그라운드 재학습 오류: %s", exc)
    finally:
        db.close()


# ── 루프 상태 조회 ────────────────────────────────────────────────────────────

@app.get("/loop-status", response_model=LoopStatusResponse)
def loop_status(db: Session = Depends(get_db)):
    """자가진화 루프의 현재 상태 — 활성 프롬프트 변형, 피드백 누적 현황, 정확도 추이."""
    return LoopStatusResponse(**feedback_loop.get_loop_status(db))


@app.post("/loop-trigger")
def manual_loop_trigger(db: Session = Depends(get_db)):
    """수동으로 루프 사이클을 즉시 실행한다 (테스트·관리용)."""
    metric = feedback_loop.run_retrain_cycle(db, trigger="manual")
    return {
        "message": "루프 사이클 완료",
        "metric_id": metric.id,
        "accuracy_before": metric.accuracy_before,
        "accuracy_after": metric.accuracy_after,
        "prompt_variant_switched": metric.prompt_variant_switched,
        "active_prompt_variant": metric.active_prompt_variant,
        "notes": metric.notes,
    }


# ── 컨설팅 방법론 3종 실제 모델 엔드포인트 ───────────────────────────────────────

class TimeseriesRequest(BaseModel):
    """월별 성적/출결 시계열 (최근 N개, 오름차순). 값은 0~100 정규 점수."""
    values: list[float]
    horizon: int = 3


class TimeseriesResponse(BaseModel):
    trend: float
    forecast: list[float]
    change_point_idx: int | None
    note: str


@app.post("/timesfm-predict", response_model=TimeseriesResponse)
def timesfm_predict(req: TimeseriesRequest):
    """TimesFM 계열 시계열 기초모델 참조 경량 예측 (선형추세+이동평균 잔차보정)."""
    import statistics
    vals = [float(v) for v in req.values if v is not None]
    if len(vals) < 2:
        raise HTTPException(status_code=400, detail="최소 2개 이상의 시계열 값이 필요합니다.")
    n = len(vals)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(vals) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((xs[i] - mean_x) * (vals[i] - mean_y) for i in range(n)) / denom if denom else 0.0
    ma = []
    for i in range(n):
        lo = max(0, i - 2)
        ma.append(statistics.mean(vals[lo:i + 1]))
    resid = vals[-1] - ma[-1]
    forecast = []
    for h in range(1, req.horizon + 1):
        nxt = vals[-1] + slope * h + resid * (0.6 ** h)
        forecast.append(round(max(0.0, min(100.0, nxt)), 1))
    change_point = None
    for i in range(1, n):
        if (vals[i] - vals[i - 1]) * (vals[i - 1] - (vals[i - 2] if i >= 2 else vals[0])) < 0:
            change_point = n - i
    note = "상승 추세" if slope > 0.5 else "하락 추세" if slope < -0.5 else "정체"
    return TimeseriesResponse(trend=round(slope, 2), forecast=forecast,
                              change_point_idx=change_point,
                              note=f"월평균 {note} (기울기 {round(slope, 2)}) — 향후 {req.horizon}개월 예측")


class UnderstandRequest(BaseModel):
    student: str = ""
    parent: str = ""
    teacher: str = ""


class UnderstandResponse(BaseModel):
    summary: str
    conflicts: list[str]
    actions: list[str]


@app.post("/understand-analyze", response_model=UnderstandResponse)
def understand_analyze(req: UnderstandRequest):
    """다자 간 맥락 이해 모델 (Egonex-AI/Understand-Anything 참조)."""
    s, p, t = req.student.strip(), req.parent.strip(), req.teacher.strip()
    parts = [x for x in [s, p, t] if x]
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="최소 2명 이상의 입력이 필요합니다.")
    conflict_kw = {
        "성적": "성적에 대한 기대 차이가 있을 수 있습니다.",
        "스트레스": "학생의 스트레스 신호가 감지됩니다.",
        "모르겠": "의도/상황 파악이 불명확합니다.",
        "바빠": "학부모의 시간 부족으로 소통이 끊길 수 있습니다.",
        "요구": "요구사항 충돌 가능성이 있습니다.",
        "비싸": "비용 부담 이슈가 있습니다.",
        "못 따라": "학습 진도 격차 우려가 있습니다.",
    }
    conflicts = [msg for kw, msg in conflict_kw.items() if kw in f"{s} {p} {t}"]
    if not conflicts:
        conflicts.append("특별한 갈등 신호는 감지되지 않았습니다.")
    summary = (f"학생은 '{s[:30] or '미입력'}'를, 학부모는 '{p[:30] or '미입력'}'를, "
               f"교사는 '{t[:30] or '미입력'}'를 전달했습니다. 세 주체의 의도와 상황을 정리했습니다.")
    actions = [
        "학생에게는 현재 상태를 비언어적으로 확인하는 1:1 체크인을 권장합니다.",
        "학부모에게는 기대치를 구체적 목표로 환산해 공유합니다.",
        "교사에게는 학생의 행동 신호를 주간 리포트로 전달할 것을 제안합니다.",
    ]
    return UnderstandResponse(summary=summary, conflicts=conflicts, actions=actions)


class RtiPbisRequest(BaseModel):
    score_gap: float
    behavior_incidents: int
    attendance_rate: float


class RtiPbisResponse(BaseModel):
    rti_tier: int
    pbis_level: str
    plan: list[str]


@app.post("/rti-pbis-assess", response_model=RtiPbisResponse)
def rti_pbis_assess(req: RtiPbisRequest):
    """RTI 3-tier + PBIS 단계 진단."""
    gap = max(0.0, min(100.0, req.score_gap))
    inc = max(0, req.behavior_incidents)
    att = max(0.0, min(100.0, req.attendance_rate))
    if gap >= 40 or inc >= 3:
        rti_tier = 3
    elif gap >= 20 or inc >= 1:
        rti_tier = 2
    else:
        rti_tier = 1
    if att < 85 or inc >= 3:
        pbis = "집중 지원 (Tier 3)"
    elif att < 92 or inc >= 1:
        pbis = "선택 지원 (Tier 2)"
    else:
        pbis = "보편 지원 (Tier 1)"
    plan = ["Tier 1: 보편적 검증 교수 + 주 단위 모니터링"]
    if rti_tier >= 2:
        plan.append("Tier 2: 소집단 보충 지도(8~10명) + 진행도 주단위 평가")
    if rti_tier >= 3:
        plan.append("Tier 3: 개별 집중 중재 + 전문가 평가 연계")
    if "Tier 3" in pbis:
        plan.append("PBIS: 기능평가(FBA) 기반 행동지원계획(BIP) 수립")
    elif "Tier 2" in pbis:
        plan.append("PBIS: 체크인/체크아웃(CICO) 정기 멘토링")
    else:
        plan.append("PBIS: 명시적 기대 교습 + 긍정적 피드백 정례화")
    return RtiPbisResponse(rti_tier=rti_tier, pbis_level=pbis, plan=plan)


# ── RTI · PBIS 통합 시스템 (실제 아키텍처) ──────────────────────────────────────

from app.rti_pbis_models import (
    Base as RtiBase, Student, UniversalScreening, ProgressMonitoringAcademic,
    ProgressMonitoringBehavior, Intervention, FidelityRecord,
)
from app import rti_pbis_engine

# 테이블 자동 생성 (기존 engine 재사용 — SQLite/PostgreSQL 호환)
RtiBase.metadata.create_all(bind=engine)


class StudentCreate(BaseModel):
    student_id: str
    school_id: str | None = None
    grade_level: int | None = None
    classroom: str | None = None
    demographics: str | None = None


class ScreeningCreate(BaseModel):
    student_id: str
    screening_date: str | None = None  # YYYY-MM-DD
    reading_benchmark_score: float | None = None
    math_percentile_rank: float | None = None
    social_skills_rating: float | None = None
    behavioral_risk_index: float | None = None


class InterventionCreate(BaseModel):
    student_id: str
    intervention_id: str
    tier: int = 1
    assigned_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    status: str = "진행 중"
    delivery_details: str | None = None
    fba_hypothesis: str | None = None


class AcademicPMCreate(BaseModel):
    student_id: str
    intervention_id: int | None = None
    date: str | None = None
    curriculum_based_measurement_score: float
    note: str | None = None


class BehaviorPMCreate(BaseModel):
    student_id: str
    intervention_id: int | None = None
    date: str | None = None
    daily_behavior_rating: float | None = None
    cico_points_earned: float | None = None
    note: str | None = None


class FidelityCreate(BaseModel):
    intervention_id: int
    observer: str | None = None
    date: str | None = None
    fidelity_score: float


class FbaIncident(BaseModel):
    antecedent: str = ""
    behavior: str = ""
    consequence: str = ""


def _as_date(s: str | None):
    from datetime import date, datetime
    if not s:
        return date.today()
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


@app.post("/rti/student")
def create_student(req: StudentCreate, db: Session = Depends(get_db)):
    """학생 기본 정보 등록 (Student Core)."""
    if db.query(Student).filter(Student.student_id == req.student_id).first():
        raise HTTPException(status_code=409, detail="이미 존재하는 student_id")
    s = Student(**req.model_dump())
    db.add(s); db.commit(); db.refresh(s)
    return {"student_id": s.student_id, "status": "등록 완료"}


@app.post("/rti/screening")
def create_screening(req: ScreeningCreate, db: Session = Depends(get_db)):
    """보편적 스크리닝 등록 + 위험도 자동 식별."""
    if not db.query(Student).filter(Student.student_id == req.student_id).first():
        raise HTTPException(status_code=404, detail="학생 없음")
    s = UniversalScreening(
        student_id=req.student_id, screening_date=_as_date(req.screening_date),
        reading_benchmark_score=req.reading_benchmark_score,
        math_percentile_rank=req.math_percentile_rank,
        social_skills_rating=req.social_skills_rating,
        behavioral_risk_index=req.behavioral_risk_index,
    )
    db.add(s); db.commit(); db.refresh(s)
    risk = rti_pbis_engine.identify_risk(s)
    return {"screening_id": s.id, "risk": risk}


@app.post("/rti/intervention")
def create_intervention(req: InterventionCreate, db: Session = Depends(get_db)):
    """중재 배정 (Intervention)."""
    if not db.query(Student).filter(Student.student_id == req.student_id).first():
        raise HTTPException(status_code=404, detail="학생 없음")
    iv = Intervention(
        student_id=req.student_id, intervention_id=req.intervention_id, tier=req.tier,
        assigned_date=_as_date(req.assigned_date), start_date=_as_date(req.start_date),
        end_date=_as_date(req.end_date) if req.end_date else None,
        status=req.status, delivery_details=req.delivery_details, fba_hypothesis=req.fba_hypothesis,
    )
    db.add(iv); db.commit(); db.refresh(iv)
    return {"intervention_db_id": iv.id, "type": iv.intervention_id, "tier": iv.tier, "status": iv.status}


@app.post("/rti/pm-academic")
def create_academic_pm(req: AcademicPMCreate, db: Session = Depends(get_db)):
    """학업 진도 모니터링 기록 (CBM)."""
    pm = ProgressMonitoringAcademic(
        student_id=req.student_id, intervention_id=req.intervention_id,
        date=_as_date(req.date), curriculum_based_measurement_score=req.curriculum_based_measurement_score,
        note=req.note)
    db.add(pm); db.commit(); db.refresh(pm)
    return {"pm_id": pm.id, "date": str(pm.date), "score": pm.curriculum_based_measurement_score}


@app.post("/rti/pm-behavior")
def create_behavior_pm(req: BehaviorPMCreate, db: Session = Depends(get_db)):
    """행동 진도 모니터링 기록 (일일점수/CICO)."""
    pm = ProgressMonitoringBehavior(
        student_id=req.student_id, intervention_id=req.intervention_id, date=_as_date(req.date),
        daily_behavior_rating=req.daily_behavior_rating, cico_points_earned=req.cico_points_earned, note=req.note)
    db.add(pm); db.commit(); db.refresh(pm)
    return {"pm_id": pm.id, "date": str(pm.date), "rating": pm.daily_behavior_rating}


@app.post("/rti/fidelity")
def create_fidelity(req: FidelityCreate, db: Session = Depends(get_db)):
    """충실도 측정 기록."""
    f = FidelityRecord(intervention_id=req.intervention_id, observer=req.observer,
                       date=_as_date(req.date), fidelity_score=req.fidelity_score)
    db.add(f); db.commit(); db.refresh(f)
    return {"fidelity_id": f.id, "score": f.fidelity_score}


@app.post("/rti/fba")
def analyze_fba(req: list[FbaIncident]):
    """FBA 지원: A-B-C 사건 로그 → 기능적 가설 도출."""
    incidents = [i.model_dump() for i in req]
    return rti_pbis_engine.analyze_fba(incidents)


@app.get("/rti/profile/{student_id}")
def unified_profile(student_id: str, db: Session = Depends(get_db)):
    """통합 학생 프로필 (학업·행동·중재 이력 한눈에)."""
    return rti_pbis_engine.build_unified_profile(db, student_id)


# ── 시계열 성적·행동 예측 시스템 (TimesFM 참조 아키텍처) ────────────────────────────
class PredictionRequest(BaseModel):
    student_id: int
    subject_ids: Optional[list[int]] = None
    horizon: int = 12
    include_behavioral: bool = False


class PredictionResponse(BaseModel):
    student_id: int
    predictions: dict
    recommendations: list
    timestamp: str


@app.post("/api/predict/student/{student_id}")
def predict_student_performance(student_id: int, req: PredictionRequest, db: Session = Depends(get_db)):
    """학생 성적 예측 API (명세 6절)."""
    system = timeseries_engine.ComprehensivePredictionSystem(db)
    try:
        if req.subject_ids:
            predictions = system.predictor.predict_multi_subject(db, student_id, req.subject_ids, req.horizon)
        else:
            report = system.generate_student_report(student_id, req.horizon)
            predictions = report["performance_trends"]
        recommendations = []
        if req.subject_ids is None:
            report = system.generate_student_report(student_id, req.horizon)
            recommendations = report["intervention_recommendations"]
        return PredictionResponse(
            student_id=student_id, predictions=predictions,
            recommendations=recommendations, timestamp=datetime.now().isoformat())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analysis/subject/{student_id}/{subject_id}")
def analyze_subject_performance(student_id: int, subject_id: int, db: Session = Depends(get_db)):
    """과목별 상세 분석 API (명세 6절)."""
    system = timeseries_engine.ComprehensivePredictionSystem(db)
    analysis = {
        "subject_analysis": system.analyzer.analyze_by_difficulty(db, student_id, subject_id),
        "term_analysis": system.analyzer.analyze_by_term(db, student_id, subject_id),
        "forecast": system.predictor.forecast_performance(db, student_id, subject_id),
        "recommendations": system._generate_intervention(
            system._analyze_subject_detailed(student_id, subject_id)),
    }
    return analysis


@app.get("/api/dashboard/student/{student_id}")
def get_student_dashboard(student_id: int, db: Session = Depends(get_db)):
    """학생 대시보드 데이터 API (명세 6절)."""
    system = timeseries_engine.ComprehensivePredictionSystem(db)
    report = system.generate_student_report(student_id)
    return {
        "overall_performance": report["subject_analysis"],
        "risk_assessment": report["risk_assessment"],
        "interventions": report["intervention_recommendations"],
        "trends": report["performance_trends"],
        "backend": report["backend"],
    }


# ─────────────────────────────────────────────────────────────
# 방법 02 · 교육 컨설팅 상호이해 모델 (Understand-Anything 아키텍처 변환)
# ─────────────────────────────────────────────────────────────
class UnderstandAnalyzeRequest(BaseModel):
    student: str = ""
    parent: str = ""
    teacher: str = ""


class UnderstandSessionRequest(BaseModel):
    student: str = ""
    parent: str = ""
    teacher: str = ""


@app.post("/api/understand/analyze")
def understand_analyze(req: UnderstandAnalyzeRequest, db: Session = Depends(get_db)):
    """다중 에이전트 파이프라인 전체 실행 (프로필→지식그래프→분석→리포트→실행계획)."""
    raw = {"student": req.student, "parent": req.parent, "teacher": req.teacher}
    try:
        result = understanding_engine.run_full_analysis(db, raw)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/understand/session/{session_id}")
def understand_session(session_id: str, db: Session = Depends(get_db)):
    """세션의 상호이해 점수·갭·강점·리포트 조회."""
    sess = db.query(understanding_models.UnderstandingSession).filter(
        understanding_models.UnderstandingSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="세션 없음")
    mus = db.query(understanding_models.MutualUnderstandingScores).filter(
        understanding_models.MutualUnderstandingScores.session_id == session_id).first()
    gaps = db.query(understanding_models.GapAnalysis).filter(
        understanding_models.GapAnalysis.session_id == session_id).all()
    strengths = db.query(understanding_models.StrengthAnalysis).filter(
        understanding_models.StrengthAnalysis.session_id == session_id).all()
    rep = db.query(understanding_models.ConsultingReport).filter(
        understanding_models.ConsultingReport.session_id == session_id).first()
    return {
        "session_id": session_id,
        "type": sess.type,
        "participants": sess.participants,
        "mutual_scores": {
            "understanding": mus.understanding if mus else {},
            "empathy": mus.empathy if mus else {},
            "communication": mus.communication if mus else {},
            "overall": mus.overall if mus else None,
        },
        "gaps": [{"type": g.type, "description": g.description, "severity": g.severity,
                  "actors": g.related_actors, "actions": g.recommended_actions} for g in gaps],
        "strengths": [{"type": s.type, "description": s.description,
                       "actors": s.related_actors} for s in strengths],
        "report": {
            "id": rep.id if rep else None,
            "title": rep.title if rep else None,
            "summary": rep.summary if rep else None,
            "versions": rep.versions if rep else {},
        } if rep else None,
        "backend": "statistical-fallback",
    }


@app.get("/api/understand/report/{report_id}")
def understand_report(report_id: str, db: Session = Depends(get_db)):
    """페르소나별 컨설팅 리포트 버전 조회."""
    rep = db.query(understanding_models.ConsultingReport).filter(
        understanding_models.ConsultingReport.id == report_id).first()
    if not rep:
        raise HTTPException(status_code=404, detail="리포트 없음")
    return {
        "id": rep.id,
        "title": rep.title,
        "summary": rep.summary,
        "versions": rep.versions,
        "next_steps": rep.next_steps,
        "permissions": rep.permissions,
        "backend": "statistical-fallback",
    }

