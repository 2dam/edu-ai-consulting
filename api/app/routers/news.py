import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import ai_community, naver_news, sentiment_finbert
from app.auth import get_current_user
from app.community_common import apply_vote, build_comment_tree, create_comment, serialize_news_post
from app.database import get_db
from app.models_community import AISummary, Board, BoardType, Comment, ModerationStatus, NewsPost, Region, Report, TargetType, User
from app.schemas import IngestPayload
from app.schemas_community import (
    CommentCreate,
    CommentOut,
    CommentSentimentOut,
    DebateSummaryOut,
    IssueSentimentOut,
    IssueSentimentSample,
    NewsFeedPage,
    NewsImportRequest,
    NewsPostDetail,
    NewsPostOut,
    NewsSummaryOut,
    ReportCreate,
    ReportOut,
    SentimentAnalysisOut,
    VoteRequest,
    VoteResult,
)

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/feed", response_model=NewsFeedPage)
def get_feed(
    category: str | None = None,
    region_slug: str | None = None,
    limit: int = Query(20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(NewsPost).filter(NewsPost.moderation_status == ModerationStatus.VISIBLE)
    if category:
        query = query.filter(NewsPost.category == category)
    if region_slug:
        region = db.query(Region).filter(Region.slug == region_slug).first()
        if not region:
            raise HTTPException(status_code=404, detail="존재하지 않는 지역입니다")
        query = query.filter(NewsPost.region_id == region.id)

    total = query.count()
    posts = query.order_by(NewsPost.created_at.desc()).offset(offset).limit(limit).all()
    return NewsFeedPage(items=[serialize_news_post(p) for p in posts], total=total, limit=limit, offset=offset)


@router.get("/issue-sentiment", response_model=IssueSentimentOut)
def issue_sentiment(keyword: str = Query(..., min_length=1, max_length=50)):
    """이슈(키워드)별 여론 평가 — 랜딩페이지 공개 위젯 전용, 로그인 불필요.

    네이버 뉴스 검색 오픈API(app.naver_news, 이미 /education-news 등에서 쓰는 실시간
    외부 연동)로 해당 키워드의 최신 기사를 가져와 제목을 FinBERT로 감정분석한다.
    NAVER_CLIENT_ID/SECRET 미설정 시 naver_news.search_news가 빈 목록을 반환하므로
    이 경우 404로 안내한다(main.py의 /education-news와 동일한 폴백 관례)."""
    articles = naver_news.search_news(keyword, display=15)
    if not articles:
        raise HTTPException(status_code=404, detail="관련 뉴스를 찾지 못했습니다. 다른 키워드로 시도해보세요.")

    results = sentiment_finbert.analyze_batch([a["title"] for a in articles])

    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for r in results:
        counts[r["label"].value] += 1
    overall_label = max(counts, key=counts.get)
    method = "finbert" if any(r["method"] == "finbert" for r in results) else "rule_based"

    return IssueSentimentOut(
        keyword=keyword,
        overall_label=overall_label,
        positive_count=counts["positive"],
        neutral_count=counts["neutral"],
        negative_count=counts["negative"],
        total_analyzed=len(results),
        method=method,
        samples=[
            IssueSentimentSample(
                title=a["title"], url=a["url"], source=a.get("source"),
                label=r["label"].value, score=r["score"],
            )
            for a, r in zip(articles, results)
        ],
    )


@router.get("/{news_id}", response_model=NewsPostDetail)
def get_news_detail(news_id: int, db: Session = Depends(get_db)):
    news = db.get(NewsPost, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="뉴스를 찾을 수 없습니다")

    comments = (
        db.query(Comment)
        .filter(Comment.target_type == TargetType.NEWS_POST, Comment.target_id == news_id)
        .all()
    )
    base = serialize_news_post(news)
    return NewsPostDetail(**base.model_dump(), body_text=news.body_text, comments=build_comment_tree(comments))


@router.post("/ingest")
def ingest_news(payload: IngestPayload, db: Session = Depends(get_db)):
    """크롤러(education_news_spider) 전용 수집 엔드포인트.

    /ingest(RawRecord)와 별도로 둔 이유: 뉴스는 실시간 피드/투표/댓글이 필요한 1급
    엔티티라 JSON blob이 아니라 실제 컬럼을 가진 NewsPost 테이블이 필요하다.
    region/category 문자열이 기존 데이터와 매칭되지 않아도 절대 reject하지 않고
    null로 저장한다 — 크롤러 안정성이 완벽한 분류보다 우선한다.
    """
    data = payload.data

    region = None
    region_key = data.get("region")
    if region_key:
        region = (
            db.query(Region)
            .filter((Region.slug == region_key) | (Region.name == region_key))
            .first()
        )

    board = db.query(Board).filter(Board.board_type == BoardType.NEWS).first()

    tags = data.get("tags") or []
    tags_str = ",".join(str(t) for t in tags) if isinstance(tags, list) else str(tags)

    published_at = None
    raw_published = data.get("published_at")
    if raw_published:
        try:
            published_at = datetime.fromisoformat(str(raw_published))
        except ValueError:
            published_at = None

    news = NewsPost(
        board_id=board.id if board else None,
        region_id=region.id if region else None,
        title=data.get("title", "(제목 없음)"),
        source_url=data.get("url") or data.get("source_url", ""),
        source_name=data.get("source"),
        category=data.get("category"),
        body_text=data.get("body_text"),
        thumbnail_url=data.get("thumbnail_url"),
        tags=tags_str,
        published_at=published_at,
    )
    db.add(news)
    db.commit()
    return {"id": news.id}


@router.post("/import-url", response_model=NewsPostOut)
def import_url(
    payload: NewsImportRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """관리자/운영자가 단일 기사를 수동 등록 — 서버측 임의 URL 스크래핑은 범위 밖이라
    프론트에서 채운 필드를 그대로 받는다."""
    region = None
    if payload.region_slug:
        region = db.query(Region).filter(Region.slug == payload.region_slug).first()

    board = db.query(Board).filter(Board.board_type == BoardType.NEWS).first()

    news = NewsPost(
        board_id=board.id if board else None,
        region_id=region.id if region else None,
        title=payload.title,
        source_url=payload.url,
        source_name=payload.source_name,
        category=payload.category,
        body_text=payload.body_text,
        thumbnail_url=payload.thumbnail_url,
        tags=",".join(payload.tags),
        published_at=payload.published_at,
    )
    db.add(news)
    db.commit()
    db.refresh(news)
    return serialize_news_post(news)


@router.post("/{news_id}/summarize", response_model=NewsSummaryOut)
def summarize_news(news_id: int, db: Session = Depends(get_db)):
    news = db.get(NewsPost, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="뉴스를 찾을 수 없습니다")

    try:
        summary_text = ai_community.summarize_news_article(news.title, news.body_text or "")
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    db.add(
        AISummary(
            summary_type="news_summary", target_type=TargetType.NEWS_POST, target_id=news_id, content=summary_text,
        )
    )
    db.commit()
    return NewsSummaryOut(news_post_id=news_id, summary=summary_text, model_name="gpt-4o-mini")


@router.post("/{news_id}/debate-summary", response_model=DebateSummaryOut)
def debate_summary(news_id: int, db: Session = Depends(get_db)):
    """summarize_comment_thread + extract_debate_points 부가 AI 기능 —
    뉴스 댓글 스레드의 논점을 요약한다. 댓글이 없으면 400으로 명확히 안내한다."""
    news = db.get(NewsPost, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="뉴스를 찾을 수 없습니다")

    comments = (
        db.query(Comment)
        .filter(
            Comment.target_type == TargetType.NEWS_POST,
            Comment.target_id == news_id,
            Comment.moderation_status == ModerationStatus.VISIBLE,
        )
        .all()
    )
    bodies = [c.body for c in comments]
    if not bodies:
        raise HTTPException(status_code=400, detail="아직 댓글이 없어 토론을 요약할 수 없습니다")

    try:
        comment_summary = ai_community.summarize_comment_thread(bodies)
        debate = ai_community.extract_debate_points(bodies)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    db.add(
        AISummary(
            summary_type="debate_summary",
            target_type=TargetType.NEWS_POST,
            target_id=news_id,
            content=json.dumps({"comment_summary": comment_summary, **debate}, ensure_ascii=False),
        )
    )
    db.commit()

    return DebateSummaryOut(
        news_post_id=news_id, comment_summary=comment_summary,
        agree=debate["agree"], disagree=debate["disagree"],
    )


@router.post("/{news_id}/sentiment", response_model=SentimentAnalysisOut)
def analyze_sentiment(news_id: int, db: Session = Depends(get_db)):
    """"여론 평가" — 기사 본문 + 공개 댓글을 FinBERT로 감정분석해 긍정/중립/부정 비율을 낸다.

    FinBERT(transformers/torch)가 설치·로드되지 않은 환경에서는 app.reputation_sentiment의
    규칙 기반 스코어러로 자동 폴백하므로 항상 응답한다 — 응답의 method 필드로 어느 쪽이
    쓰였는지 구분할 수 있다."""
    news = db.get(NewsPost, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="뉴스를 찾을 수 없습니다")

    comments = (
        db.query(Comment)
        .filter(
            Comment.target_type == TargetType.NEWS_POST,
            Comment.target_id == news_id,
            Comment.moderation_status == ModerationStatus.VISIBLE,
        )
        .all()
    )
    bodies = [c.body for c in comments]

    result = sentiment_finbert.summarize_opinions(news.body_text or "", bodies)

    db.add(
        AISummary(
            summary_type="sentiment_analysis",
            target_type=TargetType.NEWS_POST,
            target_id=news_id,
            content=json.dumps(
                {
                    "overall_label": result["overall_label"].value,
                    "positive_count": result["positive_count"],
                    "neutral_count": result["neutral_count"],
                    "negative_count": result["negative_count"],
                    "total_analyzed": result["total_analyzed"],
                    "method": result["method"],
                },
                ensure_ascii=False,
            ),
            model_name=sentiment_finbert.MODEL_NAME if result["method"] == "finbert" else "rule_based",
        )
    )
    db.commit()

    return SentimentAnalysisOut(
        news_post_id=news_id,
        overall_label=result["overall_label"].value,
        positive_count=result["positive_count"],
        neutral_count=result["neutral_count"],
        negative_count=result["negative_count"],
        total_analyzed=result["total_analyzed"],
        method=result["method"],
        comment_sentiments=[
            CommentSentimentOut(label=c["label"].value, score=c["score"]) for c in result["comment_sentiments"]
        ],
    )


@router.post("/{news_id}/comments", response_model=CommentOut)
def add_news_comment(
    news_id: int, payload: CommentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    news = db.get(NewsPost, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="뉴스를 찾을 수 없습니다")

    if payload.parent_id is not None:
        parent = db.get(Comment, payload.parent_id)
        if not parent or parent.target_type != TargetType.NEWS_POST or parent.target_id != news_id:
            raise HTTPException(status_code=400, detail="잘못된 부모 댓글입니다")

    comment = create_comment(db, TargetType.NEWS_POST, news_id, user, payload.body, payload.parent_id)
    return CommentOut(
        id=comment.id, author_nickname=user.nickname, body=comment.body, parent_id=comment.parent_id,
        upvote_count=comment.upvote_count, downvote_count=comment.downvote_count,
        toxicity_flag=comment.toxicity_flag, moderation_status=comment.moderation_status.value,
        created_at=comment.created_at, replies=[],
    )


@router.post("/{news_id}/vote", response_model=VoteResult)
def vote_news(
    news_id: int, payload: VoteRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        return apply_vote(db, user, TargetType.NEWS_POST, news_id, payload.value)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{news_id}/report", response_model=ReportOut)
def report_news(
    news_id: int, payload: ReportCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    news = db.get(NewsPost, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="뉴스를 찾을 수 없습니다")

    report = Report(
        reporter_id=user.id, target_type=TargetType.NEWS_POST, target_id=news_id,
        reason=payload.reason, detail=payload.detail,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return ReportOut(
        id=report.id, target_type=report.target_type.value, target_id=report.target_id,
        reason=report.reason, detail=report.detail, status=report.status.value, created_at=report.created_at,
    )
