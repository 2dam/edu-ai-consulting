"""
커뮤니티/뉴스 모듈의 AI 보조 기능. app.ai_engine.get_client()의 싱글턴 OpenAI 클라이언트를
그대로 재사용하고, 각 함수는 gpt-4o-mini에 짧고 목적이 분명한 프롬프트 한 번만 호출한다.

detect_toxic_comment / extract_debate_points 등 JSON을 기대하는 함수는 파싱 실패 시
예외를 던지지 않고 안전한 기본값으로 폴백한다 — 특히 detect_toxic_comment는 댓글 작성
라우트에서 non-blocking으로 호출되므로 AI 응답이 이상해도 댓글 작성 자체를 막으면 안 된다.
"""
import json

from app.ai_engine import get_client

_MODEL = "gpt-4o-mini"


def _chat(system: str, user: str) -> str:
    client = get_client()
    completion = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return completion.choices[0].message.content or ""


def summarize_news_article(title: str, body_text: str) -> str:
    system = "당신은 교육 뉴스 요약가입니다. 사실만 담백하게 3문장 이내로 요약하세요. 추측이나 의견을 덧붙이지 마세요."
    user = f"[제목]\n{title}\n\n[본문]\n{(body_text or '')[:4000]}"
    return _chat(system, user)


def summarize_comment_thread(comments: list[str]) -> str:
    system = "다음은 게시글에 달린 댓글 목록입니다. 핵심 의견을 3~5개 불릿으로 요약하세요. 특정 개인을 지목하거나 비방하지 마세요."
    user = "\n".join(f"- {c}" for c in comments) or "(댓글 없음)"
    return _chat(system, user)


def extract_debate_points(comments: list[str]) -> dict:
    system = (
        "다음 댓글에서 찬성 의견과 반대 의견을 구분하세요. "
        '반드시 JSON 형식 {"agree": ["..."], "disagree": ["..."]} 으로만 답하세요. '
        "다른 설명 텍스트는 포함하지 마세요."
    )
    user = "\n".join(f"- {c}" for c in comments) or "(댓글 없음)"
    raw = _chat(system, user)
    try:
        data = json.loads(raw)
        return {
            "agree": list(data.get("agree", [])),
            "disagree": list(data.get("disagree", [])),
        }
    except (json.JSONDecodeError, AttributeError):
        return {"agree": [], "disagree": []}


def detect_toxic_comment(body: str) -> dict:
    """advisory 전용 — 절대 댓글 작성을 막는 데 쓰지 않는다. 호출부는 반드시 non-blocking으로 감싸야 한다."""
    system = (
        "아래 댓글이 욕설, 비방, 혐오 표현을 포함하는지 판단하세요. "
        '반드시 JSON 형식 {"is_toxic": true 또는 false, "reason": "짧은 이유"} 로만 답하세요.'
    )
    try:
        raw = _chat(system, body)
        data = json.loads(raw)
        return {"is_toxic": bool(data.get("is_toxic", False)), "reason": str(data.get("reason", ""))}
    except Exception:
        return {"is_toxic": False, "reason": "AI 판정 실패 - 안전 기본값 적용"}


def suggest_related_posts(title: str, candidate_titles: list[str]) -> list[str]:
    if not candidate_titles:
        return []
    system = (
        "아래 후보 제목 목록 중 주어진 글과 가장 관련 있는 제목을 최대 3개 골라, "
        "후보 목록에 있던 문자열 그대로 한 줄에 하나씩만 출력하세요. 설명을 덧붙이지 마세요."
    )
    user = f"[글 제목]\n{title}\n\n[후보 목록]\n" + "\n".join(f"- {t}" for t in candidate_titles)
    raw = _chat(system, user)
    picked = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]
    return [t for t in picked if t in candidate_titles][:3]


def extract_trending_keywords(recent_titles: list[str]) -> list[str]:
    if not recent_titles:
        return []
    system = (
        "최근 게시글 제목 목록에서 가장 자주 등장하거나 화제가 되는 핵심 키워드를 5개 이내로 추출하세요. "
        "한 줄에 하나씩, 키워드만 출력하세요."
    )
    user = "\n".join(f"- {t}" for t in recent_titles)
    raw = _chat(system, user)
    return [line.strip("- ").strip() for line in raw.splitlines() if line.strip()][:5]
