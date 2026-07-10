"""평판 추세 기반 예측 — 규칙 기반 선형 추세 외삽 (AI/학습모델 아님).

predictive_model.py의 RandomForest 같은 학습 모델은 쓰지 않는다 — 학원 한 곳당 평판 점수
이력이 많아야 몇 건뿐이라 모델을 학습시키면 사실상 노이즈에 과적합될 뿐이다. 대신 이력이
2건 미만이면 "이력 부족"이라고 정직하게 답하고, 있으면 단순 선형 추세만 외삽한다 —
committee_engine.py의 "확실하지 않은 통계를 지어내지 않는다" 원칙과 같은 정신이다.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models_reputation import Academy, AcademyMonthlyMetric, ReputationScore

_FORECAST_DAYS = 60
_MIN_HISTORY = 2
_MIN_SPAN_DAYS = 3  # 이보다 짧은 기간의 이력으로 60일 외삽하면 노이즈를 추세로 오인하기 쉽다


def _linear_fit(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """최소제곱 직선 (slope, intercept). x가 전부 같으면 기울기 0."""
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return 0.0, mean_y
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom
    intercept = mean_y - slope * mean_x
    return slope, intercept


def _forecast_attrition(metrics: list[AcademyMonthlyMetric]) -> int | None:
    usable = [
        m for m in sorted(metrics, key=lambda m: m.month)
        if m.renewal_eligible is not None and m.renewal_actual is not None
    ]
    if len(usable) < _MIN_HISTORY:
        return None
    xs = list(range(len(usable)))
    ys = [m.renewal_eligible - m.renewal_actual for m in usable]
    slope, intercept = _linear_fit(xs, ys)
    projected = slope * len(usable) + intercept
    return max(0, round(projected))


def forecast_score(db: Session, academy: Academy) -> dict:
    history = (
        db.query(ReputationScore)
        .filter(ReputationScore.academy_id == academy.id)
        .order_by(ReputationScore.computed_at.asc())
        .all()
    )
    if len(history) < _MIN_HISTORY:
        return {
            "available": False,
            "reason": f"평판 점수 이력이 {_MIN_HISTORY}건 이상 쌓이면 예측을 제공합니다 (현재 {len(history)}건)",
        }

    first_ts = history[0].computed_at
    xs = [(h.computed_at - first_ts).total_seconds() / 86400 for h in history]  # 경과일
    ys = [h.overall_score for h in history]

    if xs[-1] < _MIN_SPAN_DAYS:
        return {
            "available": False,
            "reason": f"점수 이력이 쌓인 기간이 너무 짧습니다(최소 {_MIN_SPAN_DAYS}일 필요) — 며칠 뒤 다시 계산해보세요",
        }
    slope, intercept = _linear_fit(xs, ys)

    last_x = xs[-1]
    projected_x = last_x + _FORECAST_DAYS
    projected_score = max(0.0, min(100.0, slope * projected_x + intercept))

    delta = projected_score - history[-1].overall_score
    if delta > 2:
        trend_direction = "상승"
    elif delta < -2:
        trend_direction = "하락"
    else:
        trend_direction = "보합"

    key_driver = None
    if len(history) >= 2:
        prev_cat = history[-2].category_scores or {}
        curr_cat = history[-1].category_scores or {}
        deltas = {
            k: curr_cat[k] - prev_cat[k]
            for k in curr_cat
            if k in prev_cat
        }
        if deltas:
            driver_name = max(deltas, key=lambda k: abs(deltas[k]))
            key_driver = {"category": driver_name, "delta": round(deltas[driver_name], 1)}

    metrics = db.query(AcademyMonthlyMetric).filter(AcademyMonthlyMetric.academy_id == academy.id).all()
    at_risk_estimate = _forecast_attrition(metrics)

    return {
        "available": True,
        "current_score": history[-1].overall_score,
        "projected_score": round(projected_score, 1),
        "projected_date": (datetime.now(timezone.utc) + timedelta(days=_FORECAST_DAYS)).strftime("%Y-%m-%d"),
        "trend_direction": trend_direction,
        "key_driver": key_driver,
        "at_risk_student_estimate": at_risk_estimate,
    }
