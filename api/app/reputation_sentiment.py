"""SNS 공개 게시물 언급에 대한 규칙 기반 감성 분석 — 결정론적, 외부 API 불필요.

1단계의 "점수는 규칙 기반, AI는 서술 요약에만" 원칙을 그대로 따른다. Claude/OpenAI
크레딧이 없어도(현재 로컬 개발 환경처럼) 온라인평판 카테고리 점수가 항상 계산되게 하려는
목적 — 키워드 사전은 학원 리뷰에서 실제로 자주 쓰이는 표현 위주로 구성했다.
"""
from sqlalchemy.orm import Session

from app.models import RawRecord
from app.models_reputation import Academy, AcademyMention, SentimentLabel

_POSITIVE_KEYWORDS = [
    "친절", "꼼꼼", "열정", "실력", "추천", "만족", "향상", "합격", "성실", "책임감",
    "세심", "체계적", "믿고", "좋아요", "최고", "감사", "정성", "성장", "재밌", "재미있",
]
_NEGATIVE_KEYWORDS = [
    "불친절", "불만", "환불", "퇴원", "실망", "불안", "무책임", "방치", "짜증", "최악",
    "후회", "불편", "부족", "성의없", "무성의", "지연", "연락두절", "돈만", "비싸기만",
]


def score_text(text: str) -> tuple[float, SentimentLabel]:
    """텍스트의 긍정/부정 키워드 출현 빈도로 -1~1 점수와 라벨을 계산한다."""
    pos = sum(text.count(kw) for kw in _POSITIVE_KEYWORDS)
    neg = sum(text.count(kw) for kw in _NEGATIVE_KEYWORDS)
    total = pos + neg
    if total == 0:
        return 0.0, SentimentLabel.NEUTRAL

    score = (pos - neg) / total
    if score > 0.2:
        label = SentimentLabel.POSITIVE
    elif score < -0.2:
        label = SentimentLabel.NEGATIVE
    else:
        label = SentimentLabel.NEUTRAL
    return round(score, 2), label


def sync_mentions(db: Session, academy: Academy) -> int:
    """RawRecord(item_type=SnsPostItem) 중 이 학원명과 일치하고 아직 동기화되지 않은
    건만 골라 감성 점수를 매겨 AcademyMention으로 복사한다. 몇 건이 새로 반영됐는지 반환."""
    existing_urls = {
        u for (u,) in db.query(AcademyMention.source_url).filter(AcademyMention.academy_id == academy.id).all()
    }

    records = db.query(RawRecord).filter(RawRecord.item_type == "SnsPostItem").all()
    inserted = 0
    for r in records:
        data = r.data or {}
        if data.get("academy_name") != academy.name:
            continue
        source_url = data.get("source_url", "")
        if not source_url or source_url in existing_urls:
            continue

        text = f"{data.get('post_title', '')} {data.get('post_body', '')}"
        sentiment_score, sentiment_label = score_text(text)

        db.add(
            AcademyMention(
                academy_id=academy.id,
                platform=data.get("platform", "unknown"),
                source_url=source_url,
                post_title=data.get("post_title"),
                post_body=data.get("post_body"),
                published_at=data.get("published_at"),
                hashtags=data.get("hashtags"),
                sentiment_label=sentiment_label,
                sentiment_score=sentiment_score,
                crawled_at=data.get("crawled_at"),
            )
        )
        existing_urls.add(source_url)
        inserted += 1

    db.commit()
    return inserted
