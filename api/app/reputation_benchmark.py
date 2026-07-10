"""학원 간 익명 평판 비교 — 개별 경쟁 학원의 점수는 절대 노출하지 않고 집계값(평균)만 제공한다.

표본이 최소 3곳 미만인 그룹은 평균을 숨긴다 — 비교 대상이 1~2곳뿐이면 사실상 특정 학원의
점수를 역산할 수 있어(원 설계의 "경쟁 학원의 민감한 내부 수치는 공개하지 않는다" 요구사항 위반).
비교 그룹(지역/과목/규모/상위 20%)은 모두 이 학원 자신을 제외한 다른 학원들로 구성한다.
"""
from sqlalchemy.orm import Session

from app.models_reputation import Academy, AcademyMonthlyMetric, ReputationScore

_MIN_GROUP_SIZE = 3


def _size_tier(total_students: int | None) -> str | None:
    if total_students is None:
        return None
    if total_students < 50:
        return "50명 미만"
    if total_students <= 150:
        return "50~150명"
    return "150명 초과"


def _latest_scores(db: Session) -> dict[int, ReputationScore]:
    """academy_id -> 가장 최근 ReputationScore. 파이썬에서 골라내는 게 SQLite/Postgres
    양쪽에서 동일하게 동작해 서브쿼리보다 단순하다(학원 수가 많지 않은 초기 단계 기준)."""
    all_scores = db.query(ReputationScore).order_by(ReputationScore.computed_at.desc()).all()
    latest: dict[int, ReputationScore] = {}
    for s in all_scores:
        if s.academy_id not in latest:
            latest[s.academy_id] = s
    return latest


def _latest_size(db: Session, academy_id: int) -> int | None:
    metric = (
        db.query(AcademyMonthlyMetric)
        .filter(AcademyMonthlyMetric.academy_id == academy_id)
        .order_by(AcademyMonthlyMetric.month.desc())
        .first()
    )
    return metric.total_students if metric else None


def _group_result(scores: list[float]) -> dict:
    if len(scores) < _MIN_GROUP_SIZE:
        return {"available": False, "sample_size": len(scores), "reason": "비교 대상 학원이 부족합니다(최소 3곳 필요)"}
    return {"available": True, "average": round(sum(scores) / len(scores), 1), "sample_size": len(scores)}


def compute_benchmark(db: Session, academy: Academy) -> dict:
    latest_by_academy = _latest_scores(db)
    our_score = latest_by_academy.get(academy.id)
    if our_score is None:
        return {"available": False, "reason": "먼저 이 학원의 평판 점수를 계산해주세요"}

    others = [(aid, s) for aid, s in latest_by_academy.items() if aid != academy.id]
    all_academies = {a.id: a for a in db.query(Academy).all()}
    our_subjects = {s.strip() for s in (academy.subjects or "").split(",") if s.strip()}
    our_size_tier = _size_tier(_latest_size(db, academy.id))

    region_scores, subject_scores, size_scores = [], [], []
    for aid, s in others:
        other = all_academies.get(aid)
        if not other:
            continue
        if academy.region and other.region == academy.region:
            region_scores.append(s.overall_score)
        other_subjects = {x.strip() for x in (other.subjects or "").split(",") if x.strip()}
        if our_subjects and our_subjects & other_subjects:
            subject_scores.append(s.overall_score)
        if our_size_tier and _size_tier(_latest_size(db, aid)) == our_size_tier:
            size_scores.append(s.overall_score)

    all_scores_sorted = sorted((s.overall_score for _, s in others), reverse=True)
    top20_cutoff = max(1, round(len(all_scores_sorted) * 0.2))
    top20_scores = all_scores_sorted[:top20_cutoff] if len(all_scores_sorted) >= _MIN_GROUP_SIZE else []

    return {
        "available": True,
        "our_score": our_score.overall_score,
        "region": {"label": academy.region, **_group_result(region_scores)},
        "subject": {"label": academy.subjects, **_group_result(subject_scores)},
        "size_tier": {"label": our_size_tier, **_group_result(size_scores)},
        "top20pct": _group_result(top20_scores),
    }
