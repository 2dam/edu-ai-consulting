"""Mini QCRM engine for education consulting.

Learning factors are represented as proposition-like probabilities, rules boost
dependent states, and contradiction penalties dampen unstable patterns.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from app import beqbn_engine


FACTOR_LABELS = {
    "concept_mastery": "Concept mastery",
    "problem_interpretation": "Problem interpretation",
    "strategy_selection": "Strategy selection",
    "calculation_accuracy": "Calculation accuracy",
    "attention_control": "Attention control",
    "time_management": "Time management",
}


@dataclass(frozen=True)
class Rule:
    antecedents: tuple[str, ...]
    consequent: str
    strength: float
    rationale: str


RULES = [
    Rule(("concept_mastery", "problem_interpretation"), "strategy_selection", 0.30, "개념 이해와 조건 해석이 함께 올라가면 풀이 전략 선택 가능성이 커집니다."),
    Rule(("strategy_selection", "calculation_accuracy"), "time_management", 0.18, "전략이 안정되고 계산 실수가 적으면 시간 운용 부담이 줄어듭니다."),
    Rule(("attention_control", "time_management"), "calculation_accuracy", 0.16, "주의 조절과 시간 관리가 안정되면 계산 정확도도 함께 받쳐줍니다."),
    Rule(("concept_mastery",), "problem_interpretation", 0.12, "개념 이해는 문제 조건을 읽는 기준점이 됩니다."),
]

CONFLICTS = [
    ("concept_mastery", "strategy_selection", 0.16, "전략 선택이 개념 이해보다 과도하게 높으면 암기식 풀이 가능성을 점검합니다."),
    ("problem_interpretation", "calculation_accuracy", 0.12, "조건 해석은 낮은데 계산만 높으면 문제 독해 훈련을 우선 확인합니다."),
    ("attention_control", "time_management", 0.10, "주의 조절과 시간 관리 차이가 크면 시험 상황 변동성이 커질 수 있습니다."),
]

DEFAULT_PROFILE = {
    "concept_mastery": 0.62,
    "problem_interpretation": 0.56,
    "strategy_selection": 0.48,
    "calculation_accuracy": 0.68,
    "attention_control": 0.52,
    "time_management": 0.46,
}


def _clamp(value: float, low: float = 0.03, high: float = 0.97) -> float:
    return max(low, min(high, value))


def _normalize_score(value: Any, default: float) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number > 1:
        number = number / 100 if number > 5 else number / 5
    return _clamp(number)


def _phase_mix(probability: float, phase: float) -> float:
    amplitude = math.sqrt(_clamp(probability))
    complement = math.sqrt(_clamp(1 - probability))
    interference = math.cos(phase) * amplitude - math.sin(phase) * complement
    return _clamp(interference * interference)


def run_mini_qcrm(profile: dict[str, Any] | None = None, iterations: int = 3) -> dict[str, Any]:
    raw_profile = profile or {}
    states = {key: _normalize_score(raw_profile.get(key), default) for key, default in DEFAULT_PROFILE.items()}
    trace: list[dict[str, Any]] = []

    for step in range(max(1, min(iterations, 8))):
        next_states = dict(states)
        for rule in RULES:
            activation = 1.0
            for factor in rule.antecedents:
                activation *= states[factor]
            before = next_states[rule.consequent]
            delta = rule.strength * activation * (1 - before)
            next_states[rule.consequent] = _clamp(before + delta)
            if step == 0:
                trace.append({"type": "rule", "target": rule.consequent, "activation": round(activation, 3), "delta": round(delta, 3), "rationale": rule.rationale})

        for left, right, penalty, rationale in CONFLICTS:
            gap = states[right] - states[left]
            if gap > 0.18:
                phase = penalty * gap * math.pi
                next_states[right] = _phase_mix(next_states[right], phase)
                if step == 0:
                    trace.append({"type": "penalty", "target": right, "gap": round(gap, 3), "rationale": rationale})
        states = next_states

    ordered = sorted(states.items(), key=lambda item: item[1])
    readiness = round(0.34 * states["concept_mastery"] + 0.24 * states["problem_interpretation"] + 0.22 * states["strategy_selection"] + 0.20 * states["attention_control"], 3)
    decision_adjustment = run_decision_adjustment(states)
    result = {
        "states": {key: round(value, 3) for key, value in states.items()},
        "labels": FACTOR_LABELS,
        "readiness_score": readiness,
        "readiness_level": _readiness_level(readiness),
        "decision_adjustment": decision_adjustment,
        "weakest_links": [{"factor": key, "label": FACTOR_LABELS[key], "score": round(value, 3)} for key, value in ordered[:2]],
        "strongest_links": [{"factor": key, "label": FACTOR_LABELS[key], "score": round(value, 3)} for key, value in ordered[-2:][::-1]],
        "recommendations": _recommend(states),
        "trace": trace[:6],
        "method_note": "Mini QCRM은 양자 회로의 중첩, 규칙 게이트, 간섭 penalty를 교육 진단용으로 단순화한 모델입니다. 실제 양자 하드웨어 실행이나 표준화 검사가 아닙니다.",
    }
    return result


def to_consulting_context(result: dict[str, Any]) -> str:
    weak = ", ".join(item["label"] for item in result.get("weakest_links", []))
    recs = " ".join(f"- {item}" for item in result.get("recommendations", []))
    adjustment = result.get("decision_adjustment", {})
    adjustment_line = ""
    if adjustment:
        adjustment_line = (
            "\n- 판단 보정: "
            f"{adjustment.get('recommendation_level')} "
            f"(개입안 적합도 {adjustment.get('adjusted_success_probability')}, "
            f"신뢰도 {adjustment.get('confidence')})"
        )
    return f"[Mini QCRM 학습 사고 상태 진단]\n- 종합 준비도: {result.get('readiness_score')} ({result.get('readiness_level')})\n- 우선 점검 연결고리: {weak}{adjustment_line}\n- 권장 개입: {recs}"


def run_decision_adjustment(states: dict[str, float]) -> dict[str, Any]:
    profile = {
        "context_support": round(
            0.35 * states["concept_mastery"]
            + 0.30 * states["problem_interpretation"]
            + 0.20 * states["attention_control"]
            + 0.15 * states["time_management"],
            4,
        ),
        "success_given_supported": round(
            0.35 * states["strategy_selection"]
            + 0.30 * states["calculation_accuracy"]
            + 0.20 * states["concept_mastery"]
            + 0.15 * states["attention_control"],
            4,
        ),
        "success_given_unsupported": round(
            0.40 * states["concept_mastery"]
            + 0.25 * states["problem_interpretation"]
            + 0.20 * states["calculation_accuracy"]
            + 0.15 * states["time_management"],
            4,
        ),
        "uncertainty_bias": 1.0,
        "phase_shift": round((states["strategy_selection"] - states["attention_control"]) * 0.8, 4),
    }
    return beqbn_engine.run_beqbn_consulting(profile)


def _readiness_level(score: float) -> str:
    if score >= 0.72:
        return "stable"
    if score >= 0.52:
        return "developing"
    return "needs_support"


def _recommend(states: dict[str, float]) -> list[str]:
    recommendations: list[str] = []
    if states["problem_interpretation"] < 0.58:
        recommendations.append("문항 조건 표시, 재진술, 함정 조건 찾기 훈련을 먼저 배치하세요.")
    if states["strategy_selection"] < 0.58:
        recommendations.append("유형별 풀이 선택지를 비교하게 하고 선택 이유를 말로 설명하게 하세요.")
    if states["concept_mastery"] < 0.60:
        recommendations.append("개념 정의와 반례를 짝지어 짧은 확인 문제로 재구성하세요.")
    if states["attention_control"] < 0.55:
        recommendations.append("짧은 시간 제한 세트와 풀이 후 자기 점검 루틴을 함께 사용하세요.")
    if not recommendations:
        recommendations.append("응용 문항 비중을 늘리고 풀이 전략 전이를 점검하세요.")
    return recommendations[:3]
