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


class ReportResponse(BaseModel):
    id: int
    student_label: str
    tier: str
    report_text: str
