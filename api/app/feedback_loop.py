"""
자가진화 루프 엔진 (Loop Engineering).

피드백 수집 → 재학습 판단 → 모델 재학습 → 프롬프트 A/B 전환의 순환을 구현한다.

루프 흐름:
    POST /feedback 로 피드백 누적
        ↓
    run_loop_tick() — 주기적으로 또는 피드백 임계치 도달 시 호출
        ↓
    should_retrain() — 미처리 피드백이 RETRAIN_THRESHOLD 이상인지 확인
        ↓
    run_retrain_cycle() — 피드백을 훈련 신호로 변환 → predictive_model 재학습
        ↓
    _maybe_switch_prompt_variant() — A/B 변형 중 평점이 높은 쪽을 활성화
        ↓
    LoopMetric 저장 → 피드백 processed=True 마킹
"""
from __future__ import annotations

import ast
import logging
from datetime import datetime, timezone
from statistics import mean

import numpy as np
from sklearn.model_selection import cross_val_score
from sqlalchemy.orm import Session

from app.models import ConsultingReport, FeedbackRecord, LoopMetric

logger = logging.getLogger(__name__)

# 미처리 피드백이 이 수 이상 쌓이면 재학습 트리거
RETRAIN_THRESHOLD = 10

# 현재 활성 프롬프트 변형 — 런타임 상태 (프로세스 재시작 시 LoopMetric에서 복원)
_active_variant: str = "A"


# ── 활성 variant 접근 ─────────────────────────────────────────────────────────

def get_active_variant() -> str:
    return _active_variant


def set_active_variant(variant: str) -> None:
    global _active_variant
    _active_variant = variant


def restore_variant_from_db(db: Session) -> None:
    """서버 재시작 시 마지막 LoopMetric에서 활성 variant를 복원."""
    last = (
        db.query(LoopMetric)
        .filter(LoopMetric.active_prompt_variant.isnot(None))
        .order_by(LoopMetric.created_at.desc())
        .first()
    )
    if last and last.active_prompt_variant:
        set_active_variant(last.active_prompt_variant)
        logger.info("프롬프트 variant 복원: %s (마지막 루프 사이클 기준)", last.active_prompt_variant)


# ── 재학습 판단 ───────────────────────────────────────────────────────────────

def unprocessed_count(db: Session) -> int:
    return db.query(FeedbackRecord).filter(FeedbackRecord.processed == False).count()  # noqa: E712


def should_retrain(db: Session) -> bool:
    return unprocessed_count(db) >= RETRAIN_THRESHOLD


# ── 피드백 → 훈련 신호 변환 ───────────────────────────────────────────────────

def _feedback_to_training_signals(
    feedbacks: list[FeedbackRecord], db: Session
) -> tuple[np.ndarray, np.ndarray] | None:
    """
    FeedbackRecord + ConsultingReport.student_features 를 결합해
    (X, y) 훈련 데이터를 만든다.

    라벨 변환 규칙:
      rating 1~2  → y=1 (위험 신호: 컨설팅 도움 안 됨 = 개선 안 됨)
      rating 4~5  → y=0 (정상 신호: 컨설팅 도움 됨 = 개선됨)
      rating 3    → 제외 (중립, 신호 불명확)
      actual_outcome "worsened" → y=1 강제, "improved" → y=0 강제
    """
    from app.predictive_model import FEATURE_NAMES, _vectorize

    X_rows, y_vals = [], []
    for fb in feedbacks:
        report = db.get(ConsultingReport, fb.report_id)
        if not report or not report.student_features:
            continue

        features = report.student_features
        x = _vectorize(features)

        # actual_outcome 이 있으면 우선
        if fb.actual_outcome == "improved":
            label = 0
        elif fb.actual_outcome == "worsened":
            label = 1
        elif fb.rating <= 2:
            label = 1
        elif fb.rating >= 4:
            label = 0
        else:
            continue  # rating==3 제외

        X_rows.append(x)
        y_vals.append(label)

    if len(X_rows) < 2 or len(set(y_vals)) < 2:
        logger.warning("훈련 신호 부족 (샘플=%d, 클래스 수=%d) — 재학습 스킵", len(X_rows), len(set(y_vals)))
        return None

    return np.array(X_rows), np.array(y_vals)


# ── 재학습 사이클 ─────────────────────────────────────────────────────────────

