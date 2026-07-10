import logging

import anthropic
from fastapi import APIRouter, HTTPException

from app import committee_engine
from app.schemas_committee import (
    CommitteeReviseRequest,
    CommitteeReviseResponse,
    CommitteeRunRequest,
    CommitteeRunResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/committee", tags=["committee"])


@router.post("/run", response_model=CommitteeRunResponse)
async def run_committee(payload: CommitteeRunRequest):
    """사안을 접수해 30인 풀에서 위원회를 구성하고, 토의 + 초안 보고서를 한 번에 생성한다."""
    if not payload.case_text.strip():
        raise HTTPException(status_code=400, detail="사안 내용을 입력하세요")
    try:
        result = await committee_engine.run_full_committee(payload.case_text)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except anthropic.APIError as exc:
        logger.error("[위원회] 초안 종합 실패: %s", exc)
        raise HTTPException(status_code=502, detail=f"Claude API 오류: {exc.message}")
    return CommitteeRunResponse(**result)


@router.post("/revise", response_model=CommitteeReviseResponse)
async def revise_committee(payload: CommitteeReviseRequest):
    """초안 보고서에 컨설턴트 피드백을 반영해 최종본을 생성한다."""
    if not payload.feedback.strip():
        raise HTTPException(status_code=400, detail="피드백을 입력하세요")
    try:
        final_report = await committee_engine.revise_report(payload.draft, payload.feedback)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except anthropic.APIError as exc:
        logger.error("[위원회] 최종안 생성 실패: %s", exc)
        raise HTTPException(status_code=502, detail=f"Claude API 오류: {exc.message}")
    return CommitteeReviseResponse(final_report=final_report)
