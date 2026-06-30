import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app import ai_engine, feedback_loop, imputation, predictive_model, psychology_engine
from app.database import Base, engine, get_db
from app.models import ConsultingReport, FeedbackRecord, RawRecord
from app.schemas import (
    DropoutRiskRequest,
    DropoutRiskResponse,
    FeedbackRequest,
    FeedbackResponse,
    IngestPayload,
    LoopStatusResponse,
    PsychAssessmentRequest,
    PsychAssessmentResponse,
    ReportRequest,
    ReportResponse,
)

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
    # 재시작 시 마지막 활성 prompt variant 복원
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        feedback_loop.restore_variant_from_db(db)
    finally:
        db.close()
    # 백그라운드 루프 시작
    task = asyncio.create_task(_loop_scheduler())
    yield
    task.cancel()


app = FastAPI(title="AI 빅데이터 교육 컨설팅 API", lifespan=lifespan)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── 정적 페이지 ───────────────────────────────────────────────────────────────

@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


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
