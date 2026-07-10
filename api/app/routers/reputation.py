"""학원 평판 인텔리전스 API.

관리(학원 등록/소스/설문 생성/CSV 업로드/점수 계산/PDF)는 require_admin으로 게이트한다
(내부 컨설턴트 전용 — 학원 원장 로그인은 이번 범위 밖). 설문 응답 폼(/surveys/{token})만
학부모·학생이 QR로 접근하는 완전 공개 엔드포인트다.
"""
import csv
import io
import logging
import secrets

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app import pdf_report, reputation_ai, reputation_benchmark, reputation_forecast, reputation_scoring, reputation_sentiment
from app.auth import require_admin
from app.database import get_db
from app.models_community import User
from app.models_reputation import (
    Academy,
    AcademyMention,
    AcademyMonthlyMetric,
    AcademySource,
    ReputationScore,
    SourceType,
    SurveyCampaign,
    SurveyResponse,
)
from app.schemas_reputation import (
    AcademyCreate,
    AcademyMentionOut,
    AcademyMonthlyMetricOut,
    AcademyOut,
    AcademySourceCreate,
    AcademySourceOut,
    BenchmarkOut,
    CrawlTargetsOut,
    ForecastOut,
    MentionSyncResult,
    MetricsUploadResult,
    ReputationDashboardOut,
    ReputationScoreOut,
    SurveyCampaignCreate,
    SurveyCampaignOut,
    SurveyQuestionsOut,
    SurveyResponseOut,
    SurveyResponseSubmit,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reputation", tags=["reputation"])

_METRIC_CSV_FIELDS = (
    "month", "total_students", "new_enrollments", "withdrawals", "renewal_eligible",
    "renewal_actual", "consultation_count", "conversion_count", "attendance_rate", "homework_rate",
)
_METRIC_INT_FIELDS = (
    "total_students", "new_enrollments", "withdrawals", "renewal_eligible",
    "renewal_actual", "consultation_count", "conversion_count",
)
_METRIC_FLOAT_FIELDS = ("attendance_rate", "homework_rate")


def _slugify_region(region: str | None) -> str:
    # ASCII만 남긴다 — 한글 등 non-ASCII 문자가 섞이면 external_id가 PDF
    # Content-Disposition 헤더(latin-1 전용) 등 HTTP 헤더에 쓰일 때 깨진다.
    ascii_only = "".join(ch for ch in (region or "") if ch.isalnum() and ch.isascii())
    return ascii_only.upper() or "MISC"


def _make_external_id(db: Session, region: str | None) -> str:
    prefix = f"ACADEMY-{_slugify_region(region)}"
    existing = (
        db.query(Academy)
        .filter(Academy.external_id.like(f"{prefix}-%"))
        .count()
    )
    return f"{prefix}-{existing + 1:04d}"


def _to_academy_out(a: Academy) -> AcademyOut:
    return AcademyOut(
        id=a.id, external_id=a.external_id, name=a.name, region=a.region,
        subjects=a.subjects, academy_type=a.academy_type, target_grades=a.target_grades,
        edu_office_reg_no=a.edu_office_reg_no, created_at=a.created_at,
    )


def _to_score_out(s: ReputationScore) -> ReputationScoreOut:
    return ReputationScoreOut(
        id=s.id, computed_at=s.computed_at, overall_score=s.overall_score,
        category_scores=s.category_scores or {}, confidence_score=s.confidence_score,
        sample_size=s.sample_size, ai_summary=s.ai_summary,
    )


def _get_academy_or_404(db: Session, academy_id: int) -> Academy:
    academy = db.get(Academy, academy_id)
    if not academy:
        raise HTTPException(status_code=404, detail="학원을 찾을 수 없습니다")
    return academy


# ── 학원 등록/조회 (admin) ────────────────────────────────────────────────────

@router.post("/academies", response_model=AcademyOut)
def create_academy(payload: AcademyCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    academy = Academy(
        external_id=_make_external_id(db, payload.region),
        name=payload.name, region=payload.region, subjects=payload.subjects,
        academy_type=payload.academy_type, target_grades=payload.target_grades,
        edu_office_reg_no=payload.edu_office_reg_no,
    )
    db.add(academy)
    db.commit()
    db.refresh(academy)
    return _to_academy_out(academy)


@router.get("/academies", response_model=list[AcademyOut])
def list_academies(
    q: str | None = Query(default=None, description="이름 부분 검색"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Academy)
    if q:
        query = query.filter(Academy.name.contains(q))
    academies = query.order_by(Academy.created_at.desc()).all()
    return [_to_academy_out(a) for a in academies]


@router.get("/academies/{academy_id}", response_model=AcademyOut)
def get_academy(academy_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return _to_academy_out(_get_academy_or_404(db, academy_id))


# ── 소스 URL (admin) ──────────────────────────────────────────────────────────

@router.post("/academies/{academy_id}/sources", response_model=AcademySourceOut)
def add_source(
    academy_id: int, payload: AcademySourceCreate,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
):
    _get_academy_or_404(db, academy_id)
    source = AcademySource(academy_id=academy_id, source_type=payload.source_type, url=payload.url)
    db.add(source)
    db.commit()
    db.refresh(source)
    return AcademySourceOut(id=source.id, source_type=source.source_type.value, url=source.url, created_at=source.created_at)


@router.get("/academies/{academy_id}/sources", response_model=list[AcademySourceOut])
def list_sources(academy_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _get_academy_or_404(db, academy_id)
    sources = db.query(AcademySource).filter(AcademySource.academy_id == academy_id).order_by(AcademySource.created_at.desc()).all()
    return [AcademySourceOut(id=s.id, source_type=s.source_type.value, url=s.url, created_at=s.created_at) for s in sources]


# ── 설문 캠페인 (admin 생성 / 공개 조회·응답) ──────────────────────────────────

@router.post("/academies/{academy_id}/surveys", response_model=SurveyCampaignOut)
def create_survey_campaign(
    academy_id: int, payload: SurveyCampaignCreate,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
):
    _get_academy_or_404(db, academy_id)
    campaign = SurveyCampaign(
        academy_id=academy_id, token=secrets.token_urlsafe(16),
        title=payload.title, closes_at=payload.closes_at,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return SurveyCampaignOut(
        id=campaign.id, academy_id=campaign.academy_id, token=campaign.token,
        title=campaign.title, is_active=campaign.is_active, created_at=campaign.created_at,
        closes_at=campaign.closes_at, survey_url=f"/survey/{campaign.token}",
    )


@router.get("/surveys/{token}", response_model=SurveyQuestionsOut)
def get_survey(token: str, db: Session = Depends(get_db)):
    """공개 엔드포인트 — 설문 폼 렌더링용. 로그인 불필요."""
    campaign = db.query(SurveyCampaign).filter(SurveyCampaign.token == token).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="존재하지 않는 설문입니다")
    academy = db.get(Academy, campaign.academy_id)
    return SurveyQuestionsOut(
        academy_name=academy.name if academy else "(알 수 없음)",
        campaign_title=campaign.title,
        is_active=campaign.is_active,
    )


@router.post("/surveys/{token}/responses", response_model=SurveyResponseOut)
def submit_survey_response(token: str, payload: SurveyResponseSubmit, db: Session = Depends(get_db)):
    """공개 엔드포인트 — 학부모·학생이 QR로 접근해 제출. 로그인 불필요."""
    campaign = db.query(SurveyCampaign).filter(SurveyCampaign.token == token).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="존재하지 않는 설문입니다")
    if not campaign.is_active:
        raise HTTPException(status_code=400, detail="마감된 설문입니다")

    existing = (
        db.query(SurveyResponse)
        .filter(
            SurveyResponse.campaign_id == campaign.id,
            SurveyResponse.client_fingerprint == payload.client_fingerprint,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="이미 이 기기로 응답을 제출하셨습니다")

    response = SurveyResponse(
        campaign_id=campaign.id,
        respondent_type=payload.respondent_type,
        answers=payload.answers.model_dump(),
        client_fingerprint=payload.client_fingerprint,
    )
    db.add(response)
    db.commit()
    db.refresh(response)
    return SurveyResponseOut(id=response.id, submitted_at=response.submitted_at)


# ── 월간 운영 지표 CSV 업로드 (admin) ─────────────────────────────────────────

@router.post("/academies/{academy_id}/metrics/upload", response_model=MetricsUploadResult)
async def upload_metrics_csv(
    academy_id: int, file: UploadFile,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
):
    """CSV 헤더: month,total_students,new_enrollments,withdrawals,renewal_eligible,
    renewal_actual,consultation_count,conversion_count,attendance_rate,homework_rate
    (month 외 컬럼은 없어도 되며, 있는 값만 갱신한다)"""
    _get_academy_or_404(db, academy_id)
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="UTF-8로 인코딩된 CSV 파일이어야 합니다")

    reader = csv.DictReader(io.StringIO(text))
    imported, updated, errors = 0, 0, []

    for i, row in enumerate(reader, start=2):  # 헤더가 1행
        month = (row.get("month") or "").strip()
        if not month:
            errors.append(f"{i}행: month 값이 비어있어 건너뜀")
            continue

        values: dict = {}
        try:
            for field in _METRIC_INT_FIELDS:
                if row.get(field, "").strip():
                    values[field] = int(float(row[field]))
            for field in _METRIC_FLOAT_FIELDS:
                if row.get(field, "").strip():
                    values[field] = float(row[field])
        except ValueError:
            errors.append(f"{i}행: 숫자로 변환할 수 없는 값이 있어 건너뜀")
            continue

        existing = (
            db.query(AcademyMonthlyMetric)
            .filter(AcademyMonthlyMetric.academy_id == academy_id, AcademyMonthlyMetric.month == month)
            .first()
        )
        if existing:
            for k, v in values.items():
                setattr(existing, k, v)
            updated += 1
        else:
            db.add(AcademyMonthlyMetric(academy_id=academy_id, month=month, **values))
            imported += 1

    db.commit()
    return MetricsUploadResult(imported=imported, updated=updated, errors=errors)


@router.get("/academies/{academy_id}/metrics", response_model=list[AcademyMonthlyMetricOut])
def list_metrics(academy_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _get_academy_or_404(db, academy_id)
    metrics = (
        db.query(AcademyMonthlyMetric)
        .filter(AcademyMonthlyMetric.academy_id == academy_id)
        .order_by(AcademyMonthlyMetric.month.desc())
        .all()
    )
    return [
        AcademyMonthlyMetricOut(
            month=m.month, total_students=m.total_students, new_enrollments=m.new_enrollments,
            withdrawals=m.withdrawals, renewal_eligible=m.renewal_eligible, renewal_actual=m.renewal_actual,
            consultation_count=m.consultation_count, conversion_count=m.conversion_count,
            attendance_rate=m.attendance_rate, homework_rate=m.homework_rate,
        )
        for m in metrics
    ]


# ── 평판 점수 계산/조회 (admin) ────────────────────────────────────────────────

@router.post("/academies/{academy_id}/score/compute", response_model=ReputationScoreOut)
async def compute_score(academy_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    academy = _get_academy_or_404(db, academy_id)
    score = reputation_scoring.compute_score(db, academy_id)

    top_comments = [
        (r.answers or {}).get("free_text")
        for r in (
            db.query(SurveyResponse)
            .join(SurveyCampaign, SurveyResponse.campaign_id == SurveyCampaign.id)
            .filter(SurveyCampaign.academy_id == academy_id)
            .order_by(SurveyResponse.submitted_at.desc())
            .limit(10)
            .all()
        )
    ]
    top_comments = [c for c in top_comments if c][:5]

    try:
        score.ai_summary = await reputation_ai.generate_insight(
            academy_name=academy.name, overall_score=score.overall_score,
            category_scores=score.category_scores or {}, confidence_score=score.confidence_score,
            sample_size=score.sample_size, top_comments=top_comments,
        )
        db.commit()
        db.refresh(score)
    except RuntimeError as exc:
        logger.warning("[평판] AI 요약 생략(설정 누락): %s", exc)
    except anthropic.APIError as exc:
        logger.error("[평판] AI 요약 생성 실패: %s", exc)

    return _to_score_out(score)


@router.get("/academies/{academy_id}/score", response_model=ReputationScoreOut)
def get_latest_score(academy_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _get_academy_or_404(db, academy_id)
    score = (
        db.query(ReputationScore)
        .filter(ReputationScore.academy_id == academy_id)
        .order_by(ReputationScore.computed_at.desc())
        .first()
    )
    if not score:
        raise HTTPException(status_code=404, detail="아직 계산된 평판 점수가 없습니다")
    return _to_score_out(score)


@router.get("/academies/{academy_id}/score/history", response_model=list[ReputationScoreOut])
def get_score_history(academy_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _get_academy_or_404(db, academy_id)
    scores = (
        db.query(ReputationScore)
        .filter(ReputationScore.academy_id == academy_id)
        .order_by(ReputationScore.computed_at.desc())
        .limit(12)
        .all()
    )
    return [_to_score_out(s) for s in scores]


@router.get("/academies/{academy_id}/dashboard", response_model=ReputationDashboardOut)
def get_dashboard(academy_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    academy = _get_academy_or_404(db, academy_id)
    history = (
        db.query(ReputationScore)
        .filter(ReputationScore.academy_id == academy_id)
        .order_by(ReputationScore.computed_at.desc())
        .limit(6)
        .all()
    )
    comments = [
        (r.answers or {}).get("free_text")
        for r in (
            db.query(SurveyResponse)
            .join(SurveyCampaign, SurveyResponse.campaign_id == SurveyCampaign.id)
            .filter(SurveyCampaign.academy_id == academy_id)
            .order_by(SurveyResponse.submitted_at.desc())
            .limit(10)
            .all()
        )
    ]
    comments = [c for c in comments if c][:5]

    return ReputationDashboardOut(
        academy=_to_academy_out(academy),
        latest_score=_to_score_out(history[0]) if history else None,
        score_history=[_to_score_out(s) for s in history],
        top_comments=comments,
    )


# ── PDF 리포트 (admin) ────────────────────────────────────────────────────────

@router.get("/academies/{academy_id}/report.pdf")
def download_report_pdf(academy_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    academy = _get_academy_or_404(db, academy_id)
    score = (
        db.query(ReputationScore)
        .filter(ReputationScore.academy_id == academy_id)
        .order_by(ReputationScore.computed_at.desc())
        .first()
    )
    if not score:
        raise HTTPException(status_code=404, detail="먼저 평판 점수를 계산해주세요")

    pdf_bytes = pdf_report.build_reputation_pdf(academy, score)
    # Content-Disposition은 latin-1 헤더라, external_id에 혹시 non-ASCII가 섞여도 깨지지 않게 방어.
    safe_id = academy.external_id.encode("ascii", "ignore").decode() or f"academy-{academy.id}"
    filename = f"{safe_id}-reputation.pdf"
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── SNS 언급 (admin) ──────────────────────────────────────────────────────────
# 실제 크롤링은 crawler/academy_reputation_crawl.py(로컬 CLI, Scrapy)가 수행한다 — scrapy는
# 배포된 API 서비스에는 설치돼 있지 않다. 여기서는 (1) 로컬 크롤 스크립트에게 크롤 대상을
# 알려주고 (2) 크롤 스크립트가 /ingest-batch로 이미 적재한 RawRecord를 동기화·감성점수화한다.

@router.get("/academies/{academy_id}/crawl-targets", response_model=CrawlTargetsOut)
def get_crawl_targets(academy_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    academy = _get_academy_or_404(db, academy_id)
    sources = db.query(AcademySource).filter(AcademySource.academy_id == academy_id).all()
    # map_review(카카오맵/구글 리뷰 등)는 자동 수집 대상에서 제외 — 민간 리뷰 스크래핑 금지 방침.
    sns_urls = [s.url for s in sources if s.source_type != SourceType.MAP_REVIEW]
    return CrawlTargetsOut(academy_name=academy.name, region=academy.region, sns_urls=sns_urls)


@router.post("/academies/{academy_id}/mentions/sync", response_model=MentionSyncResult)
def sync_mentions(academy_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    academy = _get_academy_or_404(db, academy_id)
    synced = reputation_sentiment.sync_mentions(db, academy)
    return MentionSyncResult(synced=synced)


@router.get("/academies/{academy_id}/mentions", response_model=list[AcademyMentionOut])
def list_mentions(academy_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _get_academy_or_404(db, academy_id)
    mentions = (
        db.query(AcademyMention)
        .filter(AcademyMention.academy_id == academy_id)
        .order_by(AcademyMention.synced_at.desc())
        .limit(50)
        .all()
    )
    return [
        AcademyMentionOut(
            id=m.id, platform=m.platform, source_url=m.source_url, post_title=m.post_title,
            post_body=m.post_body, published_at=m.published_at, hashtags=m.hashtags,
            sentiment_label=m.sentiment_label.value, sentiment_score=m.sentiment_score,
            synced_at=m.synced_at,
        )
        for m in mentions
    ]


# ── 경쟁 학원 비교 (admin) ─────────────────────────────────────────────────────

@router.get("/academies/{academy_id}/benchmark", response_model=BenchmarkOut)
def get_benchmark(academy_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    academy = _get_academy_or_404(db, academy_id)
    return BenchmarkOut(**reputation_benchmark.compute_benchmark(db, academy))


# ── 평판 예측 (admin) ──────────────────────────────────────────────────────────

@router.get("/academies/{academy_id}/forecast", response_model=ForecastOut)
def get_forecast(academy_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    academy = _get_academy_or_404(db, academy_id)
    return ForecastOut(**reputation_forecast.forecast_score(db, academy))
