import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import ai_engine, cctv, feedback_loop, imputation, naver_news, predictive_model, psychology_engine, qcrm_engine, youtube
from app import models_community  # noqa: F401 - Base.metadata에 커뮤니티 테이블을 등록시키기 위한 import
from app.models_community import Comment, CommunityPost, User
from app import models_reputation  # noqa: F401 - Base.metadata에 학원 평판 테이블을 등록시키기 위한 import
from app.database import Base, engine, get_db
from app.models import ConsultingReport, FeedbackRecord, RawRecord
from app.routers import admin, committee, community, mom_cafe, news, reputation
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
    Base.metadata.create_all(bind=engine)
    # 운영 DB의 raw_records가 수만 건 규모라 CREATE INDEX/ANALYZE를 앱 시작(lifespan) 경로에
    # 동기로 넣었더니 기동 자체가 헬스체크 타임아웃을 넘겨버려 502를 유발했다 — 되돌림.
    # 인덱스 보정은 별도 1회성 스크립트로 오프라인에서 실행할 것(앱 기동 경로에 넣지 않는다).
    from app.database import SessionLocal
    db = SessionLocal()
    try:
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
app.include_router(news.router)
app.include_router(mom_cafe.router)
app.include_router(admin.router)
app.include_router(committee.router)
app.include_router(reputation.router)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── 정적 페이지 ───────────────────────────────────────────────────────────────

@app.get("/")
def index():
    # 통합된 랜딩 페이지(마케팅 + 리포트 체험 폼)를 기본 페이지로 제공.
    return FileResponse(STATIC_DIR / "landing.html")


@app.get("/landing")
def landing():
    return FileResponse(STATIC_DIR / "landing.html")


@app.get("/health")
def health():
    return {"status": "ok"}


# ── 크롤러 데이터 적재 ────────────────────────────────────────────────────────

@app.post("/ingest")
def ingest(payload: IngestPayload, db: Session = Depends(get_db)):
    record = RawRecord(
        item_type=payload.item_type,
        data=payload.data,
        source_url=payload.data.get("source_url", ""),
    )
    db.add(record)
    db.commit()
    return {"id": record.id}


@app.post("/ingest-batch")
def ingest_batch(payloads: list[IngestPayload], db: Session = Depends(get_db)):
    """대량 크롤링(학원 등)에서 건별 요청 왕복 비용을 줄이기 위한 일괄 적재."""
    records = [
        RawRecord(
            item_type=p.item_type,
            data=p.data,
            source_url=p.data.get("source_url", ""),
        )
        for p in payloads
    ]
    db.add_all(records)
    db.commit()
    return {"count": len(records)}


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

    facility_type/region/district는 limit을 적용하기 전에 SQL(json_extract) 레벨에서
    걸러낸다 — 예전엔 "최근 limit건을 가져온 뒤 Python에서 필터"하는 방식이라, 특정
    facility_type의 크롤이 대량으로 몰리면(예: 유치원 8만건 적재) 그보다 오래된 다른
    타입(학원·초등 등)이 최근 limit건 안에 아예 안 들어와 조회 결과에서 통째로 사라지는
    버그가 있었다.
    """
    limit = min(limit, _EDUCATION_FACILITIES_MAX_LIMIT)
    query = db.query(RawRecord).filter(RawRecord.item_type == "EducationFacilityItem")
    if facility_type:
        query = query.filter(func.json_extract(RawRecord.data, "$.facility_type") == facility_type)
    if region:
        query = query.filter(func.json_extract(RawRecord.data, "$.region") == region)
    if district:
        query = query.filter(func.json_extract(RawRecord.data, "$.district") == district)
    matching_total = query.count()
    records = query.order_by(RawRecord.created_at.desc()).limit(limit).all()

    results = []
    summary: dict[str, int] = {}
    for r in records:
        data = r.data or {}
        results.append({"id": r.id, "data": data, "created_at": r.created_at})
        ft = data.get("facility_type", "unknown")
        summary[ft] = summary.get(ft, 0) + 1

    return {
        "items": results,
        "total": len(results),
        "matching_total": matching_total,
        "summary_by_type": summary,
    }


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

    region_expr = func.json_extract(RawRecord.data, "$.region")
    district_expr = func.json_extract(RawRecord.data, "$.district")
    grouped = (
        db.query(region_expr, district_expr, func.count(RawRecord.id))
        .filter(
            RawRecord.item_type == "EducationFacilityItem",
            func.json_extract(RawRecord.data, "$.facility_type") == "academy",
        )
        .group_by(region_expr, district_expr)
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


@app.get("/site-stats")
def site_stats(db: Session = Depends(get_db)):
    """랜딩페이지("숫자로 먼저 보여드립니다" 섹션)가 쓰는 실제 운영 지표.

    전부 단순 COUNT 쿼리 — 무거운 집계 없음. 예전엔 이 숫자들이 landing.html에
    하드코딩된 시안용 예시치("1,842개 학원 커리큘럼" 등)였다.
    """
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

    return {
        "facility_records": facility_records or 0,
        "curriculum_items": curriculum_items or 0,
        "admission_data_points": admission_data_points or 0,
        "reports_issued": reports_issued or 0,
        "active_members": active_members or 0,
        "posts_today": posts_today or 0,
        "comments_this_week": comments_this_week or 0,
    }


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
    scores = psychology_engine.score_assessment(req.answers)
    return PsychAssessmentResponse(scores=scores, narrative=psychology_engine.to_consulting_context(scores))


@app.post("/predict-dropout-risk", response_model=DropoutRiskResponse)
def predict_dropout_risk(req: DropoutRiskRequest, db: Session = Depends(get_db)):
    result = predictive_model.predict_dropout_risk(db, req.student_features)
    return DropoutRiskResponse(**result)


@app.post("/qcrm-assessment", response_model=QcrmAssessmentResponse)
def qcrm_assessment(req: QcrmAssessmentRequest):
    result = qcrm_engine.run_mini_qcrm(req.profile, req.iterations)
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
