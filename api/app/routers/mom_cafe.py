from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.community_common import serialize_post
from app.database import get_db
from app.models_community import Board, CommunityPost, ModerationStatus
from app.schemas_community import BoardOut, FeedPage

router = APIRouter(prefix="/mom-cafe", tags=["mom-cafe"])


@router.get("/boards", response_model=list[BoardOut])
def list_boards(db: Session = Depends(get_db)):
    boards = db.query(Board).all()
    return [
        BoardOut(
            id=b.id, slug=b.slug, name=b.name, board_type=b.board_type.value,
            region=b.region.name if b.region else None,
        )
        for b in boards
    ]


def _board_feed(db: Session, slug: str, limit: int, offset: int) -> FeedPage:
    board = db.query(Board).filter(Board.slug == slug).first()
    if not board:
        raise HTTPException(status_code=404, detail="존재하지 않는 게시판입니다")

    query = db.query(CommunityPost).filter(
        CommunityPost.board_id == board.id, CommunityPost.moderation_status == ModerationStatus.VISIBLE
    )
    total = query.count()
    posts = query.order_by(CommunityPost.created_at.desc()).offset(offset).limit(limit).all()
    return FeedPage(items=[serialize_post(p) for p in posts], total=total, limit=limit, offset=offset)


@router.get("/region/{region}", response_model=FeedPage)
def region_board(region: str, limit: int = Query(20, le=100), offset: int = 0, db: Session = Depends(get_db)):
    return _board_feed(db, f"region-{region}", limit, offset)


@router.get("/education", response_model=FeedPage)
def education_board(limit: int = Query(20, le=100), offset: int = 0, db: Session = Depends(get_db)):
    return _board_feed(db, "education", limit, offset)


@router.get("/parenting", response_model=FeedPage)
def parenting_board(limit: int = Query(20, le=100), offset: int = 0, db: Session = Depends(get_db)):
    return _board_feed(db, "parenting", limit, offset)
