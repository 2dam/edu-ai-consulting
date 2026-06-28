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


class PsychAssessmentRequest(BaseModel):
    answers: dict[str, int]


class PsychAssessmentResponse(BaseModel):
    scores: dict[str, Any]
    narrative: str


class ReportResponse(BaseModel):
    id: int
    student_label: str
    tier: str
    report_text: str
