"""라우터 4개(community/news/mom_cafe/admin)가 공유하는 헬퍼.

투표 적용, 댓글 생성(+비차단 AI 독성 체크), 댓글 트리 구성, 모델→Pydantic 직렬화처럼
여러 라우터에서 똑같이 필요한 로직을 한 곳에 모아 라우트 함수를 얇게 유지한다.
"""
from sqlalchemy.orm import Session

from app import ai_community
from app.models_community import Comment, CommunityPost, NewsPost, TargetType, User, Vote
from app.schemas_community import CommentOut, CommunityPostOut, NewsPostOut, VoteResult

_TARGET_MODELS = {
    TargetType.POST: CommunityPost,
    TargetType.NEWS_POST: NewsPost,
    TargetType.COMMENT: Comment,
}


def get_target_row(db: Session, target_type: TargetType, target_id: int):
    model = _TARGET_MODELS[target_type]
    return db.get(model, target_id)


def apply_vote(db: Session, user: User, target_type: TargetType, target_id: int, value: int) -> VoteResult:
    """같은 값으로 재투표하면 취소(레딧 UX), 반대 값이면 전환. 카운터는 델타로만 갱신한다."""
    target = get_target_row(db, target_type, target_id)
    if target is None:
        raise ValueError("대상을 찾을 수 없습니다")

    existing = (
        db.query(Vote)
        .filter(Vote.user_id == user.id, Vote.target_type == target_type, Vote.target_id == target_id)
        .first()
    )

    if existing is None:
        db.add(Vote(user_id=user.id, target_type=target_type, target_id=target_id, value=value))
        if value == 1:
            target.upvote_count += 1
        else:
            target.downvote_count += 1
        user_vote = value
    elif existing.value == value:
        db.delete(existing)
        if value == 1:
            target.upvote_count = max(0, target.upvote_count - 1)
        else:
            target.downvote_count = max(0, target.downvote_count - 1)
        user_vote = 0
    else:
        if existing.value == 1:
            target.upvote_count = max(0, target.upvote_count - 1)
            target.downvote_count += 1
        else:
            target.downvote_count = max(0, target.downvote_count - 1)
            target.upvote_count += 1
        existing.value = value
        user_vote = value

    db.commit()
    db.refresh(target)
    return VoteResult(upvote_count=target.upvote_count, downvote_count=target.downvote_count, user_vote=user_vote)


def build_comment_tree(comments: list[Comment]) -> list[CommentOut]:
    by_parent: dict[int | None, list[Comment]] = {}
    for c in comments:
        by_parent.setdefault(c.parent_id, []).append(c)

    def build(parent_id: int | None) -> list[CommentOut]:
        nodes = []
        for c in sorted(by_parent.get(parent_id, []), key=lambda x: x.created_at):
            nodes.append(
                CommentOut(
                    id=c.id,
                    author_nickname=c.author.nickname,
                    body=c.body,
                    parent_id=c.parent_id,
                    upvote_count=c.upvote_count,
                    downvote_count=c.downvote_count,
                    toxicity_flag=c.toxicity_flag,
                    moderation_status=c.moderation_status.value,
                    created_at=c.created_at,
                    replies=build(c.id),
                )
            )
        return nodes

    return build(None)


def create_comment(db: Session, target_type: TargetType, target_id: int, author: User, body: str, parent_id: int | None) -> Comment:
    comment = Comment(
        target_type=target_type,
        target_id=target_id,
        parent_id=parent_id,
        author_id=author.id,
        body=body,
    )
    db.add(comment)
    db.flush()

    try:
        result = ai_community.detect_toxic_comment(body)
        comment.toxicity_flag = result["is_toxic"]
    except Exception:
        pass  # non-blocking: AI 판정이 실패해도 댓글 작성 자체는 막지 않는다.

    target = get_target_row(db, target_type, target_id)
    if target is not None:
        target.comment_count += 1

    db.commit()
    db.refresh(comment)
    return comment


def serialize_post(post: CommunityPost) -> CommunityPostOut:
    return CommunityPostOut(
        id=post.id,
        board_slug=post.board.slug,
        author_nickname=post.author.nickname,
        title=post.title,
        body=post.body,
        upvote_count=post.upvote_count,
        downvote_count=post.downvote_count,
        comment_count=post.comment_count,
        moderation_status=post.moderation_status.value,
        created_at=post.created_at,
    )


def serialize_news_post(news: NewsPost) -> NewsPostOut:
    return NewsPostOut(
        id=news.id,
        title=news.title,
        source_url=news.source_url,
        source_name=news.source_name,
        category=news.category,
        thumbnail_url=news.thumbnail_url,
        region=news.region.name if news.region else None,
        tags=[t.strip() for t in news.tags.split(",") if t.strip()] if news.tags else [],
        fake_news_risk_label=news.fake_news_risk_label,
        published_at=news.published_at,
        upvote_count=news.upvote_count,
        downvote_count=news.downvote_count,
        comment_count=news.comment_count,
        moderation_status=news.moderation_status.value,
        created_at=news.created_at,
    )


def preview_text(text: str, limit: int = 80) -> str:
    text = text.strip().replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + "…"
