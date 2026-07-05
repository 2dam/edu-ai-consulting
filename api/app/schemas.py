from typing import Any, Literal

from pydantic import BaseModel


class IngestPayload(BaseModel):
    item_type: str
    data: dict[str, Any]


class ReportRequest(BaseModel):
    student_label: str
    tier: Literal["BASIC", "STANDARD", "PREMIUM"] = "BASIC"
    # 학생 본인이 입력하는 비식별 정보 (성적대, 지망 학과, 관심 지역 등)
    profile: dict[str, Any]
    # 참고할 RawRecord item_type 목록 (없으면 전체 최신 데이터 사용)
    context_item_types: list[str] | None = None
    # SDT/SRL/긍정심리/생태학적 진단 설문 응답 (item_id -> 1~5점). app/psychology_engine.py 참고
    psych_answers: dict[str, int] | None = None
    # 출결/성적 등 정량 피처 (app/predictive_model.FEATURE_NAMES). 앙상블 중도탈락 예측에 사용
    student_features: dict[str, float] | None = None


class PsychAssessmentRequest(BaseModel):
    answers: dict[str, int]


class PsychAssessmentResponse(BaseModel):
    scores: dict[str, Any]
    narrative: str


class DropoutRiskRequest(BaseModel):
    # app/predictive_model.FEATURE_NAMES 키: attendance_rate, assignment_avg_score,
    # midterm_score, study_hours_per_week, motivation_score
    student_features: dict[str, float]


class DropoutRiskResponse(BaseModel):
    dropout_risk_probability: float
    predicted_label: str
    explanation_method: str
    feature_contributions: list[dict[str, Any]]
    is_synthetic_training_data: bool
    warning: str | None = None


class ReportResponse(BaseModel):
    id: int
    student_label: str
    tier: str
    prompt_variant: str | None = None
    report_text: str


class FeedbackRequest(BaseModel):
    report_id: int
    student_label: str
    rating: Literal[1, 2, 3, 4, 5]
    comment: str | None = None
    # 나중에 실제 결과가 확인됐을 때 추가 입력 가능
    actual_outcome: Literal["improved", "no_change", "worsened"] | None = None


class FeedbackResponse(BaseModel):
    id: int
    report_id: int
    rating: int
    message: str


class CctvInfo(BaseModel):
    name: str
    lat: float
    lng: float
    stream_url: str
    format: str


class CctvResponse(BaseModel):
    items: list[CctvInfo]
    total: int
    source: str = "국가교통정보센터(ITS) 공공 도로 CCTV"


class LoopStatusResponse(BaseModel):
    active_prompt_variant: str
    total_feedbacks: int
    unprocessed_feedbacks: int
    retrain_threshold: int
    feedbacks_until_retrain: int
    total_loop_cycles: int
    last_cycle: dict[str, Any] | None = None
    model_accuracy_trend: list[dict[str, Any]]
