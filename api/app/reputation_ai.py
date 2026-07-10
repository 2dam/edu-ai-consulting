"""학원 평판 점수에 대한 AI 서술형 요약 (Claude API).

reputation_scoring.py가 계산한 점수/신뢰도는 입력으로만 주고, 점수 자체를 AI가
다시 매기지 않는다. committee_engine.py의 클라이언트 lazy-init 패턴을 그대로 따른다.
"""
import logging
import os

from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-5"

_client: AsyncAnthropic | None = None


def get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY 환경변수가 설정되어 있지 않습니다 (.env 확인)")
        _client = AsyncAnthropic(api_key=api_key)
    return _client


SYSTEM_PROMPT = """당신은 교육컨설팅 플랫폼의 평판 데이터 분석가입니다. 학원의 평판 점수 데이터를
받아 아래 형식으로 정확히 요약하세요. 다른 말은 덧붙이지 마세요.

**종합 평판**: (점수와 신뢰도를 한 문장으로)

**긍정 요인**:
- ...

**위험 요인**:
- ...

**개선 권고**:
1. ...
2. ...

원칙:
- 주어진 점수·지표·응답 코멘트에 근거해서만 작성하세요. 지어낸 통계나 사례를 만들지 마세요.
- 표본이 적어 신뢰도가 낮으면 그 사실을 반드시 언급하세요.
- 4~8문장 분량으로 간결하게 작성하세요."""


def _extract_text(message) -> str:
    text = "\n".join(block.text for block in message.content if block.type == "text").strip()
    return text or "(응답 없음)"


async def generate_insight(
    academy_name: str,
    overall_score: float,
    category_scores: dict[str, float],
    confidence_score: float,
    sample_size: int,
    top_comments: list[str],
) -> str:
    category_lines = "\n".join(f"- {k}: {v}점" for k, v in category_scores.items())
    comments_block = "\n".join(f'- "{c}"' for c in top_comments) if top_comments else "(자유의견 없음)"

    user_prompt = f"""학원명: {academy_name}
종합 평판 점수: {overall_score}점 (0~100)
데이터 신뢰도: {confidence_score}점 (0~100, 표본수 {sample_size}건 기준)

카테고리별 점수:
{category_lines}

학부모·학생 자유의견 일부:
{comments_block}"""

    client = get_client()
    message = await client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return _extract_text(message)
