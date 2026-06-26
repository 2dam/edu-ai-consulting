from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app import ai_engine
from app.database import Base, engine, get_db
from app.models import ConsultingReport, RawRecord
from app.schemas import IngestPayload, ReportRequest, ReportResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI 빅데이터 교육 컨설팅 API")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/landing")
def landing():
    return FileResponse(STATIC_DIR / "landing.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
def ingest(payload: IngestPayload, db: Session = Depends(get_db)):
    """크롤러(edu_crawler.pipelines.ApiExportPipeline)가 호출하는 수집 엔드포인트."""
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


@app.post("/reports", response_model=ReportResponse)
def create_report(req: ReportRequest, db: Session = Depends(get_db)):
    """사업계획서 3.3항 4단계 파이프라인 중 분석~제공 단계."""
    try:
        report_text = ai_engine.generate_report(
            db, req.student_label, req.tier, req.profile, req.context_item_types
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    record = ConsultingReport(
        student_label=req.student_label,
        tier=req.tier,
        input_summary=str(req.profile),
        report_text=report_text,
    )
    db.add(record)
    db.commit()
    return ReportResponse(
        id=record.id, student_label=record.student_label, tier=record.tier, report_text=record.report_text
    )


@app.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db)):
    record = db.get(ConsultingReport, report_id)
    if not record:
        raise HTTPException(status_code=404, detail="report not found")
    return ReportResponse(
        id=record.id, student_label=record.student_label, tier=record.tier, report_text=record.report_text
    )
