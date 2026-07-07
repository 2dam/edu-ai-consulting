"""
R_Predictive_Models_for_Educational_Consulting.pdf 3장(앙상블)·3.2장(XAI)을 코드화.

원 보고서는 R(caretEnsemble, shapr/lime)을 전제로 하지만, 이 프로젝트는 Python/FastAPI
스택이므로 동일한 개념을 scikit-learn + shap 로 구현한다.

- 앙상블(스태킹): 로지스틱 회귀 + 랜덤포레스트(배깅) + 그래디언트 부스팅(부스팅)을
  기본 모델로 두고, 메타 모델(로지스틱 회귀)로 최종 예측을 결합 (StackingClassifier).
- XAI: shap 패키지로 각 변수의 기여도(Shapley value)를 계산해 "왜" 그렇게 예측했는지
  설명. shap 미설치 시에는 RandomForest의 변수 중요도(permutation importance)로 폴백.

실제 학생 중도탈락 라벨 데이터가 아직 쌓이지 않았으므로(imputation.py와 동일한 상황),
학습 데이터가 없을 때는 합성 데이터로 모델을 만들어 파이프라인이 동작함을 보장한다.
실 데이터(RawRecord item_type="StudentOutcomeRecord")가 쌓이면 그쪽을 우선 사용한다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, StackingClassifier
from sklearn.linear_model import LogisticRegression
from sqlalchemy.orm import Session

from app.models import RawRecord

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "attendance_rate",      # 출석률 (0~1)
    "assignment_avg_score", # 과제 평균 점수 (0~100)
    "midterm_score",        # 중간고사 점수 (0~100)
    "study_hours_per_week", # 주간 자기학습 시간
    "motivation_score",     # psychology_engine SDT 평균 등으로 산출된 동기 점수 (0~5)
]

_FEATURE_LABELS_KO = {
    "attendance_rate": "출석률",
    "assignment_avg_score": "과제 평균 점수",
    "midterm_score": "중간고사 점수",
    "study_hours_per_week": "주간 자기학습 시간",
    "motivation_score": "동기 점수(SDT)",
}


@dataclass
class TrainingData:
    X: np.ndarray
    y: np.ndarray
    is_synthetic: bool = field(default=False)


def _vectorize(record: dict) -> list[float]:
    return [float(record.get(name, 0.0) or 0.0) for name in FEATURE_NAMES]


def load_training_data(db: Session) -> TrainingData:
    """RawRecord(item_type='StudentOutcomeRecord')에서 학습 데이터를 가져온다.
    'dropout_risk'(0/1) 라벨이 있는 레코드만 사용. 충분치 않으면 합성 데이터로 폴백."""
    records = (
        db.query(RawRecord)
        .filter(RawRecord.item_type == "StudentOutcomeRecord")
        .all()
    )

    X, y = [], []
    for r in records:
        d = r.data or {}
        if "dropout_risk" not in d:
            continue
        X.append(_vectorize(d))
        y.append(int(d["dropout_risk"]))

    if len(X) >= 30 and len(set(y)) > 1:
        return TrainingData(X=np.array(X), y=np.array(y), is_synthetic=False)

    return TrainingData(*_synthetic_dataset(), is_synthetic=True)


def _synthetic_dataset(n: int = 300, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """실 라벨 데이터가 부족할 때 파이프라인 검증용으로 쓰는 합성 데이터.
    경향성만 현실적으로 흉내냄 (출석률·성적·동기 낮을수록 중도탈락 위험 높게)."""
    rng = np.random.default_rng(seed)
    attendance = rng.uniform(0.4, 1.0, n)
    assignment = rng.uniform(30, 100, n)
    midterm = rng.uniform(20, 100, n)
    study_hours = rng.uniform(0, 30, n)
    motivation = rng.uniform(1, 5, n)

    risk_score = (
        (1 - attendance) * 2.0
        + (100 - assignment) / 100 * 1.5
        + (100 - midterm) / 100 * 1.5
        + (30 - study_hours) / 30 * 1.0
        + (5 - motivation) / 5 * 1.0
        + rng.normal(0, 0.3, n)
    )
    y = (risk_score > np.median(risk_score)).astype(int)
    X = np.column_stack([attendance, assignment, midterm, study_hours, motivation])
    return X, y


def build_stacking_model() -> StackingClassifier:
    """배깅(RandomForest) + 부스팅(GradientBoosting)을 기본 모델로,
    로지스틱 회귀를 메타 모델로 쓰는 스태킹 앙상블."""
    base_learners = [
        ("logreg", LogisticRegression(max_iter=1000)),
        ("rf", RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)),
        ("gb", GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42)),
    ]
    return StackingClassifier(
        estimators=base_learners,
        final_estimator=LogisticRegression(max_iter=1000),
        cv=5,
    )


def train_dropout_model(db: Session) -> tuple[StackingClassifier, TrainingData]:
    data = load_training_data(db)
    model = build_stacking_model()
    model.fit(data.X, data.y)
    return model, data


def _explain_with_shap(model: StackingClassifier, X_background: np.ndarray, x_row: np.ndarray) -> list[dict] | None:
    try:
        import shap
    except ImportError:
        return None

    # StackingClassifier 전체를 감싸는 KernelExplainer는 느리지만 모델-비종속적이라
    # 메타 모델까지 포함한 최종 예측을 정확히 설명할 수 있다. 배경 샘플은 50개로 제한해 속도 확보.
    background = X_background[np.random.default_rng(0).choice(len(X_background), size=min(50, len(X_background)), replace=False)]
    explainer = shap.KernelExplainer(lambda x: model.predict_proba(x)[:, 1], background)
    shap_values = explainer.shap_values(x_row.reshape(1, -1), nsamples=100)

    contributions = []
    for name, value in zip(FEATURE_NAMES, shap_values[0]):
        contributions.append({"feature": name, "label": _FEATURE_LABELS_KO[name], "shap_value": round(float(value), 4)})
    contributions.sort(key=lambda c: abs(c["shap_value"]), reverse=True)
    return contributions


def _explain_with_permutation_importance(model: StackingClassifier, data: TrainingData, x_row: np.ndarray) -> list[dict]:
    """shap 미설치 시 폴백. feature_importances_ 자체는 크기만 있고 방향(+/-)이 없으므로,
    학습 데이터에서의 (피처-라벨) 상관 방향과 해당 학생의 값이 평균보다 높은지/낮은지를
    곱해 근사 방향을 추정한다. SHAP보다 거칠지만 "왜"에 대한 최소한의 설명을 제공."""
    rf = dict(model.estimators)["rf"]
    if not hasattr(rf, "feature_importances_"):
        rf.fit(data.X, data.y)
    importances = rf.feature_importances_

    means = data.X.mean(axis=0)
    contributions = []
    for i, name in enumerate(FEATURE_NAMES):
        corr = float(np.corrcoef(data.X[:, i], data.y)[0, 1]) if data.X[:, i].std() > 0 else 0.0
        deviation = x_row[i] - means[i]
        approx_direction = corr * deviation
        signed_value = importances[i] if approx_direction >= 0 else -importances[i]
        contributions.append({"feature": name, "label": _FEATURE_LABELS_KO[name], "shap_value": round(float(signed_value), 4)})
    contributions.sort(key=lambda c: abs(c["shap_value"]), reverse=True)
    return contributions


def predict_dropout_risk(db: Session, student_features: dict) -> dict:
    """학생 1명의 피처를 받아 중도탈락 위험을 예측하고 XAI 설명을 함께 반환."""
    model, data = train_dropout_model(db)
    x_row = np.array(_vectorize(student_features))

    proba = float(model.predict_proba(x_row.reshape(1, -1))[0, 1])
    prediction = int(proba >= 0.5)

    explanation_method = "shap"
    contributions = _explain_with_shap(model, data.X, x_row)
    if contributions is None:
        explanation_method = "permutation_importance(rf)"
        contributions = _explain_with_permutation_importance(model, data, x_row)

    return {
        "dropout_risk_probability": round(proba, 4),
        "predicted_label": "위험군" if prediction == 1 else "정상",
        "explanation_method": explanation_method,
        "feature_contributions": contributions,
        "is_synthetic_training_data": data.is_synthetic,
        "warning": (
            "실제 학생 중도탈락 라벨 데이터가 충분하지 않아 합성 데이터로 학습된 모델입니다. "
            "참고용으로만 사용하고, RawRecord(item_type='StudentOutcomeRecord')에 실 데이터가 "
            "30건 이상(라벨 2종 포함) 쌓이면 자동으로 실 데이터 학습으로 전환됩니다."
            if data.is_synthetic
            else None
        ),
    }


def to_consulting_context(result: dict) -> str:
    """predict_dropout_risk() 결과를 ai_engine 프롬프트용 자연어 컨텍스트로 변환."""
    lines = [
        "[앙상블(스태킹) 예측 모델 기반 중도탈락 위험 진단]",
        f"- 예측: {result['predicted_label']} (위험 확률 {result['dropout_risk_probability']*100:.1f}%)",
        f"- 설명 기법: {result['explanation_method']}",
        "- 주요 영향 요인 (영향력 큰 순):",
    ]
    for c in result["feature_contributions"][:5]:
        direction = "위험 증가 요인" if c["shap_value"] > 0 else "위험 완화 요인"
        lines.append(f"  · {c['label']}: {c['shap_value']} ({direction})")
    if result.get("warning"):
        lines.append(f"- 주의: {result['warning']}")
    return "\n".join(lines)
