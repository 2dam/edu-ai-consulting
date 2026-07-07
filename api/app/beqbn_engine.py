"""BEQBN-based decision support for education consulting.

The model maps a binary consulting decision into a two-node quantum-like
Bayesian network:

- A: current learner context supports option 1 vs option 2
- B: the intervention is likely to succeed vs needs redesign

It is intended as a diagnostic signal for reports, not as a deterministic
placement or admissions decision.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np


DEFAULT_PROFILE = {
    "context_support": 0.55,
    "success_given_supported": 0.78,
    "success_given_unsupported": 0.38,
    "uncertainty_bias": 1.0,
    "phase_shift": 0.0,
}

SCENARIO_LABELS = {
    "context_support": "학습 환경이 1순위 개입안을 지지할 확률",
    "success_given_supported": "환경 지지가 있을 때 개입 성공 확률",
    "success_given_unsupported": "환경 지지가 약할 때 개입 성공 확률",
    "uncertainty_bias": "불확실성 기반 판단 보정 강도",
    "phase_shift": "숨은 선호/저항 요인의 위상 보정",
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _normalize_probability(value: Any, default: float) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number > 1:
        number = number / 100 if number > 5 else number / 5
    return _clamp(number)


def _normalize_float(value: Any, default: float, low: float, high: float) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


class BEQBN:
    """Two-binary-node quantum-like Bayesian network."""

    def __init__(self, p_a1: float, p_b1_given_a1: float, p_b1_given_a2: float):
        self.p_a1 = _clamp(float(p_a1))
        self.p_a2 = 1.0 - self.p_a1
        self.p_b1_given_a1 = _clamp(float(p_b1_given_a1))
        self.p_b2_given_a1 = 1.0 - self.p_b1_given_a1
        self.p_b1_given_a2 = _clamp(float(p_b1_given_a2))
        self.p_b2_given_a2 = 1.0 - self.p_b1_given_a2

        self.b1 = np.array([1.0, 0.0])
        self.superposition_state: np.ndarray | None = None
        self.biased_operator: np.ndarray | None = None
        self.theta: float | None = None
        self.shannon_entropy = self._calculate_shannon_entropy()

    def _calculate_shannon_entropy(self) -> float:
        probs = np.array([self.p_a1, self.p_a2])
        nonzero_probs = probs[probs > 0.0]
        return float(-np.sum(nonzero_probs * np.log2(nonzero_probs)))

    def set_superposition_state(self, amplitudes: list[complex]) -> None:
        state = np.array(amplitudes, dtype=complex)
        norm = np.linalg.norm(state)
        if np.isclose(norm, 0.0):
            raise ValueError("BEQBN state cannot be the zero vector.")
        self.superposition_state = state / norm

    def set_superposition_from_probabilities(self, phase_shift: float = 0.0) -> None:
        p_a1b1 = self.p_a1 * self.p_b1_given_a1
        p_a1b2 = self.p_a1 * self.p_b2_given_a1
        p_a2b1 = self.p_a2 * self.p_b1_given_a2
        p_a2b2 = self.p_a2 * self.p_b2_given_a2

        phase = complex(math.cos(phase_shift), math.sin(phase_shift))
        self.set_superposition_state(
            [
                math.sqrt(p_a1b1),
                math.sqrt(p_a1b2),
                phase * math.sqrt(p_a2b1),
                math.sqrt(p_a2b2),
            ]
        )

    def set_biased_operator_from_entropy(self, uncertainty_bias: float = 1.0) -> None:
        adjusted_entropy = _clamp(self.shannon_entropy * uncertainty_bias)
        self.theta = float(math.acos(-adjusted_entropy))
        self.biased_operator = np.array(
            [
                [math.cos(self.theta / 2.0), -math.sin(self.theta / 2.0)],
                [math.sin(self.theta / 2.0), math.cos(self.theta / 2.0)],
            ],
            dtype=complex,
        )

    def current_state(self, apply_bias: bool = True) -> np.ndarray:
        if self.superposition_state is None:
            raise ValueError("BEQBN superposition state has not been initialized.")
        if apply_bias and self.biased_operator is not None:
            return np.kron(self.biased_operator, np.eye(2)) @ self.superposition_state
        return self.superposition_state

    def probability_b1(self, apply_bias: bool = True) -> float:
        state = self.current_state(apply_bias=apply_bias)
        projection_op = np.kron(np.eye(2), np.outer(self.b1, self.b1))
        probability = np.vdot(state, projection_op @ state).real
        return round(float(_clamp(probability)), 4)

    def entanglement_witness(self, apply_bias: bool = False) -> complex:
        a, b, c, d = self.current_state(apply_bias=apply_bias)
        return a * d - b * c

    def concurrence(self, apply_bias: bool = False) -> float:
        return round(float(_clamp(2.0 * abs(self.entanglement_witness(apply_bias)))), 4)


def run_beqbn_consulting(profile: dict[str, Any] | None = None) -> dict[str, Any]:
    raw_profile = profile or {}
    normalized = {
        "context_support": _normalize_probability(
            raw_profile.get("context_support"), DEFAULT_PROFILE["context_support"]
        ),
        "success_given_supported": _normalize_probability(
            raw_profile.get("success_given_supported"),
            DEFAULT_PROFILE["success_given_supported"],
        ),
        "success_given_unsupported": _normalize_probability(
            raw_profile.get("success_given_unsupported"),
            DEFAULT_PROFILE["success_given_unsupported"],
        ),
        "uncertainty_bias": _normalize_float(
            raw_profile.get("uncertainty_bias"),
            DEFAULT_PROFILE["uncertainty_bias"],
            0.0,
            1.5,
        ),
        "phase_shift": _normalize_float(
            raw_profile.get("phase_shift"), DEFAULT_PROFILE["phase_shift"], -math.pi, math.pi
        ),
    }

    model = BEQBN(
        normalized["context_support"],
        normalized["success_given_supported"],
        normalized["success_given_unsupported"],
    )
    model.set_superposition_from_probabilities(normalized["phase_shift"])
    model.set_biased_operator_from_entropy(normalized["uncertainty_bias"])

    classical_success = (
        normalized["context_support"] * normalized["success_given_supported"]
        + (1.0 - normalized["context_support"]) * normalized["success_given_unsupported"]
    )
    adjusted_success = model.probability_b1(apply_bias=True)
    concurrence = model.concurrence(apply_bias=False)
    witness = model.entanglement_witness()
    confidence = round(float(_clamp(1.0 - model.shannon_entropy * 0.35 - concurrence * 0.25)), 4)

    result = {
        "inputs": {key: round(float(value), 4) for key, value in normalized.items()},
        "labels": SCENARIO_LABELS,
        "classical_success_probability": round(float(classical_success), 4),
        "adjusted_success_probability": adjusted_success,
        "shannon_entropy": round(float(model.shannon_entropy), 4),
        "entanglement_witness": {
            "real": round(float(witness.real), 4),
            "imag": round(float(witness.imag), 4),
        },
        "concurrence": concurrence,
        "confidence": confidence,
        "recommendation_level": _recommendation_level(adjusted_success, confidence),
        "recommendations": _recommend(adjusted_success, confidence, concurrence),
        "method_note": (
            "판단 보정은 학생-환경-개입의 불확실성과 상호의존성을 진단 신호로 변환하는 "
            "양자-유사 모델입니다. 합격/성과를 보장하는 예측 모델이 아닙니다."
        ),
    }
    return result


def to_consulting_context(result: dict[str, Any]) -> str:
    recommendations = " ".join(f"- {item}" for item in result.get("recommendations", []))
    return (
        "[QCRM 판단 보정 진단]\n"
        f"- 고전 베이지안 성공 확률: {result.get('classical_success_probability')}\n"
        f"- 보정 성공 확률: {result.get('adjusted_success_probability')}\n"
        f"- 얽힘 지표 concurrence: {result.get('concurrence')}\n"
        f"- 판단 신뢰도: {result.get('confidence')} ({result.get('recommendation_level')})\n"
        f"- 권장 해석: {recommendations}"
    )


def _recommendation_level(adjusted_success: float, confidence: float) -> str:
    if adjusted_success >= 0.72 and confidence >= 0.55:
        return "proceed"
    if adjusted_success >= 0.52:
        return "pilot"
    return "redesign"


def _recommend(adjusted_success: float, confidence: float, concurrence: float) -> list[str]:
    recommendations: list[str] = []
    if adjusted_success < 0.52:
        recommendations.append("현재 개입안은 바로 실행하기보다 학습 환경 조건을 먼저 재설계하세요.")
    elif adjusted_success < 0.72:
        recommendations.append("소규모 파일럿으로 시작하고 2주 단위 피드백으로 보정하세요.")
    else:
        recommendations.append("현재 개입안을 우선 적용하되 학생 반응 데이터를 함께 기록하세요.")

    if concurrence >= 0.45:
        recommendations.append("학생 요인과 환경 요인이 강하게 얽혀 있어 단일 원인 설명을 피하세요.")
    if confidence < 0.5:
        recommendations.append("불확실성이 높으므로 보호자·교사 관찰 데이터를 추가 확인하세요.")
    return recommendations[:3]
