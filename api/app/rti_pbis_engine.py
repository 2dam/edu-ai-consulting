"""RTI · PBIS 통합 시스템 — 분석 및 의사결정 엔진 (Analytics & Decision Engine).

아키텍처 3대 기능:
  1. 위험도 식별 (Risk Identification)    — 스크리닝 임계값 기반 자동 식별
  2. 진전도 평가 (Progress Evaluation)    — 진도 모니터링으로 반응 판단 + 다음 단계 제안
  3. FBA 지원 (Functional Behavior Assessment) — A-B-C 패턴 파악 → 가설 도출

순수 함수 + DB 세션 연동 헬퍼로 구성. 실제 운영에서는 이 로직이
Apache Airflow 등으로 정기 스케줄링되어 자동 평가된다.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from statistics import mean

# ── 임계값 (Universal Screening 기준) ──────────────────────────────────────────
# 학업: 백분위 25 미만 → 위험 / 행동: 위험지수 70 초과 → 위험
MATH_RISK_PERCENTILE = 25.0
BEHAVIOR_RISK_THRESHOLD = 70.0
SOCIAL_SKILL_MIN = 40.0  # 사회성 기술 낮으면 보완 필요

# 진전도: 주간 CBM 목표 성장률(점/주). 이보다 낮으면 "반응 부족"
MIN_ACCEPTABLE_WEEKLY_GAIN = 1.0
# 행동: CICO/일일점수 목표선
BEHAVIOR_TARGET = 70.0


# ── 1. 위험도 식별 ─────────────────────────────────────────────────────────────

def identify_risk(screening) -> dict:
    """스크리닝 1건으로 학업/행동 위험 영역을 식별한다."""
    risks = []
    academic_risk = False
    behavior_risk = False

    if screening.math_percentile_rank is not None and screening.math_percentile_rank < MATH_RISK_PERCENTILE:
        academic_risk = True
        risks.append(f"수학 백분위 {screening.math_percentile_rank:.0f} (< {MATH_RISK_PERCENTILE:.0f} 기준 위험)")
    if screening.reading_benchmark_score is not None and screening.reading_benchmark_score < MATH_RISK_PERCENTILE:
        academic_risk = True
        risks.append(f"읽기 벤치마크 {screening.reading_benchmark_score:.0f} (< {MATH_RISK_PERCENTILE:.0f} 기준 위험)")

    if screening.behavioral_risk_index is not None and screening.behavioral_risk_index > BEHAVIOR_RISK_THRESHOLD:
        behavior_risk = True
        risks.append(f"행동 위험지수 {screening.behavioral_risk_index:.0f} (> {BEHAVIOR_RISK_THRESHOLD:.0f} 위험)")
    if screening.social_skills_rating is not None and screening.social_skills_rating < SOCIAL_SKILL_MIN:
        behavior_risk = True
        risks.append(f"사회성 기술 {screening.social_skills_rating:.0f} (< {SOCIAL_SKILL_MIN:.0f} 보완 필요)")

    tier = 3 if (academic_risk and behavior_risk) else (2 if (academic_risk or behavior_risk) else 1)
    return {
        "academic_risk": academic_risk,
        "behavior_risk": behavior_risk,
        "risk_flags": risks,
        "recommended_tier": tier,
        "summary": "위험 신호 없음" if not risks else "; ".join(risks),
    }


# ── 2. 진전도 평가 ─────────────────────────────────────────────────────────────

def evaluate_progress(pm_records: list, kind: str = "academic") -> dict:
    """진도 모니터링 기록 리스트로 성장 추세를 계산하고 다음 단계를 제안한다.

    pm_records: date/score 순으로 정렬된 객체 리스트 (curriculum_based_measurement_score 또는 daily_behavior_rating)
    """
    if len(pm_records) < 2:
        return {"trend": 0.0, "verdict": "데이터 부족", "recommendation": "진도 모니터링 기록을 2회 이상 축적하세요."}

    recs = sorted(pm_records, key=lambda r: r.date)
    scores = [getattr(r, "curriculum_based_measurement_score" if kind == "academic" else "daily_behavior_rating") for r in recs]
    # 주차 간격 추정 (일수 → 주)
    span_days = (recs[-1].date - recs[0].date).days
    weeks = max(span_days / 7.0, 1.0)
    total_gain = scores[-1] - scores[0]
    weekly_gain = total_gain / weeks

    if kind == "academic":
        if weekly_gain >= MIN_ACCEPTABLE_WEEKLY_GAIN:
            verdict, rec = "반응 양호", "현 중재 지속 (Tier 유지)"
        elif weekly_gain >= 0:
            verdict, rec = "미흡한 반응", "중재 강화 (빈도↑ 또는 소집단→개별)"
        else:
            verdict, rec = "반응 없음/후퇴", "중재 변경 또는 상위 Tier 격상 검토"
    else:
        # 행동: 목표선 도달 여부
        if scores[-1] >= BEHAVIOR_TARGET and weekly_gain >= 0:
            verdict, rec = "목표 도달 중", "현 중재 지속, 종료 임박 시 CICO 단계적 축소"
        elif weekly_gain >= 0:
            verdict, rec = "완만한 개선", "CICO 정기 멘토링 지속 + 기능평가(FBA) 병행"
        else:
            verdict, rec = "행동 악화", "FBA 기반 BIP 수립, Tier 3 격상 검토"

    return {
        "first_score": round(scores[0], 1),
        "latest_score": round(scores[-1], 1),
        "total_gain": round(total_gain, 1),
        "weekly_gain": round(weekly_gain, 2),
        "verdict": verdict,
        "recommendation": rec,
    }


# ── 3. FBA 지원 (Antecedent-Behavior-Consequence) ─────────────────────────────

def analyze_fba(incidents: list[dict]) -> dict:
    """행동 사건 로그(각 dict: antecedent/behavior/consequence)에서
    가장 빈번한 A-B-C 패턴을 찾아 기능적 가설을 도출한다."""
    if not incidents:
        return {"pattern": None, "hypothesis": "행동 사건 기록이 없습니다.", "top_antecedent": None, "top_function": None}

    ant = Counter(i.get("antecedent", "미상") for i in incidents)
    beh = Counter(i.get("behavior", "미상") for i in incidents)
    con = Counter(i.get("consequence", "미상") for i in incidents)
    # 기능 추정: 결과가 '주의획득' 또는 '과제회피' 성격이면 해당 기능 가정
    functions = []
    for i in incidents:
        c = i.get("consequence", "")
        if any(k in c for k in ["주의", "반응", "꾸중"]):
            functions.append("주의 획득")
        elif any(k in c for k in ["과제중단", "놀이", "회피", "쉬움"]):
            functions.append("과제 회피")
        else:
            functions.append("미상")
    func = Counter(functions).most_common(1)[0][0] if functions else "미상"

    top_ant = ant.most_common(1)[0][0]
    top_beh = beh.most_common(1)[0][0]
    top_con = con.most_common(1)[0][0]

    hypothesis = (
        f"학생은 '{top_ant}'(선행) 상황에서 '{top_beh}'(행동)을 보이고, "
        f"그 결과 '{top_con}'(결과)를 얻습니다. 기능적 가설: '{func}' 기능의 행동으로 추정됩니다."
    )
    return {
        "pattern": {"antecedent": top_ant, "behavior": top_beh, "consequence": top_con},
        "hypothesis": hypothesis,
        "top_function": func,
        "n_incidents": len(incidents),
    }


# ── DB 세션 연동 헬퍼 ──────────────────────────────────────────────────────────

def build_unified_profile(db, student_id: str) -> dict:
    """학생별 통합 프로필: 학업·행동·중재 이력을 한눈에 본다 (아키텍처 핵심)."""
    from app.rti_pbis_models import (
        Intervention, ProgressMonitoringAcademic, ProgressMonitoringBehavior,
        Student, UniversalScreening,
    )
    stu = db.query(Student).filter(Student.student_id == student_id).first()
    if not stu:
        return {"error": "학생 없음"}

    screenings = db.query(UniversalScreening).filter(
        UniversalScreening.student_id == student_id).order_by(UniversalScreening.screening_date.desc()).all()
    interventions = db.query(Intervention).filter(Intervention.student_id == student_id).all()
    acad = db.query(ProgressMonitoringAcademic).filter(
        ProgressMonitoringAcademic.student_id == student_id).order_by(ProgressMonitoringAcademic.date).all()
    beh = db.query(ProgressMonitoringBehavior).filter(
        ProgressMonitoringBehavior.student_id == student_id).order_by(ProgressMonitoringBehavior.date).all()

    risk = identify_risk(screenings[0]) if screenings else None
    acad_eval = evaluate_progress(acad, "academic") if len(acad) >= 2 else None
    beh_eval = evaluate_progress(beh, "behavior") if len(beh) >= 2 else None

    return {
        "student_id": stu.student_id,
        "school_id": stu.school_id,
        "grade_level": stu.grade_level,
        "classroom": stu.classroom,
        "demographics": stu.demographics,
        "latest_risk": risk,
        "interventions": [
            {"id": iv.id, "type": iv.intervention_id, "tier": iv.tier, "status": iv.status,
             "start": str(iv.start_date) if iv.start_date else None,
             "fidelity_avg": round(mean([f.fidelity_score for f in iv.fidelity]), 1) if iv.fidelity else None}
            for iv in interventions
        ],
        "academic_progress": acad_eval,
        "behavior_progress": beh_eval,
        "n_academic_pm": len(acad),
        "n_behavior_pm": len(beh),
    }
