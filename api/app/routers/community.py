from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import ai_community
from app.auth import get_current_user
from app.community_common import apply_vote, build_comment_tree, create_comment, serialize_post
from app.database import get_db
from app.models_community import Board, Comment, CommunityPost, ModerationStatus, Region, Report, TargetType, User
from app.schemas_community import (
    CommentCreate,
    CommentOut,
    CommunityPostCreate,
    CommunityPostDetail,
    CommunityPostOut,
    FeedPage,
    RelatedPostOut,
    ReportCreate,
    ReportOut,
    UserCreate,
    UserOut,
    VoteRequest,
    VoteResult,
)

router = APIRouter(prefix="/community", tags=["community"])


@router.post("/users", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    """임시 가입 — 비밀번호 없이 닉네임만으로 user_id를 발급한다. TODO: 실제 인증으로 교체."""
    if db.query(User).filter(User.nickname == payload.nickname).first():
        raise HTTPException(status_code=409, detail="이미 사용 중인 닉네임입니다")

    region = None
    if payload.region_slug:
        region = db.query(Region).filter(Region.slug == payload.region_slug).first()
        if not region:
            raise HTTPException(status_code=400, detail="존재하지 않는 지역입니다")

    user = User(nickname=payload.nickname, region_id=region.id if region else None)
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut(
        id=user.id, nickname=user.nickname, region=region.name if region else None,
        level=None, created_at=user.created_at,
    )


@router.get("/feed", response_model=FeedPage)
def get_feed(
    board_slug: str | None = None,
    sort: str = Query("new", pattern="^(new|top)$"),
    limit: int = Query(20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(CommunityPost).filter(CommunityPost.moderation_status == ModerationStatus.VISIBLE)
    if board_slug:
        board = db.query(Board).filter(Board.slug == board_slug).first()
        if not board:
            raise HTTPException(status_code=404, detail="존재하지 않는 게시판입니다")
        query = query.filter(CommunityPost.board_id == board.id)

    total = query.count()
    if sort == "top":
        query = query.order_by((CommunityPost.upvote_count - CommunityPost.downvote_count).desc())
    else:
        query = query.order_by(CommunityPost.created_at.desc())

    posts = query.offset(offset).limit(limit).all()
    return FeedPage(items=[serialize_post(p) for p in posts], total=total, limit=limit, offset=offset)


@router.get("/posts/{post_id}", response_model=CommunityPostDetail)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.get(CommunityPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")

    comments = (
        db.query(Comment)
        .filter(Comment.target_type == TargetType.POST, Comment.target_id == post_id)
        .all()
    )
    base = serialize_post(post)
    return CommunityPostDetail(**base.model_dump(), comments=build_comment_tree(comments))


@router.post("/posts", response_model=CommunityPostOut)
def create_post(
    payload: CommunityPostCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    board = db.query(Board).filter(Board.slug == payload.board_slug).first()
    if not board:
        raise HTTPException(status_code=400, detail="존재하지 않는 게시판입니다")

    post = CommunityPost(board_id=board.id, author_id=user.id, title=payload.title, body=payload.body)
    db.add(post)
    db.commit()
    db.refresh(post)
    return serialize_post(post)


@router.post("/posts/{post_id}/comments", response_model=CommentOut)
def add_comment(
    post_id: int, payload: CommentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    post = db.get(CommunityPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")

    if payload.parent_id is not None:
        parent = db.get(Comment, payload.parent_id)
        if not parent or parent.target_type != TargetType.POST or parent.target_id != post_id:
            raise HTTPException(status_code=400, detail="잘못된 부모 댓글입니다")

    comment = create_comment(db, TargetType.POST, post_id, user, payload.body, payload.parent_id)
    return CommentOut(
        id=comment.id, author_nickname=user.nickname, body=comment.body, parent_id=comment.parent_id,
        upvote_count=comment.upvote_count, downvote_count=comment.downvote_count,
        toxicity_flag=comment.toxicity_flag, moderation_status=comment.moderation_status.value,
        created_at=comment.created_at, replies=[],
    )


@router.post("/posts/{post_id}/vote", response_model=VoteResult)
def vote_post(
    post_id: int, payload: VoteRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        return apply_vote(db, user, TargetType.POST, post_id, payload.value)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/comments/{comment_id}/vote", response_model=VoteResult)
def vote_comment(
    comment_id: int, payload: VoteRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        return apply_vote(db, user, TargetType.COMMENT, comment_id, payload.value)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/trending", response_model=list[str])
def trending_keywords(limit: int = Query(30, le=100), db: Session = Depends(get_db)):
    """extract_trending_keywords 부가 AI 기능 — 최근 게시글 제목에서 화제 키워드를 추출한다.
    advisory 성격이라 AI 호출 실패 시에도 빈 목록으로 폴백하고 절대 500을 던지지 않는다."""
    posts = (
        db.query(CommunityPost)
        .filter(CommunityPost.moderation_status == ModerationStatus.VISIBLE)
        .order_by(CommunityPost.created_at.desc())
        .limit(limit)
        .all()
    )
    try:
        return ai_community.extract_trending_keywords([p.title for p in posts])
    except Exception:
        return []


@router.get("/posts/{post_id}/related", response_model=list[RelatedPostOut])
def related_posts(post_id: int, db: Session = Depends(get_db)):
    """suggest_related_posts 부가 AI 기능 — 같은 게시판의 최근 글 중 관련 글을 추천한다."""
    post = db.get(CommunityPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")

    candidates = (
        db.query(CommunityPost)
        .filter(
            CommunityPost.board_id == post.board_id,
            CommunityPost.id != post_id,
            CommunityPost.moderation_status == ModerationStatus.VISIBLE,
        )
        .order_by(CommunityPost.created_at.desc())
        .limit(30)
        .all()
    )
    if not candidates:
        return []

    by_title = {c.title: c for c in candidates}
    try:
        picked = ai_community.suggest_related_posts(post.title, list(by_title.keys()))
    except Exception:
        return []

    return [RelatedPostOut(id=by_title[t].id, title=t) for t in picked if t in by_title]


@router.post("/posts/{post_id}/report", response_model=ReportOut)
def report_post(
    post_id: int, payload: ReportCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    post = db.get(CommunityPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")

    report = Report(
        reporter_id=user.id, target_type=TargetType.POST, target_id=post_id,
        reason=payload.reason, detail=payload.detail,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return ReportOut(
        id=report.id, target_type=report.target_type.value, target_id=report.target_id,
        reason=report.reason, detail=report.detail, status=report.status.value, created_at=report.created_at,
    )
