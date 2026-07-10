"""학원 평판 점수 — 규칙 기반 계산 (AI 아님).

AI(Claude)는 이 점수를 설명하는 서술형 요약(reputation_ai.py)에만 쓰이고, 점수 자체는
여기서 결정론적으로 계산한다 — "AI에게 최종 점수를 전부 맡기지 않는다"는 원칙.

1단계(MVP)에서 실제로 수집한 데이터는 학부모·학생 설문과 학원 운영 월간 지표라 카테고리
2개(학부모설문/학생행동)만 계산했다. 2단계에서 SNS 공개 게시물 언급(AcademyMention, 규칙 기반
감성분석 — reputation_sentiment.py)이 추가되어 "온라인평판" 카테고리를 더한다. 교육성과(성적
데이터)·전문가평가(AI 위원회)는 아직 수집 파이프라인이 없어 여전히 미포함 — 생기면 같은
category_scores dict에 키만 추가하면 되도록 설계했다. 데이터가 없는 카테고리는 가중치 0으로
두고 나머지 카테고리 가중치를 비례 재정규화한다.
"""
from sqlalchemy.orm import Session

from app.models_reputation import (
    AcademyMention,
    AcademyMonthlyMetric,
    ReputationScore,
    SurveyCampaign,
    SurveyResponse,
)

# 카테고리별 기본 가중치. 데이터가 없는 카테고리는 0으로 취급되고 나머지가 재정규화된다.
_CATEGORY_WEIGHTS = {
    "학부모설문": 0.45,
    "학생행동": 0.35,
    "온라인평판": 0.20,
}

_RECENT_MONTHS = 3  # 학생행동 계산에 쓰는 최근 개월 수
_MIN_MENTIONS = 5  # 이보다 적은 언급 수로는 온라인평판 카테고리를 계산하지 않음(표본 과소 방지)
_SATISFACTION_FIELDS = (
    "class_satisfaction",
    "teacher_satisfaction",
    "homework_mgmt",
    "counseling_satisfaction",
    "improvement_felt",
    "price_satisfaction",
)


def _score_survey_category(responses: list[SurveyResponse]) -> float | None:
    if not responses:
        return None

    satisfaction_vals = []
    nps_vals = []
    renewal_intents = []
    for r in responses:
        answers = r.answers or {}
        for field in _SATISFACTION_FIELDS:
            if field in answers and answers[field] is not None:
                satisfaction_vals.append(answers[field])
        if "nps" in answers and answers["nps"] is not None:
            nps_vals.append(answers["nps"])
        if "renewal_intent" in answers and answers["renewal_intent"] is not None:
            renewal_intents.append(bool(answers["renewal_intent"]))

    # 만족도(1~5) → 0~100
    satisfaction_pct = (
        (sum(satisfaction_vals) / len(satisfaction_vals) - 1) / 4 * 100 if satisfaction_vals else None
    )

    # NPS(0~10): 9~10 promoter, 0~6 detractor, 7~8 passive. (promoter% - detractor%) → -100~100 → 0~100
    nps_pct = None
    if nps_vals:
        promoters = sum(1 for v in nps_vals if v >= 9)
        detractors = sum(1 for v in nps_vals if v <= 6)
        nps_raw = (promoters - detractors) / len(nps_vals) * 100
        nps_pct = (nps_raw + 100) / 2

    renewal_pct = (
        sum(1 for v in renewal_intents if v) / len(renewal_intents) * 100 if renewal_intents else None
    )

    parts = [(satisfaction_pct, 0.5), (nps_pct, 0.3), (renewal_pct, 0.2)]
    available = [(v, w) for v, w in parts if v is not None]
    if not available:
        return None
    total_weight = sum(w for _, w in available)
    return sum(v * w for v, w in available) / total_weight


def _score_behavior_category(metrics: list[AcademyMonthlyMetric]) -> float | None:
    if not metrics:
        return None

    recent = sorted(metrics, key=lambda m: m.month, reverse=True)[:_RECENT_MONTHS]

    attendance_vals = [m.attendance_rate for m in recent if m.attendance_rate is not None]
    homework_vals = [m.homework_rate for m in recent if m.homework_rate is not None]
    renewal_rates = [
        m.renewal_actual / m.renewal_eligible * 100
        for m in recent
        if m.renewal_eligible and m.renewal_actual is not None and m.renewal_eligible > 0
    ]

    attendance_pct = sum(attendance_vals) / len(attendance_vals) if attendance_vals else None
    homework_pct = sum(homework_vals) / len(homework_vals) if homework_vals else None
    renewal_pct = sum(renewal_rates) / len(renewal_rates) if renewal_rates else None

    parts = [(attendance_pct, 0.3), (homework_pct, 0.3), (renewal_pct, 0.4)]
    available = [(v, w) for v, w in parts if v is not None]
    if not available:
        return None
    total_weight = sum(w for _, w in available)
    return sum(v * w for v, w in available) / total_weight


def _score_online_reputation_category(mentions: list[AcademyMention]) -> float | None:
    if len(mentions) < _MIN_MENTIONS:
        return None
    # sentiment_score는 -1(부정)~1(긍정) — 0~100으로 환산.
    avg = sum(m.sentiment_score for m in mentions) / len(mentions)
    return (avg + 1) / 2 * 100


def _confidence_score(sample_size: int, metric_months: int, mention_count: int) -> float:
    # 설문 30건 + 지표 3개월 + 언급 20건이 모두 쌓이면 각각 만점. 셋 다 없으면 0.
    survey_conf = min(1.0, sample_size / 30) * 45
    metrics_conf = min(1.0, metric_months / _RECENT_MONTHS) * 35
    mentions_conf = min(1.0, mention_count / 20) * 20
    return round(survey_conf + metrics_conf + mentions_conf, 1)


def compute_score(db: Session, academy_id: int) -> ReputationScore:
    responses = (
        db.query(SurveyResponse)
        .join(SurveyCampaign, SurveyResponse.campaign_id == SurveyCampaign.id)
        .filter(SurveyCampaign.academy_id == academy_id)
        .all()
    )
    metrics = db.query(AcademyMonthlyMetric).filter(AcademyMonthlyMetric.academy_id == academy_id).all()
    mentions = db.query(AcademyMention).filter(AcademyMention.academy_id == academy_id).all()

    raw_scores = {
        "학부모설문": _score_survey_category(responses),
        "학생행동": _score_behavior_category(metrics),
        "온라인평판": _score_online_reputation_category(mentions),
    }

    available = {k: v for k, v in raw_scores.items() if v is not None}
    if available:
        total_weight = sum(_CATEGORY_WEIGHTS[k] for k in available)
        overall = sum(available[k] * _CATEGORY_WEIGHTS[k] for k in available) / total_weight
    else:
        overall = 0.0

    category_scores = {k: round(v, 1) for k, v in raw_scores.items() if v is not None}

    metric_months = len({m.month for m in metrics})
    confidence = _confidence_score(len(responses), metric_months, len(mentions))

    record = ReputationScore(
        academy_id=academy_id,
        overall_score=round(overall, 1),
        category_scores=category_scores,
        confidence_score=confidence,
        sample_size=len(responses),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
