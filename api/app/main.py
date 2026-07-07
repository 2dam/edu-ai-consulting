import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app import ai_engine, cctv, feedback_loop, imputation, predictive_model, psychology_engine, qcrm_engine, youtube
from app import models_community  # noqa: F401 - Base.metadata에 커뮤니티 테이블을 등록시키기 위한 import
from app.database import Base, engine, get_db
from app.models import ConsultingReport, FeedbackRecord, RawRecord
from app.routers import admin, community, mom_cafe, news
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

# dashboard/(Vite 개발 서버, 기본 5173 포트)에서 오는 요청을 허용한다.
# 커뮤니티/뉴스 모듈이 별도 프론트엔드로 분리되며 새로 필요해진 설정 — 기존 라우트에는 영향 없음.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(community.router)
app.include_router(news.router)
app.include_router(mom_cafe.router)
app.include_router(admin.router)

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

@app.get("/education-facilities")
def list_education_facilities(
    facility_type: str | None = None,
    region: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """crawler/early_education_spider 가 수집한 어린이집·유치원·초등학교 기초자료 조회.

    facility_type: daycare | kindergarten | elementary
    """
    records = (
        db.query(RawRecord)
        .filter(RawRecord.item_type == "EducationFacilityItem")
        .order_by(RawRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    results = []
    summary: dict[str, int] = {}
    for r in records:
        data = r.data or {}
        if facility_type and data.get("facility_type") != facility_type:
            continue
        if region and data.get("region") != region:
            continue
        results.append({"id": r.id, "data": data, "created_at": r.created_at})
        ft = data.get("facility_type", "unknown")
        summary[ft] = summary.get(ft, 0) + 1

    return {"items": results, "total": len(results), "summary_by_type": summary}


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

    combined_psych_context = "\n\n".join(filter(None, [psych_context, risk_context]))

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
