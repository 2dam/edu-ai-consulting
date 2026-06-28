"""
사업계획서 3.3항 "AI 컨설팅 엔진 구조"의 2~4단계(분석/가공/제공)를 구현.
1단계(수집)는 crawler/ 가 담당하고, /ingest 를 통해 RawRecord 로 적재됨.

MVP 단계 전략(계획서 본문 그대로): OpenAI API 의존도를 높여 빠르게 출시하고,
데이터가 쌓이면 자체 ML 레이어로 전환.
"""
import os

from openai import OpenAI
from sqlalchemy.orm import Session

from app.models import RawRecord

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다 (.env 확인)")
        _client = OpenAI(api_key=api_key)
    return _client


TIER_DEPTH = {
    "BASIC": "핵심 요약 위주로 5문장 이내, 일반적인 입시 정보 1~2개만 제시",
    "STANDARD": "심층 트렌드 분석을 포함해 단락 3~4개, 구체적 학습 로드맵 초안 포함",
    "PREMIUM": "전문가 상담 수준의 종합 진단 — 학과별 합격 전략, 맞춤 로드맵, 리스크 요인까지 상세히",
}


def gather_context(db: Session, item_types: list[str] | None, limit: int = 30) -> str:
    """3.1항에서 수집된 RawRecord 중 최신 데이터를 컨텍스트로 사용 (단순 RAG)."""
    query = db.query(RawRecord)
    if item_types:
        query = query.filter(RawRecord.item_type.in_(item_types))
    records = query.order_by(RawRecord.created_at.desc()).limit(limit).all()
    lines = []
    for r in records:
        lines.append(f"[{r.item_type}] {r.data}")
    return "\n".join(lines) if lines else "(수집된 데이터 없음 — 일반 지식 기준으로 답변)"


def generate_report(
    db: Session,
    student_label: str,
    tier: str,
    profile: dict,
    context_item_types: list[str] | None,
    psych_context: str = "",
) -> str:
    context = gather_context(db, context_item_types)
    depth_instruction = TIER_DEPTH.get(tier, TIER_DEPTH["BASIC"])

    system_prompt = (
        "당신은 대한민국 대입 입시 컨설턴트 AI입니다. "
        "강남 지역에서 수집된 입시 데이터를 바탕으로 지방 학생에게도 동등한 수준의 "
        "입시 정보를 제공하는 것이 목표입니다. 확인되지 않은 사실을 단정하지 말고, "
        "데이터가 부족하면 그 사실을 명시하세요. "
        "심리 진단 데이터를 해석할 때는 자기결정성이론(SDT)·자기조절학습·긍정심리학·생태학적 관점에 따라, "
        "학생 개인의 결함이 아니라 학생-환경 간 상호작용으로 설명하고, "
        "컨설턴트가 지시하기보다 협력적 파트너로서 제안하는 어조를 유지하세요."
    )
    user_prompt = (
        f"[학생 프로필 (비식별)]\n{profile}\n\n"
        f"[심리 진단 결과]\n{psych_context or '(없음)'}\n\n"
        f"[참고 데이터]\n{context}\n\n"
        f"[요청]\n{depth_instruction} 형태로 입시 컨설팅 리포트를 작성하세요. "
        f"심리 진단 결과가 있다면 동기/학습전략/정서 측면의 맞춤 제안에 반영하세요."
    )

    client = get_client()
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return completion.choices[0].message.content or ""
