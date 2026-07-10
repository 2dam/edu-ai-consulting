from pydantic import BaseModel


class CommitteeRunRequest(BaseModel):
    case_text: str


class CommitteeAgentOut(BaseModel):
    id: str
    name: str
    category: str
    perspective: str
    priority: str
    tone: str


class CommitteeRunResponse(BaseModel):
    case_type: str
    committee: list[CommitteeAgentOut]
    opinions: dict[str, str]
    draft: str


class CommitteeReviseRequest(BaseModel):
    draft: str
    feedback: str


class CommitteeReviseResponse(BaseModel):
    final_report: str