def run_retrain_cycle(db: Session, trigger: str = "feedback_threshold") -> LoopMetric:
    """
    미처리 피드백으로 predictive_model 을 재학습하고 LoopMetric 을 저장한다.
    반환값: 이번 사이클의 LoopMetric
    """
    from app.predictive_model import TrainingData, build_stacking_model, load_training_data

    feedbacks = db.query(FeedbackRecord).filter(FeedbackRecord.processed == False).all()  # noqa: E712
    logger.info("[루프] 재학습 시작 — 미처리 피드백 %d건, trigger=%s", len(feedbacks), trigger)

    # 기존 학습 데이터 (RawRecord 기반 또는 합성)
    base_data = load_training_data(db)
    acc_before = _cv_accuracy(base_data)

    # 피드백 → 훈련 신호 변환
    signals = _feedback_to_training_signals(feedbacks, db)

    notes = []
    acc_after = None

    if signals is not None:
        X_fb, y_fb = signals
        # 기존 데이터와 피드백 신호를 합쳐 재학습
        X_combined = np.vstack([base_data.X, X_fb])
        y_combined = np.concatenate([base_data.y, y_fb])
        combined_data = TrainingData(X=X_combined, y=y_combined, is_synthetic=base_data.is_synthetic)
        acc_after = _cv_accuracy(combined_data)
        delta = (acc_after - acc_before) if acc_before is not None else None
        notes.append(f"피드백 {len(X_fb)}건 반영. 정확도 변화: {delta:+.4f}" if delta is not None else f"피드백 {len(X_fb)}건 반영.")
        logger.info("[루프] 정확도 %.4f → %.4f", acc_before or 0, acc_after)
    else:
        notes.append("훈련 신호 변환 실패 — 재학습 없이 프롬프트 분석만 수행.")

    # 프롬프트 A/B 전환 여부 판단
    switched, new_variant = _maybe_switch_prompt_variant(feedbacks, db)
    if switched:
        notes.append(f"프롬프트 variant → {new_variant} 로 전환.")

    # 피드백 processed 마킹
    for fb in feedbacks:
        fb.processed = True
    db.commit()

    metric = LoopMetric(
        trigger=trigger,
        feedbacks_used=len(feedbacks),
        accuracy_before=acc_before,
        accuracy_after=acc_after,
        prompt_variant_switched=switched,
        active_prompt_variant=get_active_variant(),
        notes=" | ".join(notes),
    )
    db.add(metric)
    db.commit()
    logger.info("[루프] 사이클 완료 → LoopMetric id=%d", metric.id)
    return metric


def _cv_accuracy(data: TrainingData) -> float | None:
    """5-fold CV 정확도를 반환. 샘플이 너무 적으면 None."""
    from app.predictive_model import build_stacking_model
    if len(data.X) < 10 or len(set(data.y.tolist())) < 2:
        return None
    try:
        model = build_stacking_model()
        scores = cross_val_score(model, data.X, data.y, cv=min(5, len(data.X) // 2), scoring="accuracy")
        return float(scores.mean())
    except Exception as exc:
        logger.warning("CV 정확도 계산 실패: %s", exc)
        return None


# ── 프롬프트 A/B 자동 전환 ────────────────────────────────────────────────────

def _maybe_switch_prompt_variant(feedbacks: list[FeedbackRecord], db: Session) -> tuple[bool, str]:
    """
    각 피드백의 report prompt_variant 를 확인해,
    variant B 의 평균 평점이 A 보다 유의미하게 높으면 B 를 활성화한다.
    반환: (전환 여부, 새 variant)
    """
    ratings_by_variant: dict[str, list[int]] = {"A": [], "B": []}

    for fb in feedbacks:
        report = db.get(ConsultingReport, fb.report_id)
        if not report:
            continue
        v = report.prompt_variant or "A"
        if v in ratings_by_variant:
            ratings_by_variant[v].append(fb.rating)

    avg = {v: mean(r) for v, r in ratings_by_variant.items() if r}
    logger.info("[루프] 프롬프트 variant 평균 평점: %s", avg)

    current = get_active_variant()
    other = "B" if current == "A" else "A"

    if other in avg and current in avg:
        # 비활성 variant 가 0.5점 이상 높으면 전환
        if avg[other] - avg[current] >= 0.5:
            set_active_variant(other)
            logger.info("[루프] 프롬프트 variant %s → %s 전환 (평점 %.2f vs %.2f)",
                        current, other, avg[current], avg[other])
            return True, other

    return False, current


# ── 루프 틱 (스케줄러가 주기적으로 호출) ────────────────────────────────────

def run_loop_tick(db: Session, trigger: str = "scheduled") -> LoopMetric | None:
    """스케줄러 또는 수동 호출 시 재학습 필요 여부를 확인하고 실행."""
    if should_retrain(db):
        return run_retrain_cycle(db, trigger=trigger)
    logger.debug("[루프] 재학습 조건 미충족 (미처리 피드백 %d < %d)", unprocessed_count(db), RETRAIN_THRESHOLD)
    return None


# ── 루프 상태 요약 ────────────────────────────────────────────────────────────

def get_loop_status(db: Session) -> dict:
    total_fb = db.query(FeedbackRecord).count()
    unprocessed = unprocessed_count(db)
    cycles = db.query(LoopMetric).order_by(LoopMetric.created_at.desc()).all()

    last_cycle = None
    if cycles:
        c = cycles[0]
        last_cycle = {
            "id": c.id,
            "trigger": c.trigger,
            "feedbacks_used": c.feedbacks_used,
            "accuracy_before": c.accuracy_before,
            "accuracy_after": c.accuracy_after,
            "prompt_variant_switched": c.prompt_variant_switched,
            "active_prompt_variant": c.active_prompt_variant,
            "notes": c.notes,
            "created_at": c.created_at.isoformat(),
        }

    trend = [
        {
            "cycle_id": c.id,
            "accuracy_before": c.accuracy_before,
            "accuracy_after": c.accuracy_after,
            "created_at": c.created_at.isoformat(),
        }
        for c in reversed(cycles)
        if c.accuracy_before is not None or c.accuracy_after is not None
    ]

    return {
        "active_prompt_variant": get_active_variant(),
        "total_feedbacks": total_fb,
        "unprocessed_feedbacks": unprocessed,
        "retrain_threshold": RETRAIN_THRESHOLD,
        "feedbacks_until_retrain": max(0, RETRAIN_THRESHOLD - unprocessed),
        "total_loop_cycles": len(cycles),
        "last_cycle": last_cycle,
        "model_accuracy_trend": trend,
    }
